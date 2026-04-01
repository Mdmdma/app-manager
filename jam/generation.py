"""Agentic document generation workflow using LangGraph.

Orchestrates CV and cover-letter generation through a multi-node graph:
  retrieve_kb_docs → generate_or_revise → analyze_fit → analyze_quality
  → apply_suggestions → compile_and_check → (reduce_size loop) → finalize
"""

from __future__ import annotations

import asyncio
import json
import logging
import operator
import os
import re
import shutil
import tempfile
from collections import defaultdict
from typing import Annotated, TypedDict

import fitz  # pymupdf

from jam.config import Settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class CompileError(Exception):
    pass


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------


class DocumentGenerationState(TypedDict):
    # ── Inputs (set once before graph runs) ─────────────────────
    doc_id: str
    application_id: str
    doc_type: str  # "cv" or "cover_letter"
    latex_template: str  # original latex_source (unchanged reference)
    job_description: str
    instructions_json: str  # prompt_text JSON from DB
    is_first_generation: bool

    # ── Image assets (base64 data URIs, populated in retrieve_kb_docs) ──
    personal_photo: str         # base64 data URI or ""
    personal_signature: str     # base64 data URI or ""

    # ── Derived / populated during graph execution ───────────────
    kb_docs: list[dict]
    inline_comments: list[str]  # extracted from % [COMMENT: ...] markers
    locked_sections: list[str]  # section keys where enabled==False

    # ── Working copy ─────────────────────────────────────────────
    current_latex: str

    # ── Agent outputs ────────────────────────────────────────────
    fit_feedback: str
    quality_feedback: str

    # ── Prompt details (for transparency / debugging) ──────────────
    generation_system_prompt: str | None  # system message to LLM
    generation_user_prompt: str | None    # user message to LLM (context + instructions)

    # ── Compile loop ─────────────────────────────────────────────
    page_count: int
    compile_attempts: int  # number of size-reduction attempts (max 3)
    compile_error: str | None

    # ── SSE progress (accumulated, never replaced) ───────────────
    progress_events: Annotated[list[dict], operator.add]

    # ── Final output ─────────────────────────────────────────────
    final_latex: str | None
    final_pdf: bytes | None
    error: str | None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_COMMENT_RE = re.compile(r"%\s*\[COMMENT:\s*(.*?)\]", re.IGNORECASE)

_MAX_SIZE_ATTEMPTS = 3

# ---------------------------------------------------------------------------
# Default system prompt templates (configurable via DB settings)
# ---------------------------------------------------------------------------

PROMPT_GENERATE_FIRST = """\
You are an expert CV/cover-letter writer. Populate the LaTeX template below \
with the candidate's real information drawn from the provided knowledge-base \
documents. Preserve the LaTeX document structure and commands exactly — only \
replace placeholder text. Return ONLY the complete LaTeX document, no markdown \
fences, no commentary.
{locked_sections_notice}"""

PROMPT_GENERATE_REVISE = """\
You are an expert CV/cover-letter editor. Revise the LaTeX document according \
to the user instructions, inline comments, fit analysis, and quality analysis \
provided. Use the knowledge-base documents as the authoritative source of \
candidate information. Preserve the LaTeX document structure. Return ONLY the \
complete revised LaTeX document, no markdown fences, no commentary.
{locked_sections_notice}"""

PROMPT_ANALYZE_FIT = """\
You are a hiring-fit analyst. Read the candidate document and the job \
description. List 3-5 specific, actionable improvements to better match \
the document to the job requirements. Be concise. Plain text only — no LaTeX."""

PROMPT_ANALYZE_QUALITY = """\
You are a document-quality reviewer. Check the document for:
1. AI-sounding phrases ("leverage", "synergy", "utilize", overuse of "passionate", etc.)
2. Vague or unquantified claims
3. Grammatical or spelling issues
4. Formatting inconsistencies visible in the LaTeX source
List issues concisely. Plain text only — no LaTeX."""

PROMPT_APPLY_SUGGESTIONS = """\
You are a LaTeX document editor. Apply the feedback below to improve the \
document. {locked_sections_notice}
Return ONLY the complete revised LaTeX document, no markdown fences."""

