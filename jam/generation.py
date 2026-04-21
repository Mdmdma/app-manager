"""Agentic document generation workflow using LangGraph.

Orchestrates CV and cover-letter generation through a multi-node graph:
  retrieve_kb_docs → generate_or_revise → compile_and_check
  → fan-out: [analyze_fit || analyze_quality || analyze_compress]
  → finalize

Also contains a separate interview prep-guide pipeline:
  load_context → generate_guide → finalize_prep_guide
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
from datetime import datetime, timezone
from typing import Annotated, AsyncIterator, TypedDict

import fitz  # pymupdf

from jam.config import Settings

logger = logging.getLogger(__name__)

_LLM_SEM = asyncio.Semaphore(1)

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
    compress_feedback: str

    # ── Prompt details (for transparency / debugging) ──────────────
    generation_system_prompt: str | None  # system message to LLM
    generation_user_prompt: str | None    # user message to LLM (context + instructions)

    # ── Compact loop ─────────────────────────────────────────────
    compact_iteration: int   # starts at 0, incremented by analyze_compress
    max_compact_iterations: int  # max times to loop (default 3)

    # ── Compile loop ─────────────────────────────────────────────
    page_count: int
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

# ---------------------------------------------------------------------------
# Default system prompt templates (configurable via DB settings)
# ---------------------------------------------------------------------------

PROMPT_GENERATE_FIRST_CV = """\
You are an expert CV writer. Populate the LaTeX template with the candidate's \
real information from the knowledge-base documents. ONLY include facts explicitly \
stated in the provided documents — never invent or embellish experiences, skills, \
or achievements. Focus on: quantified achievements, strong but natural action verbs, \
keyword alignment with the job description, and consistent bullet-point structure. \
Write in plain, direct language — avoid emdashes, overly complex sentences, and \
AI-sounding phrases ("leverage", "utilize", "spearhead", "passionate about", \
"proven track record"). Preserve LaTeX structure exactly — only replace placeholder \
text. Return ONLY the complete LaTeX document, no markdown fences, no commentary.
{locked_sections_notice}"""

PROMPT_GENERATE_FIRST_CL = """\
You are an expert cover-letter writer. Draft a compelling cover letter using the \
LaTeX template and the candidate's information from the knowledge-base documents. \
ONLY include facts explicitly stated in the provided documents — never invent or \
embellish experiences, motivations, or achievements. Focus on: narrative flow, a \
strong opening hook, connecting the candidate's real experience to the role's \
requirements, and a confident closing. Address the hiring manager if their name is \
in the job description. Write in plain, natural language — avoid emdashes, overly \
complex sentences, and AI-sounding phrases ("leverage", "utilize", "spearhead", \
"passionate about", "proven track record"). The letter should sound like a real \
person wrote it, not a language model. Preserve LaTeX structure exactly — only \
replace placeholder text. Return ONLY the complete LaTeX document, no markdown \
fences, no commentary.
{locked_sections_notice}"""

PROMPT_GENERATE_REVISE_CV = """\
You are an expert CV editor. Revise the LaTeX document according to the user \
instructions, inline comments, fit analysis, quality analysis, and compression \
recommendations provided. ONLY include candidate information that appears in the \
knowledge-base documents — never invent or embellish. Focus on: tightening bullet \
points, adding quantification where supported by the source documents, improving \
keyword alignment, and strengthening action verbs. Write in plain, direct language \
— avoid emdashes, overly complex sentences, and AI-sounding phrases. Use \
knowledge-base documents as the authoritative source. Preserve the LaTeX document \
structure. Return ONLY the complete revised LaTeX document, no markdown fences, \
no commentary.
{locked_sections_notice}"""

PROMPT_GENERATE_REVISE_CL = """\
You are an expert cover-letter editor. Revise the LaTeX document according to the \
user instructions, inline comments, fit analysis, quality analysis, and compression \
recommendations provided. ONLY include candidate information that appears in the \
knowledge-base documents — never invent or embellish. Focus on: narrative coherence, \
natural tone and personality, paragraph flow, and strengthening the connection \
between the candidate's real experience and the role. Write in plain, natural \
language — avoid emdashes, overly complex sentences, and AI-sounding phrases. The \
letter should sound like a real person wrote it. Use knowledge-base documents as the \
authoritative source. Preserve the LaTeX document structure. Return ONLY the \
complete revised LaTeX document, no markdown fences, no commentary.
{locked_sections_notice}"""

PROMPT_ANALYZE_FIT = """\
You are a hiring-fit analyst. Read the candidate document and the job \
description. List 3-5 specific, actionable improvements to better match \
the document to the job requirements. Be concise. Plain text only — no LaTeX."""

PROMPT_ANALYZE_QUALITY_CV = """\
You are a CV quality reviewer. Check the document for:
1. AI-sounding phrases ("leverage", "synergy", "utilize", "spearhead", overuse of "passionate", "proven track record") and emdashes
2. Overly complex or nested sentence structures (prefer short, direct sentences)
3. Vague or unquantified claims (prefer numbers, percentages, scale)
4. Weak action verbs (prefer led, built, shipped, reduced, increased)
5. Inconsistent bullet-point structure
6. Grammatical or formatting issues
List issues concisely. Plain text only — no LaTeX."""

PROMPT_ANALYZE_QUALITY_CL = """\
You are a cover-letter quality reviewer. Check the document for:
1. AI-sounding phrases ("leverage", "synergy", "utilize", "spearhead", overuse of "passionate", "proven track record") and emdashes
2. Overly complex or nested sentence structures (should read naturally, like a real person wrote it)
3. Generic or impersonal tone
4. Repetitive sentence structures or ideas
5. Weak opening or closing paragraphs
6. Disconnects between claimed motivation and the actual role
7. Grammatical or formatting issues
List issues concisely. Plain text only — no LaTeX."""

PROMPT_ANALYZE_COMPRESS = """\
The document compiles to {page_count} page(s) but must fit on exactly 1 page. \
This is compression attempt {compact_iteration} of {max_compact_iterations}. \
Analyze the document and recommend specific content to cut or shorten. \
Prioritize: tightening wording, shortening bullet points, removing less \
important items. Do NOT recommend removing locked sections. \
List recommendations concisely as plain text — no LaTeX.
{locked_sections_notice}"""

_PROMPT_DEFAULTS: dict[str, dict[str, str]] = {
    "prompt_generate_first":  {"cv": PROMPT_GENERATE_FIRST_CV, "cover_letter": PROMPT_GENERATE_FIRST_CL},
    "prompt_generate_revise": {"cv": PROMPT_GENERATE_REVISE_CV, "cover_letter": PROMPT_GENERATE_REVISE_CL},
    "prompt_analyze_quality":  {"cv": PROMPT_ANALYZE_QUALITY_CV, "cover_letter": PROMPT_ANALYZE_QUALITY_CL},
}


def _get_prompt(key: str, default: str, doc_type: str = "") -> str:
    """Load a prompt template from DB settings with fallback to hardcoded default."""
    from jam.db import get_all_settings
    stored = get_all_settings()
    # Prompts with doc-type-specific variants
    typed_defaults = _PROMPT_DEFAULTS.get(key)
    if typed_defaults and doc_type:
        # Only look up the typed key — no shared fallback
        if stored.get(f"{key}:{doc_type}"):
            return stored[f"{key}:{doc_type}"]
        return typed_defaults.get(doc_type, default)
    # Shared-only prompts (analyze_fit, analyze_compress)
    if stored.get(key):
        return stored[key]
    return default


def get_all_prompt_defaults() -> dict[str, str]:
    """Return all prompt defaults for the API."""
    result = {
        "prompt_analyze_fit": PROMPT_ANALYZE_FIT,
        "prompt_analyze_compress": PROMPT_ANALYZE_COMPRESS,
        "prompt_generate_prep_guide": PROMPT_GENERATE_PREP_GUIDE,
    }
    for key, typed in _PROMPT_DEFAULTS.items():
        for doc_type, prompt in typed.items():
            result[f"{key}:{doc_type}"] = prompt
    return result


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

    # Only run semantic search if search namespaces are configured
    search_coro = (
        search_documents(
            query,
            n_results=n_results + padding,
            namespace_ids=search_ns,
            settings=settings,
        )
        if search_ns
        else None
    )

    # Only run namespace inclusion if include namespaces are configured
    list_coro = (
        list_namespace_documents(include_ns, settings=settings)
        if include_ns
        else None
    )

    # Dispatch concurrently whichever calls are needed
    coros = [c for c in (search_coro, list_coro) if c is not None]
    if coros:
        results = await asyncio.gather(*coros, return_exceptions=True)
    else:
        results = []

    # Unpack results back into search_results and include_docs
    idx = 0
    if search_coro is not None:
        search_results = results[idx]
        if isinstance(search_results, BaseException):
            logger.warning("KB semantic search failed: %s", search_results)
            search_results = []
        idx += 1
    else:
        search_results = []

    if list_coro is not None:
        include_docs = results[idx]
        if isinstance(include_docs, BaseException):
            logger.warning("KB include namespace fetch failed: %s", include_docs)
            include_docs = []
    else:
        include_docs = []

    # Trim results back to requested count after over-fetch
    search_results = search_results[:n_results]

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

    compact_iteration = state.get("compact_iteration", 0)

    if state["is_first_generation"] and compact_iteration == 0:
        template = _get_prompt("prompt_generate_first", PROMPT_GENERATE_FIRST_CV, doc_type=state["doc_type"])
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
    elif compact_iteration > 0:
        # Compact loop iteration — compression-focused, minimal context
        system = (
            "You are a document compressor. The document currently compiles to "
            f"{state['page_count']} page(s) but must fit on exactly 1 page. "
            "Apply the compression recommendations below to shorten the document. "
            "Remove or shorten content as recommended. Preserve LaTeX structure and commands. "
            "Return ONLY the complete LaTeX document, no markdown fences, no commentary."
        )
        if locked_str != "No sections are locked.":
            system += f"\n{locked_str}"
        parts = []
        compress_fb = state.get("compress_feedback") or ""
        if compress_fb:
            parts.append(f"=== COMPRESS RECOMMENDATIONS ===\n{compress_fb}")
        parts.append(f"=== CURRENT LATEX ===\n{state['current_latex']}")
        user = "\n\n".join(parts)
    else:
        # User-triggered revision — full revision prompt with feedback
        comments = state["inline_comments"]
        comments_str = "\n".join(f"- {c}" for c in comments) if comments else "None"
        instructions = _format_instructions(state["instructions_json"])
        template = _get_prompt("prompt_generate_revise", PROMPT_GENERATE_REVISE_CV, doc_type=state["doc_type"])
        system = template.format_map(
            defaultdict(str, locked_sections_notice=locked_str)
        )
        if image_info:
            system += f"\n{image_info}"
        parts = [
            f"=== JOB DESCRIPTION ===\n{state['job_description']}",
            f"=== KNOWLEDGE BASE DOCUMENTS ===\n{kb_context if kb_context else '(none available)'}",
            f"=== USER INSTRUCTIONS ===\n{instructions if instructions else '(none)'}",
            f"=== INLINE COMMENTS FROM USER ===\n{comments_str}",
            f"=== FIT AGENT FEEDBACK ===\n{state.get('fit_feedback') or '(none)'}",
            f"=== QUALITY AGENT FEEDBACK ===\n{state.get('quality_feedback') or '(none)'}",
        ]
        compress_fb = state.get("compress_feedback") or ""
        if compress_fb:
            parts.append(f"=== COMPRESS RECOMMENDATIONS ===\n{compress_fb}")
        parts.append(f"=== CURRENT LATEX ===\n{state['current_latex']}")
        user = "\n\n".join(parts)

    try:
        step_provider, step_model = _resolve_step_model("generate_or_revise")
        async with _LLM_SEM:
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

    system = _get_prompt("prompt_analyze_fit", PROMPT_ANALYZE_FIT, doc_type=state["doc_type"])
    user = f"""\
=== JOB DESCRIPTION ===
{state["job_description"][:3000]}

=== DOCUMENT ===
{state["current_latex"][:6000]}"""

    try:
        step_provider, step_model = _resolve_step_model("analyze_fit")
        async with _LLM_SEM:
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

    logger.info("[analyze_quality] node entered, current_latex length=%d", len(state.get("current_latex", "")))
    system = _get_prompt("prompt_analyze_quality", PROMPT_ANALYZE_QUALITY_CV, doc_type=state["doc_type"])
    user = f"=== DOCUMENT ===\n{state['current_latex'][:6000]}"

    try:
        step_provider, step_model = _resolve_step_model("analyze_quality")
        async with _LLM_SEM:
            feedback = await llm_call(system, user, Settings(), provider=step_provider, model=step_model)
    except Exception as exc:
        logger.error("[analyze_quality] LLM call failed: %s", exc)
        feedback = ""
        return {
            "quality_feedback": feedback,
            "progress_events": [
                {"node": "analyze_quality", "status": "error", "detail": str(exc)}
            ],
        }
    logger.info("[analyze_quality] feedback length=%d, first 200 chars: %s", len(feedback), feedback[:200])
    return {
        "quality_feedback": feedback,
        "progress_events": [{"node": "analyze_quality", "status": "done"}],
    }


async def analyze_compress(state: DocumentGenerationState) -> dict:
    """Recommend compression changes when document exceeds 1 page."""
    if state["page_count"] <= 1:
        return {
            "compress_feedback": "",
            "progress_events": [{"node": "analyze_compress", "status": "skipped"}],
        }

    from jam.llm import llm_call

    compact_iteration = state.get("compact_iteration", 0)
    max_compact_iterations = state.get("max_compact_iterations", 3)

    locked = state.get("locked_sections", [])
    locked_str = (
        "LOCKED sections (must NOT be removed): " + ", ".join(locked)
        if locked
        else ""
    )
    template = _get_prompt("prompt_analyze_compress", PROMPT_ANALYZE_COMPRESS, doc_type=state["doc_type"])
    system = template.format_map(
        defaultdict(
            str,
            locked_sections_notice=locked_str,
            page_count=str(state["page_count"]),
            compact_iteration=str(compact_iteration + 1),
            max_compact_iterations=str(max_compact_iterations),
        )
    )

    # Escalate aggressiveness based on which iteration this is
    if compact_iteration == 1:
        system += (
            "\n\nPrevious compression was insufficient. Be more aggressive — "
            "shorten bullet points and tighten wording."
        )
    elif compact_iteration >= 2:
        system += (
            "\n\nFINAL ATTEMPT — recommend removing entire bullet points or "
            "sections if needed."
        )

    user = f"=== DOCUMENT ===\n{state['current_latex'][:6000]}"

    try:
        step_provider, step_model = _resolve_step_model("analyze_compress")
        async with _LLM_SEM:
            feedback = await llm_call(system, user, Settings(), provider=step_provider, model=step_model)
    except Exception as exc:
        feedback = ""
        return {
            "compact_iteration": compact_iteration + 1,
            "compress_feedback": feedback,
            "progress_events": [{"node": "analyze_compress", "status": "error", "detail": str(exc)}],
        }
    return {
        "compact_iteration": compact_iteration + 1,
        "compress_feedback": feedback,
        "progress_events": [{"node": "analyze_compress", "status": "done"}],
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
    return {
        "compile_error": None,
        "page_count": page_count,
        "final_pdf": pdf_bytes,
        "final_latex": state["current_latex"],
        "progress_events": [
            {
                "node": "compile_and_check",
                "status": "done",
                "detail": f"{page_count} page(s)",
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


def _route_after_compile(state: DocumentGenerationState) -> "str | list[str]":
    """Route after compilation: compact loop, parallel analysis fan-out, or END on error."""
    from langgraph.graph import END
    if state.get("error") or state.get("compile_error"):
        return END
    page_count = state.get("page_count", 0)
    compact_iteration = state.get("compact_iteration", 0)
    max_compact_iterations = state.get("max_compact_iterations", 3)
    if page_count > 1 and compact_iteration < max_compact_iterations:
        return "analyze_compress"
    return ["analyze_fit", "analyze_quality"]


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------


def build_generation_graph():
    from langgraph.graph import StateGraph, END

    graph = StateGraph(DocumentGenerationState)

    graph.add_node("retrieve_kb_docs", retrieve_kb_docs)
    graph.add_node("generate_or_revise", generate_or_revise)
    graph.add_node("compile_and_check", compile_and_check)
    graph.add_node("analyze_fit", analyze_fit)
    graph.add_node("analyze_quality", analyze_quality)
    graph.add_node("analyze_compress", analyze_compress)
    graph.add_node("finalize", finalize)

    graph.set_entry_point("retrieve_kb_docs")

    graph.add_edge("retrieve_kb_docs", "generate_or_revise")
    graph.add_edge("generate_or_revise", "compile_and_check")

    # After compilation: either loop back through compress or fan out to analysis
    graph.add_conditional_edges(
        "compile_and_check",
        _route_after_compile,
        {
            "analyze_compress": "analyze_compress",
            "analyze_fit": "analyze_fit",
            "analyze_quality": "analyze_quality",
            END: END,
        },
    )

    # Compact loop: analyze_compress feeds back into generate_or_revise
    graph.add_edge("analyze_compress", "generate_or_revise")

    # Fan-in: parallel analysis branches converge at finalize
    graph.add_edge("analyze_fit", "finalize")
    graph.add_edge("analyze_quality", "finalize")

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


# ===========================================================================
# Interview Prep-Guide Pipeline
# ===========================================================================

# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------


class PrepGuideState(TypedDict, total=False):
    # ── Inputs (set by caller before invoking graph) ─────────────────────────
    interview_id: str
    application_id: str
    job_description: str
    company: str
    position: str
    round_type: str
    round_number: int
    interviewer_names: str
    interview_links: str           # newline-separated URLs
    interview_prep_notes: str      # existing prep_notes textarea content
    scheduled_at: str
    cv_latex: str
    cover_letter_latex: str

    # ── Populated by nodes ───────────────────────────────────────────────────
    kb_docs: list[dict]
    kb_context_text: str           # trimmed to 6000 chars

    # ── LLM outputs ─────────────────────────────────────────────────────────
    markdown: str
    thinking: str
    search_log: list[dict]
    generation_system_prompt: str
    generation_user_prompt: str

    # ── Progress / error ─────────────────────────────────────────────────────
    error: str
    progress_events: list[dict]


# ---------------------------------------------------------------------------
# Hardcoded default prompt
# ---------------------------------------------------------------------------

PROMPT_GENERATE_PREP_GUIDE = """\
You are an expert interview coach preparing a candidate for a specific interview round.