PROMPT_REDUCE_SIZE = """\
The document is {page_count} page(s) but must fit on exactly 1 page. \
Reduce content to fit: tighten wording, shorten bullet points, remove less \
important items. Do NOT remove entire sections unless unavoidable. \
{locked_sections_notice}
Return ONLY the complete revised LaTeX document, no markdown fences."""


def _get_prompt(key: str, default: str) -> str:
    """Load a prompt template from DB settings, falling back to default."""
    from jam.db import get_all_settings
    stored = get_all_settings()
    return stored.get(key) or default


def _resolve_step_model(step_key: str) -> tuple[str | None, str | None]:
    """Return (provider, model) override for a generation step, or (None, None) for global default."""
    from jam.db import get_all_settings
    stored = get_all_settings()
    catalog_id = stored.get(f"step_model_{step_key}", "")
    if not catalog_id:
        return None, None
    parts = catalog_id.split(":", 1)
    if len(parts) != 2:
        return None, None
    return parts[0], parts[1]


def _extract_inline_comments(latex: str) -> list[str]:
    """Return list of user comment strings from '% [COMMENT: ...]' markers."""
    return [m.group(1).strip() for m in _COMMENT_RE.finditer(latex)]


def _locked_sections(instructions_json: str) -> list[str]:
    """Return section keys where enabled is False."""
    try:
        data = json.loads(instructions_json)
    except (json.JSONDecodeError, TypeError):
        return []
    return [
        s["key"] for s in data.get("sections", []) if not s.get("enabled", True)
    ]


def _extract_kb_doc_content(doc: dict) -> str:
    """Extract usable content from a KB document, handling different response formats.

    KB API returns documents in two formats:
    - search_documents: {"text": "...", "metadata": {...}, ...}  (chunked search results)
    - list_namespace_documents: {"summary": "...", "title": "...", ...}  (metadata only)

    Try to extract the most complete content available.
    """
    # Try text field first (from semantic search)
    if doc.get("text"):
        return doc["text"]

    # Fall back to content field (if available)
    if doc.get("content"):
        return doc["content"]

    # Fall back to summary (from list_namespace_documents)
    if doc.get("summary"):
        return f"{doc.get('title', 'Document')}\n\n{doc['summary']}"

    # Worst case: just title
    if doc.get("title"):
        return doc["title"]

    return ""


def _format_instructions(instructions_json: str) -> str:
    """Format enabled section instructions for inclusion in an LLM prompt."""
    try:
        data = json.loads(instructions_json)
    except (json.JSONDecodeError, TypeError):
        return ""
    parts = []
    if data.get("general"):
        parts.append(f"General: {data['general']}")
    for s in data.get("sections", []):
        if s.get("enabled", True) and s.get("text"):
            parts.append(f"{s['label']}: {s['text']}")
    return "\n".join(parts)


def _restore_locked_sections(
    original_latex: str,
    revised_latex: str,
    locked_section_keys: list[str],
    doc_type: str,
) -> str:
    """Re-insert locked section content from original into revised LaTeX.

    CV sections: \\section{key}
    Cover letter sections: \\paragraph{key}
    """
    if not locked_section_keys:
        return revised_latex

    marker_cmd = "section" if doc_type == "cv" else "paragraph"

    result = revised_latex
    for key in locked_section_keys:
        pattern = (
            rf"(\\{marker_cmd}\{{{re.escape(key)}\}})(.*?)"
            rf"(?=\\{marker_cmd}\{{|\\end\{{)"
        )
        orig_match = re.search(pattern, original_latex, re.DOTALL)
        if not orig_match:
            continue
        orig_block = orig_match.group(0)
        result = re.sub(pattern, lambda _m, b=orig_block: b, result, flags=re.DOTALL)

    return result


def _strip_latex_fences(text: str) -> str:
    """Remove markdown code fences that models sometimes wrap around LaTeX."""
    text = text.strip()
    text = re.sub(r"^```(?:latex|tex)?\n?", "", text)
    text = re.sub(r"\n?```$", "", text)
    return text.strip()