Your task: given the job description, candidate's CV, cover letter, interview-round \
metadata, and KB context, produce a comprehensive markdown preparation guide.

You have access to a web_search tool with a generous budget. Use it aggressively to \
gather current, accurate information about:
- The company (products, recent news, culture, team size, funding)
- The field or domain relevant to the role
- Specific projects, technologies, or frameworks named in the job description or CV
- The interviewer(s) if they appear in the provided links (LinkedIn, company bios, etc.)

You are given an extended thinking budget. Before writing the final answer:
1. Plan which searches will give the best coverage
2. Execute searches and read the results carefully
3. Draft the guide
4. CRITIQUE your draft for coherence, accuracy, completeness, and relevance
5. Revise before finalising

Output MUST be valid markdown with the following sections (use `##` headings):

## Overview
Interview type, who the candidate is meeting, what they are likely optimising for.

## Company & field background
Grounded in your web search findings. Cite URLs inline as `[text](url)`.

## Likely question types
5–10 example questions per major category, conditioned on the round type. Include \
phone-screen icebreakers OR technical deep-dives OR behavioral questions OR \
hiring-manager-style questions as appropriate.

## Your talking points
Projects and experiences from the CV to emphasise, tied to specific requirements in \
the job description. Refer to the candidate in the second person ("you").

## Technical flashcards
One fenced block per acronym, framework, concept, or domain term the candidate \
should be able to articulate clearly. Format EXACTLY:

```flashcard
Q: <question>
A: <concise answer, 1–3 sentences>
```

Generate flashcards liberally (10+ minimum) — this is the most valuable section.

## Behavioral stories (STAR)
If the round type is behavioral, hiring_manager, or panel: outline 3–5 STAR stories \
drawing from CV bullet points. Each story: Situation, Task, Action, Result — one short \
paragraph per component.

## Interviewer notes
If links contain LinkedIn or company profile URLs, note what you found about the \
interviewers (role, background, areas of interest).

## Questions to ask them
5–8 tailored questions specific to the company and role.

## Self-review
One short paragraph confirming the guide is coherent, well-covered, and noting any \
gaps the candidate should research manually before the interview."""


# ---------------------------------------------------------------------------
# Prep guide nodes
# ---------------------------------------------------------------------------


def _parse_prep_guide_model(settings: Settings) -> tuple[str | None, str | None]:
    """Parse step_model_generate_prep_guide into (provider, model) or (None, None)."""
    raw = (settings.step_model_generate_prep_guide or "").strip()
    if not raw:
        return None, None
    parts = raw.split(":", 1)
    if len(parts) != 2:
        return None, None
    return parts[0], parts[1]


def _parse_namespaces(raw: str) -> list[str]:
    """Parse a JSON list of namespace IDs from a string, returning [] on error."""
    try:
        return json.loads(raw or "[]")
    except (json.JSONDecodeError, TypeError):
        return []


async def load_context(state: PrepGuideState, settings: Settings | None = None) -> dict:
    """Fetch KB documents for the interview prep-guide pipeline."""
    settings = settings or Settings()
    from jam.kb_client import list_namespace_documents, search_documents

    query = (state.get("job_description") or "")[:500]

    search_ns = _parse_namespaces(settings.kb_retrieval_namespaces)
    include_ns = _parse_namespaces(settings.kb_include_namespaces)
    n_results = settings.kb_retrieval_n_results
    padding = settings.kb_retrieval_padding

    search_coro = (
        search_documents(
            query,
            n_results=n_results + padding,
            namespace_ids=search_ns,
            settings=settings,
        )
        if search_ns
        else None
    )
    list_coro = (
        list_namespace_documents(include_ns, settings=settings)
        if include_ns
        else None
    )

    coros = [c for c in (search_coro, list_coro) if c is not None]
    if coros:
        results = await asyncio.gather(*coros, return_exceptions=True)
    else:
        results = []

    idx = 0
    if search_coro is not None:
        search_results = results[idx]
        if isinstance(search_results, BaseException):
            logger.warning("Prep guide: KB semantic search failed: %s", search_results)
            search_results = []
        idx += 1
    else:
        search_results = []

    if list_coro is not None:
        include_docs = results[idx]
        if isinstance(include_docs, BaseException):
            logger.warning("Prep guide: KB include namespace fetch failed: %s", include_docs)
            include_docs = []
    else:
        include_docs = []

    search_results = search_results[:n_results]

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

    kb_context_text = "\n\n".join(_extract_kb_doc_content(d) for d in merged)[:6000]

    return {
        "kb_docs": merged,
        "kb_context_text": kb_context_text,
        "progress_events": [{"node": "load_context", "status": "ok"}],
    }


async def generate_guide(state: PrepGuideState, settings: Settings | None = None) -> dict:
    """Generate the markdown prep guide via llm_call_with_trace."""
    settings = settings or Settings()
    from jam.llm import _web_search_tool, llm_call_with_trace

    # Resolve provider/model
    resolved_provider, resolved_model = _parse_prep_guide_model(settings)
    if resolved_provider is None:
        resolved_provider = settings.llm_provider or None
        resolved_model = settings.llm_model or None

    if resolved_provider not in ("anthropic", "cliproxy"):
        return {
            "error": (
                f"prep guide generation requires provider 'anthropic' or 'cliproxy', "
                f"got '{resolved_provider}'"
            ),
            "progress_events": [
                {"node": "generate_guide", "status": "error",
                 "detail": f"unsupported provider: {resolved_provider}"}
            ],
        }

    # Build prompts
    system_prompt = _get_prompt(
        "prompt_generate_prep_guide", PROMPT_GENERATE_PREP_GUIDE, doc_type=""
    )

    round_num = state.get("round_number") or ""
    user_prompt_parts = [
        f"=== JOB DESCRIPTION ===\n{state.get('job_description') or '(none)'}",
        f"=== COMPANY ===\n{state.get('company') or '(none)'}",
        f"=== POSITION ===\n{state.get('position') or '(none)'}",
        (
            "=== INTERVIEW ROUND ===\n"
            f"Type: {state.get('round_type') or '(unknown)'}\n"
            f"Round number: {round_num}\n"
            f"Scheduled: {state.get('scheduled_at') or '(not scheduled)'}\n"
            f"Interviewers: {state.get('interviewer_names') or '(unknown)'}\n"
            f"Links:\n{state.get('interview_links') or '(none)'}\n"
            f"Prep notes:\n{state.get('interview_prep_notes') or '(none)'}"
        ),
        f"=== CANDIDATE CV (LaTeX) ===\n{state.get('cv_latex') or '(not available)'}",
        f"=== CANDIDATE COVER LETTER (LaTeX) ===\n{state.get('cover_letter_latex') or '(not available)'}",
        f"=== KB CONTEXT ===\n{state.get('kb_context_text') or '(none available)'}",
        (
            "Produce the complete preparation guide as valid markdown following the "
            "section structure described in the system prompt. Include flashcard fenced "
            "blocks (```flashcard ... ```) for every technical term worth reviewing."
        ),
    ]
    user_prompt = "\n\n".join(user_prompt_parts)

    events_before: list[dict] = [{"node": "generate_guide", "status": "start"}]

    try:
        result = await llm_call_with_trace(
            system_prompt,
            user_prompt,
            settings,
            provider=resolved_provider,
            model=resolved_model,
            tools=[_web_search_tool(max_uses=settings.prep_guide_max_web_searches)],
            thinking_budget=settings.prep_guide_thinking_budget,
        )
    except Exception as exc:
        return {
            "error": str(exc),
            "progress_events": events_before + [
                {"node": "generate_guide", "status": "error", "detail": str(exc)}
            ],
        }

    search_log = result.search_log or []
    thinking = result.thinking or ""

    return {
        "markdown": result.text,
        "thinking": thinking,
        "search_log": search_log,
        "generation_system_prompt": system_prompt,
        "generation_user_prompt": user_prompt,
        "progress_events": events_before + [
            {
                "node": "generate_guide",
                "status": "done",
                "searches_used": len(search_log),
                "thinking_chars": len(thinking),
            }
        ],
    }


async def finalize_prep_guide(state: PrepGuideState, settings: Settings | None = None) -> dict:
    """Persist the generated guide to the database."""
    settings = settings or Settings()

    if state.get("error"):
        return {
            "progress_events": [{"node": "finalize", "status": "error"}],
        }

    from jam.db import db_upsert_prep_guide

    interview_id = state.get("interview_id", "")
    search_log = state.get("search_log") or []
    thinking = state.get("thinking") or ""

    try:
        db_upsert_prep_guide(
            interview_id=interview_id,
            markdown_source=state.get("markdown") or "",
            generation_system_prompt=state.get("generation_system_prompt"),
            generation_user_prompt=state.get("generation_user_prompt"),
            web_search_log=json.dumps(search_log),
            thinking_summary=thinking,
            last_generated_at=datetime.now(tz=timezone.utc).isoformat(timespec="seconds"),
        )
    except Exception as exc:
        logger.error("finalize_prep_guide: db_upsert_prep_guide failed: %s", exc)
        return {
            "error": str(exc),
            "progress_events": [
                {"node": "finalize", "status": "error", "detail": str(exc)}
            ],
        }

    return {
        "progress_events": [{"node": "finalize", "status": "ok"}],
    }


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------


def build_prep_guide_graph():
    """Build the linear interview prep-guide LangGraph."""
    from langgraph.graph import END, START, StateGraph

    builder = StateGraph(PrepGuideState)
    builder.add_node("load_context", load_context)
    builder.add_node("generate_guide", generate_guide)
    builder.add_node("finalize", finalize_prep_guide)
    builder.add_edge(START, "load_context")
    builder.add_edge("load_context", "generate_guide")
    builder.add_edge("generate_guide", "finalize")
    builder.add_edge("finalize", END)
    return builder.compile()


# ---------------------------------------------------------------------------
# Public entry point (consumed by server.py for SSE streaming)
# ---------------------------------------------------------------------------


async def run_prep_guide_graph(
    initial_state: PrepGuideState,
    settings: Settings | None = None,
) -> AsyncIterator[dict]:
    """Stream SSE-shaped events from the prep-guide graph.

    Yields one event per node transition plus a final ``{node: "done", ...}``
    event that contains the full output or an error.

    The final event shape::

        {
            "node": "done",
            "markdown": str,
            "generation_system_prompt": str,
            "generation_user_prompt": str,
            "web_search_log": str,   # JSON-encoded list[dict]
            "thinking_summary": str,
            "error": str | None,
        }
    """
    settings = settings or Settings()

    # Inject settings into node callables via closure so the graph can pick
    # them up without needing LangGraph config injection.
    async def _load_context(st: PrepGuideState) -> dict:
        return await load_context(st, settings=settings)

    async def _generate_guide(st: PrepGuideState) -> dict:
        return await generate_guide(st, settings=settings)

    async def _finalize(st: PrepGuideState) -> dict:
        return await finalize_prep_guide(st, settings=settings)

    from langgraph.graph import END, START, StateGraph

    builder = StateGraph(PrepGuideState)
    builder.add_node("load_context", _load_context)
    builder.add_node("generate_guide", _generate_guide)
    builder.add_node("finalize", _finalize)
    builder.add_edge(START, "load_context")
    builder.add_edge("load_context", "generate_guide")
    builder.add_edge("generate_guide", "finalize")
    builder.add_edge("finalize", END)
    graph = builder.compile()

    final_state: PrepGuideState = {}  # type: ignore[assignment]
    async for chunk in graph.astream(initial_state):
        # chunk is {node_name: state_update}
        for node_name, state_update in chunk.items():
            final_state.update(state_update)
            for evt in state_update.get("progress_events", []):
                yield evt

    search_log = final_state.get("search_log") or []
    yield {
        "node": "done",
        "markdown": final_state.get("markdown") or "",
        "generation_system_prompt": final_state.get("generation_system_prompt") or "",
        "generation_user_prompt": final_state.get("generation_user_prompt") or "",
        "web_search_log": json.dumps(search_log),
        "thinking_summary": final_state.get("thinking") or "",
        "error": final_state.get("error") or None,
    }