async def _compile_latex_bytes(
    latex_source: str,
    images: dict[str, str] | None = None,
) -> bytes:
    """Run tectonic and return PDF bytes. Raises CompileError on failure.

    Args:
        latex_source: LaTeX document source.
        images: Optional mapping of filename base (e.g. ``"photo"``) to
            base64 data URIs.  Each URI is decoded and written as
            ``<base>.{ext}`` in the temp directory before compilation so
            that ``\\includegraphics`` can find them.
    """
    if not shutil.which("tectonic"):
        raise CompileError("tectonic not found in PATH")
    with tempfile.TemporaryDirectory() as tmpdir:
        tex_path = os.path.join(tmpdir, "document.tex")
        pdf_path = os.path.join(tmpdir, "document.pdf")
        with open(tex_path, "w", encoding="utf-8") as fh:
            fh.write(latex_source)
        if images:
            import base64 as _b64
            for filename_base, data_uri in images.items():
                if not data_uri.startswith("data:"):
                    continue
                try:
                    header, b64 = data_uri.split(",", 1)
                    mime = header.split(":")[1].split(";")[0]
                    ext = mime.split("/")[1]
                    img_bytes = _b64.b64decode(b64)
                    with open(os.path.join(tmpdir, f"{filename_base}.{ext}"), "wb") as fh:
                        fh.write(img_bytes)
                except Exception:
                    pass
        proc = await asyncio.create_subprocess_exec(
            "tectonic",
            tex_path,
            "--untrusted",
            cwd=tmpdir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raw = stderr.decode(errors="replace") or stdout.decode(errors="replace")
            raise CompileError(raw[:2000])
        if not os.path.exists(pdf_path):
            raise CompileError("tectonic produced no PDF output")
        with open(pdf_path, "rb") as fh:
            return fh.read()


def _pdf_page_count(pdf_bytes: bytes) -> int:
    """Return the number of pages in the given PDF bytes."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    count = doc.page_count
    doc.close()
    return count


# ---------------------------------------------------------------------------
# Graph nodes
# ---------------------------------------------------------------------------


async def retrieve_kb_docs(state: DocumentGenerationState) -> dict:
    from jam.db import get_all_settings
    from jam.kb_client import list_namespace_documents, search_documents

    # Load persisted KB settings from the database, with Settings as fallback defaults
    stored = get_all_settings()
    settings = Settings()

    # kb_retrieval_namespaces: DB takes precedence, then Settings env var, then empty list
    try:
        search_ns = json.loads(
            stored.get("kb_retrieval_namespaces")
            or settings.kb_retrieval_namespaces
            or "[]"
        )
    except (json.JSONDecodeError, TypeError):
        search_ns = []

    # kb_include_namespaces: DB takes precedence, then Settings env var, then empty list
    try:
        include_ns = json.loads(
            stored.get("kb_include_namespaces")
            or settings.kb_include_namespaces
            or "[]"
        )
    except (json.JSONDecodeError, TypeError):
        include_ns = []

    # kb_retrieval_n_results: DB takes precedence, then Settings env var, then 5
    n_results = int(stored.get("kb_retrieval_n_results") or settings.kb_retrieval_n_results or 5)

    # kb_retrieval_padding: DB takes precedence, then Settings env var, then 0
    padding = int(stored.get("kb_retrieval_padding") or settings.kb_retrieval_padding or 0)

    query = state["job_description"][:500]

    # Semantic search within selected namespaces, over-fetching by padding amount
    try:
        search_results = await search_documents(
            query,
            n_results=n_results + padding,
            namespace_ids=search_ns or None,
            settings=settings,
        )
    except Exception as exc:
        logger.warning("KB semantic search failed: %s", exc)
        search_results = []

    # Trim results back to requested count after over-fetch
    search_results = search_results[:n_results]

    # Fetch full content for "include entire namespaces"
    include_docs: list[dict] = []
    if include_ns:
        try:
            include_docs = await list_namespace_documents(
                include_ns, settings=settings
            )
        except Exception as exc:
            logger.warning("KB include namespace fetch failed for %s: %s", include_ns, exc)
            include_docs = []

    # Merge: include-namespace docs first, then search results (deduplicated)
    # Search API chunks use "doc_id"; list API documents use "id".
    seen_ids: set[str] = set()
    merged: list[dict] = []
    for doc in include_docs:
        doc_id = doc.get("doc_id") or doc.get("id", "")
        if doc_id and doc_id not in seen_ids:
            seen_ids.add(doc_id)
        merged.append(doc)
    for doc in search_results:
        doc_id = doc.get("doc_id") or doc.get("id", "")
        if not doc_id or doc_id not in seen_ids:
            if doc_id:
                seen_ids.add(doc_id)
            merged.append(doc)

    search_detail = f"{len(search_results)} searched"
    include_detail = f", {len(include_docs)} included" if include_ns else ""

    return {
        "kb_docs": merged,
        "inline_comments": _extract_inline_comments(state["latex_template"]),
        "locked_sections": _locked_sections(state["instructions_json"]),
        "personal_photo": stored.get("personal_photo", ""),
        "personal_signature": stored.get("personal_signature", ""),
        "progress_events": [
            {
                "node": "retrieve_kb_docs",
                "status": "done",
                "detail": f"{len(merged)} KB docs ({search_detail}{include_detail})",
            }
        ],
    }


async def generate_or_revise(state: DocumentGenerationState) -> dict:
    from jam.llm import llm_call

    locked = state["locked_sections"]
    locked_str = (
        "The following sections are LOCKED and must NOT be modified: "
        + ", ".join(locked)
        if locked
        else "No sections are locked."
    )
    kb_context = "\n\n".join(_extract_kb_doc_content(d) for d in state["kb_docs"])[:6000]

    # Build image availability hints for the LLM
    photo_available = bool(state.get("personal_photo"))
    signature_available = bool(state.get("personal_signature"))
    image_hints = []
    if photo_available:
        photo_uri = state["personal_photo"]
        photo_ext = "png"
        if photo_uri.startswith("data:"):
            try:
                photo_ext = photo_uri.split(":")[1].split(";")[0].split("/")[1]
            except Exception:
                pass
        image_hints.append(
            f"A profile photo of the candidate is available as 'photo.{photo_ext}'."
            f" You may include it using \\includegraphics{{photo.{photo_ext}}}."
        )
    if signature_available:
        sig_uri = state["personal_signature"]
        sig_ext = "png"
        if sig_uri.startswith("data:"):
            try:
                sig_ext = sig_uri.split(":")[1].split(";")[0].split("/")[1]
            except Exception:
                pass
        image_hints.append(
            f"A signature image is available as 'signature.{sig_ext}'."
            f" You may include it using \\includegraphics{{signature.{sig_ext}}}."
        )
    image_info = "\n".join(image_hints) if image_hints else ""

    if state["is_first_generation"]:
        template = _get_prompt("prompt_generate_first", PROMPT_GENERATE_FIRST)
        system = template.format_map(
            defaultdict(str, locked_sections_notice=locked_str)
        )
        if image_info:
            system += f"\n{image_info}"
        user = f"""\
=== JOB DESCRIPTION ===
{state["job_description"]}

=== KNOWLEDGE BASE DOCUMENTS ===
{kb_context if kb_context else "(none available)"}

=== LATEX TEMPLATE ===
{state["latex_template"]}"""
    else:
        comments = state["inline_comments"]
        comments_str = "\n".join(f"- {c}" for c in comments) if comments else "None"
        instructions = _format_instructions(state["instructions_json"])
        template = _get_prompt("prompt_generate_revise", PROMPT_GENERATE_REVISE)
        system = template.format_map(
            defaultdict(str, locked_sections_notice=locked_str)
        )
        if image_info:
            system += f"\n{image_info}"
        user = f"""\
=== JOB DESCRIPTION ===
{state["job_description"]}

=== KNOWLEDGE BASE DOCUMENTS ===
{kb_context if kb_context else "(none available)"}

=== USER INSTRUCTIONS ===
{instructions if instructions else "(none)"}

=== INLINE COMMENTS FROM USER ===
{comments_str}

=== FIT AGENT FEEDBACK ===
{state.get("fit_feedback") or "(none)"}

=== QUALITY AGENT FEEDBACK ===
{state.get("quality_feedback") or "(none)"}

=== CURRENT LATEX ===
{state["current_latex"]}"""

    try:
        step_provider, step_model = _resolve_step_model("generate_or_revise")
        raw = await llm_call(system, user, Settings(), provider=step_provider, model=step_model)
    except Exception as exc:
        return {
            "error": str(exc),
            "progress_events": [
                {"node": "generate_or_revise", "status": "error", "detail": str(exc)}
            ],
        }

    latex = _strip_latex_fences(raw)
    latex = _restore_locked_sections(
        state["latex_template"], latex, locked, state["doc_type"]
    )

    return {
        "current_latex": latex,
        "generation_system_prompt": system,
        "generation_user_prompt": user,
        "progress_events": [{"node": "generate_or_revise", "status": "done"}],
    }


async def analyze_fit(state: DocumentGenerationState) -> dict:
    from jam.llm import llm_call

    system = _get_prompt("prompt_analyze_fit", PROMPT_ANALYZE_FIT)
    user = f"""\
=== JOB DESCRIPTION ===
{state["job_description"][:3000]}

=== DOCUMENT ===
{state["current_latex"][:6000]}"""

    try:
        step_provider, step_model = _resolve_step_model("analyze_fit")
        feedback = await llm_call(system, user, Settings(), provider=step_provider, model=step_model)
    except Exception as exc:
        feedback = ""
        return {
            "fit_feedback": feedback,
            "progress_events": [
                {"node": "analyze_fit", "status": "error", "detail": str(exc)}
            ],
        }
    return {
        "fit_feedback": feedback,
        "progress_events": [{"node": "analyze_fit", "status": "done"}],
    }


async def analyze_quality(state: DocumentGenerationState) -> dict:
    from jam.llm import llm_call

    system = _get_prompt("prompt_analyze_quality", PROMPT_ANALYZE_QUALITY)
    user = f"=== DOCUMENT ===\n{state['current_latex'][:6000]}"

    try:
        step_provider, step_model = _resolve_step_model("analyze_quality")
        feedback = await llm_call(system, user, Settings(), provider=step_provider, model=step_model)
    except Exception:
        feedback = ""
    return {
        "quality_feedback": feedback,
        "progress_events": [{"node": "analyze_quality", "status": "done"}],
    }


async def apply_suggestions(state: DocumentGenerationState) -> dict:
    from jam.llm import llm_call

    locked = state["locked_sections"]
    locked_str = (
        "LOCKED sections (do NOT touch): " + ", ".join(locked)
        if locked
        else "No locked sections."
    )
    template = _get_prompt("prompt_apply_suggestions", PROMPT_APPLY_SUGGESTIONS)
    system = template.format_map(
        defaultdict(str, locked_sections_notice=locked_str)
    )
    user = f"""\
=== FIT FEEDBACK ===
{state["fit_feedback"] or "(none)"}

=== QUALITY FEEDBACK ===
{state["quality_feedback"] or "(none)"}

=== DOCUMENT ===
{state["current_latex"]}"""

    try:
        step_provider, step_model = _resolve_step_model("apply_suggestions")
        raw = await llm_call(system, user, Settings(), provider=step_provider, model=step_model)
    except Exception as exc:
        return {
            "progress_events": [
                {"node": "apply_suggestions", "status": "error", "detail": str(exc)}
            ]
        }

    latex = _strip_latex_fences(raw)
    latex = _restore_locked_sections(
        state["current_latex"], latex, locked, state["doc_type"]
    )

    return {
        "current_latex": latex,
        "progress_events": [{"node": "apply_suggestions", "status": "done"}],
    }


async def compile_and_check(state: DocumentGenerationState) -> dict:
    if state.get("error"):
        # Propagate upstream error without compiling
        return {
            "page_count": 0,
            "progress_events": [
                {"node": "compile_and_check", "status": "skipped", "detail": "upstream error"}
            ],
        }
    images: dict[str, str] = {}
    if state.get("personal_photo"):
        images["photo"] = state["personal_photo"]
    if state.get("personal_signature"):
        images["signature"] = state["personal_signature"]
    try:
        pdf_bytes = await _compile_latex_bytes(state["current_latex"], images=images or None)
    except CompileError as exc:
        return {
            "compile_error": str(exc),
            "page_count": 0,
            "progress_events": [
                {"node": "compile_and_check", "status": "error", "detail": str(exc)[:200]}
            ],
        }
    page_count = _pdf_page_count(pdf_bytes)
    result: dict = {
        "compile_error": None,
        "page_count": page_count,
        "progress_events": [
            {
                "node": "compile_and_check",
                "status": "done",
                "detail": f"{page_count} page(s)",
            }
        ],
    }
    if page_count <= 1:
        result["final_pdf"] = pdf_bytes
        result["final_latex"] = state["current_latex"]
    return result


async def reduce_size(state: DocumentGenerationState) -> dict:
    from jam.llm import llm_call

    locked = state["locked_sections"]
    locked_str = (
        "LOCKED sections (must NOT be shortened): " + ", ".join(locked)
        if locked
        else "No locked sections."
    )
    attempt = state["compile_attempts"] + 1
    template = _get_prompt("prompt_reduce_size", PROMPT_REDUCE_SIZE)
    system = template.format_map(
        defaultdict(str, locked_sections_notice=locked_str, page_count=str(state["page_count"]))
    )
    user = state["current_latex"]

    try:
        step_provider, step_model = _resolve_step_model("reduce_size")
        raw = await llm_call(system, user, Settings(), provider=step_provider, model=step_model)
    except Exception as exc:
        return {
            "compile_attempts": attempt,
            "progress_events": [
                {"node": "reduce_size", "status": "error", "detail": str(exc)}
            ],
        }

    latex = _strip_latex_fences(raw)
    latex = _restore_locked_sections(
        state["current_latex"], latex, locked, state["doc_type"]
    )

    return {
        "current_latex": latex,
        "compile_attempts": attempt,
        "progress_events": [
            {
                "node": "reduce_size",
                "status": "done",
                "detail": f"attempt {attempt}",
            }
        ],
    }


async def finalize(state: DocumentGenerationState) -> dict:
    return {
        "final_latex": state["current_latex"],
        "progress_events": [{"node": "finalize", "status": "done"}],
    }


# ---------------------------------------------------------------------------
# Conditional routing
# ---------------------------------------------------------------------------


def _route_after_compile(state: DocumentGenerationState) -> str:
    if state.get("error"):
        return "end_on_error"
    if state.get("compile_error"):
        return "end_on_error"
    if state["page_count"] <= 1:
        return "finalize"
    if state["compile_attempts"] >= _MAX_SIZE_ATTEMPTS:
        return "finalize"
    return "reduce_size"


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------


def build_generation_graph():
    from langgraph.graph import StateGraph, END

    graph = StateGraph(DocumentGenerationState)

    graph.add_node("retrieve_kb_docs", retrieve_kb_docs)
    graph.add_node("generate_or_revise", generate_or_revise)
    graph.add_node("analyze_fit", analyze_fit)
    graph.add_node("analyze_quality", analyze_quality)
    graph.add_node("apply_suggestions", apply_suggestions)
    graph.add_node("compile_and_check", compile_and_check)
    graph.add_node("reduce_size", reduce_size)
    graph.add_node("finalize", finalize)

    graph.set_entry_point("retrieve_kb_docs")

    graph.add_edge("retrieve_kb_docs", "generate_or_revise")
    graph.add_edge("generate_or_revise", "analyze_fit")
    graph.add_edge("analyze_fit", "analyze_quality")
    graph.add_edge("analyze_quality", "apply_suggestions")
    graph.add_edge("apply_suggestions", "compile_and_check")

    graph.add_conditional_edges(
        "compile_and_check",
        _route_after_compile,
        {
            "finalize": "finalize",
            "reduce_size": "reduce_size",
            "end_on_error": END,
        },
    )

    graph.add_edge("reduce_size", "compile_and_check")
    graph.add_edge("finalize", END)

    return graph.compile()


# Compiled once at import time, reused across all requests.
generation_graph = build_generation_graph()


def build_critique_graph():
    """Graph that only critiques the current document without modifying it."""
    from langgraph.graph import StateGraph, END

    graph = StateGraph(DocumentGenerationState)

    graph.add_node("analyze_fit", analyze_fit)
    graph.add_node("analyze_quality", analyze_quality)
    graph.add_node("finalize", finalize)

    graph.set_entry_point("analyze_fit")

    graph.add_edge("analyze_fit", "analyze_quality")
    graph.add_edge("analyze_quality", "finalize")
    graph.add_edge("finalize", END)

    return graph.compile()


critique_graph = build_critique_graph()
