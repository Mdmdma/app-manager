# generation Knowledge
<!-- source: jam/generation.py -->
<!-- hash: 60ee30d8f98a -->
<!-- updated: 2026-04-21 -->

## Public API

| Function | Signature | Purpose |
|---|---|---|
| `build_generation_graph` | `() -> CompiledGraph` | Build the full generation LangGraph (compiled once at import) |
| `build_critique_graph` | `() -> CompiledGraph` | Build the critique-only LangGraph (no generation/compilation) |
| `retrieve_kb_docs` | `async (state) -> dict` | Fetch KB docs via semantic search + namespace inclusion |
| `generate_or_revise` | `async (state) -> dict` | LLM: create or revise LaTeX using KB docs and feedback |
| `compile_and_check` | `async (state) -> dict` | Compile LaTeX via tectonic, count pages, always store PDF |
| `analyze_fit` | `async (state) -> dict` | LLM: evaluate document-to-job fit (3-5 improvements) |
| `analyze_quality` | `async (state) -> dict` | LLM: check for AI phrases, vague claims, grammar |
| `analyze_compress` | `async (state) -> dict` | LLM: recommend compression if page_count > 1; no-op if <= 1 |
| `finalize` | `async (state) -> dict` | Terminal node: copy current_latex to final_latex |
| `get_all_prompt_defaults` | `() -> dict[str, str]` | Return all 9 prompt defaults (shared + doc-type-specific + prep guide) for API |
| `build_prep_guide_graph` | `() -> CompiledGraph` | Build the interview prep-guide LangGraph (linear: load_context → generate_guide → finalize) |
| `load_context` | `async (state, settings=None) -> dict` | Fetch KB docs + trim to 6000 chars (prep-guide variant of retrieve_kb_docs) |
| `generate_guide` | `async (state, settings=None) -> dict` | Call `llm_call_with_trace` with web_search tool (100 uses) + extended thinking |
| `finalize_prep_guide` | `async (state, settings=None) -> dict` | Persist markdown + trace to `interview_prep_guides` via `db_upsert_prep_guide` |
| `run_prep_guide_graph` | `async (initial_state, settings=None) -> AsyncIterator[dict]` | SSE entry point for prep-guide generation; yields progress events + final `done` event |

### Internal helpers

| Function | Purpose |
|---|---|
| `_get_prompt(key, default, doc_type="")` | Load prompt via 4-tier resolution: typed DB → shared DB → typed hardcoded → shared default |
| `_resolve_step_model(step_key)` | Return `(provider, model)` override or `(None, None)` |
| `_extract_inline_comments(latex)` | Extract `% [COMMENT: ...]` markers |
| `_locked_sections(instructions_json)` | Return section keys where `enabled==False` |
| `_extract_kb_doc_content(doc)` | Extract usable text from KB doc (text -> content -> summary -> title) |
| `_format_instructions(instructions_json)` | Format enabled section instructions for LLM prompt |
| `_restore_locked_sections(original, revised, keys, doc_type)` | Re-insert locked section content from original into revised LaTeX |
| `_strip_latex_fences(text)` | Remove markdown code fences |
| `_compile_latex_bytes(latex, images?)` | Run tectonic subprocess, return PDF bytes |
| `_pdf_page_count(pdf_bytes)` | Count pages using pymupdf/fitz |
| `_route_after_compile(state)` | Conditional router: compact loop, parallel analysis fan-out, or END on error |
| `_parse_prep_guide_model(settings)` | Parse `step_model_generate_prep_guide` (`"provider:model"`) → `(provider, model)` |
| `_parse_namespaces(raw)` | JSON-decode a namespace list string, returning `[]` on error |

## Key Constants / Schema

### Module-level

| Constant | Value | Purpose |
|---|---|---|
| `CompileError` | Exception class | Raised by `_compile_latex_bytes` on tectonic failure |
| `_COMMENT_RE` | `r"%\s*\[COMMENT:\s*(.*?)\]"` | Regex for inline comment extraction |

### Prompt constants (DB-configurable, doc-type-aware)

**Shared-only prompts (no doc-type variants):**

| Constant | DB Key | Placeholders |
|---|---|---|
| `PROMPT_ANALYZE_FIT` | `prompt_analyze_fit` | (none) |
| `PROMPT_ANALYZE_COMPRESS` | `prompt_analyze_compress` | `{page_count}`, `{compact_iteration}`, `{max_compact_iterations}`, `{locked_sections_notice}` |
| `PROMPT_GENERATE_PREP_GUIDE` | `prompt_generate_prep_guide` | (none) — scaffold for interview prep guide markdown, instructs the model to use web_search + extended thinking to produce 9 sections including `flashcard` fenced blocks |

**Doc-type-specific prompts (6 constants, no shared fallback):**

| Constant | DB Key | Doc Type |
|---|---|---|
| `PROMPT_GENERATE_FIRST_CV` | `prompt_generate_first:cv` | CV |
| `PROMPT_GENERATE_FIRST_CL` | `prompt_generate_first:cover_letter` | Cover letter |
| `PROMPT_GENERATE_REVISE_CV` | `prompt_generate_revise:cv` | CV |
| `PROMPT_GENERATE_REVISE_CL` | `prompt_generate_revise:cover_letter` | Cover letter |
| `PROMPT_ANALYZE_QUALITY_CV` | `prompt_analyze_quality:cv` | CV |
| `PROMPT_ANALYZE_QUALITY_CL` | `prompt_analyze_quality:cover_letter` | Cover letter |

Doc-type prompts enforce: only use retrieved KB information, avoid AI-sounding text (emdashes, complex sentences, filler phrases).

**Resolution** (`_get_prompt`): two modes based on whether `_PROMPT_DEFAULTS` has an entry for the key:
- Split prompts: typed DB (`key:doc_type`) → typed hardcoded default. No shared DB fallback.
- Shared prompts: shared DB (`key`) → shared hardcoded default.

**`_PROMPT_DEFAULTS`** dict maps 3 base keys to `{doc_type: constant}` for the split prompts only.

**`get_all_prompt_defaults()`** — public helper returning all 9 keys (3 shared + 6 typed) for the API. The 9th key is `prompt_generate_prep_guide`.

Per-step model override keys: `step_model_generate_or_revise`, `step_model_analyze_fit`, `step_model_analyze_quality`, `step_model_analyze_compress`, `step_model_generate_prep_guide`

### `DocumentGenerationState` TypedDict

| Field | Type | Purpose |
|---|---|---|
| `doc_id` | `str` | Document UUID |
| `application_id` | `str` | Parent application UUID |
| `doc_type` | `str` | `"cv"` or `"cover_letter"` |
| `latex_template` | `str` | Original LaTeX source (unchanged reference) |
| `job_description` | `str` | Full job description text |
| `instructions_json` | `str` | prompt_text JSON from DB |
| `is_first_generation` | `bool` | True = first gen, False = revision |
| `personal_photo` | `str` | Base64 data URI or `""` |
| `personal_signature` | `str` | Base64 data URI or `""` |
| `kb_docs` | `list[dict]` | Retrieved KB documents |
| `inline_comments` | `list[str]` | Extracted `% [COMMENT: ...]` markers |
| `locked_sections` | `list[str]` | Section keys where `enabled==False` |
| `current_latex` | `str` | Mutable working copy of LaTeX |
| `fit_feedback` | `str` | Output from `analyze_fit` |
| `quality_feedback` | `str` | Output from `analyze_quality` |
| `compress_feedback` | `str` | Output from `analyze_compress` (empty if <= 1 page) |
| `generation_system_prompt` | `str \| None` | System prompt sent to LLM (transparency) |
| `generation_user_prompt` | `str \| None` | User prompt sent to LLM (transparency) |
| `compact_iteration` | `int` | Current compact-loop iteration (starts 0, incremented by analyze_compress) |
| `max_compact_iterations` | `int` | Max compact-loop iterations (default 3) |
| `page_count` | `int` | PDF page count from compilation |
| `compile_error` | `str \| None` | Error message from tectonic |
| `progress_events` | `Annotated[list[dict], operator.add]` | SSE progress (accumulated) |
| `final_latex` | `str \| None` | Final LaTeX output |
| `final_pdf` | `bytes \| None` | Final PDF bytes |
| `error` | `str \| None` | Pipeline error message |

### Graph topology

**Generation graph (with compact loop):**
```
retrieve_kb_docs -> generate_or_revise -> compile_and_check
  -> _route_after_compile:
       if page_count > 1 AND compact_iteration < max: -> analyze_compress -> generate_or_revise (LOOP)
       else: -> fan-out: [analyze_fit || analyze_quality]
       on error: -> END
  -> finalize -> END
```

- `compile_and_check` always sets `final_pdf` and `final_latex` regardless of page count
- `_route_after_compile` returns `END` on error/compile_error, `"analyze_compress"` for compact loop, or `["analyze_fit", "analyze_quality"]` for parallel fan-out
- `analyze_compress` increments `compact_iteration` and loops back to `generate_or_revise`; escalates aggressiveness on later iterations
- `analyze_compress` is a no-op (returns empty feedback) when `page_count <= 1`
- LangGraph fan-in: `finalize` waits for both `analyze_fit` and `analyze_quality` before running

**Critique graph:**
```
analyze_fit -> analyze_quality -> finalize -> END
```

**Prep-guide graph (separate, linear):**
```
load_context -> generate_guide -> finalize_prep_guide -> END
```

- Single LLM call in `generate_guide` using `llm_call_with_trace` (from `jam.llm`) with `tools=[_web_search_tool(max_uses=settings.prep_guide_max_web_searches)]` (default 100) and `thinking_budget=settings.prep_guide_thinking_budget` (default 16000).
- Gated on `llm_provider in ("anthropic","cliproxy")` — other providers raise `ValueError` at the `llm_call_with_trace` boundary. `generate_guide` also has a defensive check and writes to `state["error"]` instead of propagating.
- Model can be overridden via `step_model_generate_prep_guide` (format `"provider:model"`).
- `finalize_prep_guide` calls `db_upsert_prep_guide(interview_id, markdown_source, generation_system_prompt, generation_user_prompt, web_search_log=json.dumps(search_log), thinking_summary, last_generated_at=datetime.utcnow().isoformat())`.

### Node details

- `retrieve_kb_docs`: 3-tier settings cascade (DB -> Settings env -> hardcoded defaults) for KB config. Over-fetches by padding, deduplicates by doc_id. **Skips calls entirely when their namespace list is empty** — only builds coroutines for configured sources. Uses `asyncio.gather()` to run whichever of `search_documents` / `list_namespace_documents` are needed concurrently (with `return_exceptions=True`).
- `generate_or_revise`: Three branches: (1) First gen (`is_first_generation` AND `compact_iteration == 0`) uses `PROMPT_GENERATE_FIRST` + template; (2) Compact loop (`compact_iteration > 0`) uses inline compression-focused prompt with only compress recommendations + current LaTeX (no KB docs, no job description); (3) User-triggered revision uses `PROMPT_GENERATE_REVISE` + full context. All branches restore locked sections after LLM call.
- `compile_and_check`: Calls `_compile_latex_bytes()` with optional images dict. Always stores `final_pdf` and `final_latex` in state.
- `analyze_fit`: Truncates job desc to 3000 chars, document to 6000 chars.
- `analyze_quality`: Truncates document to 6000 chars.
- `analyze_compress`: Skips LLM call when `page_count <= 1`. Otherwise provides text recommendations for compression. Increments `compact_iteration`. Escalates aggressiveness: standard on pass 1, "be more aggressive" on pass 2, "FINAL ATTEMPT" on pass 3+.
- `finalize`: Sets `final_latex` from `current_latex`.

### `PrepGuideState` TypedDict (total=False)

Inputs set by caller: `interview_id`, `application_id`, `job_description`, `company`, `position`, `round_type`, `round_number`, `interviewer_names`, `interview_links`, `interview_prep_notes`, `scheduled_at`, `cv_latex`, `cover_letter_latex`.

Populated by nodes: `kb_docs`, `kb_context_text` (trimmed 6000), `markdown`, `thinking`, `search_log`, `generation_system_prompt`, `generation_user_prompt`, `progress_events` (Annotated accumulator), `error`.

### `run_prep_guide_graph` SSE event shape

Each node emits one or more progress events; final event:

```python
{
    "node": "done",
    "markdown": str,
    "generation_system_prompt": str,
    "generation_user_prompt": str,
    "web_search_log": str,        # JSON-encoded list[{query, url, title}]
    "thinking_summary": str,
    "error": str | None,
}
```

## Dependencies

- Imports from: `jam.config` (Settings), `jam.db` (get_all_settings, db_upsert_prep_guide -- lazy), `jam.llm` (llm_call, llm_call_with_trace, _web_search_tool -- lazy), `jam.kb_client` (search_documents, list_namespace_documents -- lazy), `langgraph` (StateGraph, END -- lazy), `fitz` (pymupdf)
- Imported by: `jam/server.py` (generation_graph, critique_graph, prompt constants, `run_prep_guide_graph`, `PrepGuideState`)

## Testing

- Files: `tests/unit/test_generation.py`, `tests/unit/test_generation_prep_guide.py`
- Mock targets: `jam.generation.llm_call`, `jam.generation.llm_call_with_trace`, `jam.generation.get_all_settings`, `jam.generation.search_documents`, `jam.generation.list_namespace_documents`, `jam.generation._compile_latex_bytes`, `jam.generation._pdf_page_count`, `jam.generation.db_upsert_prep_guide`, `shutil.which`
- Pattern: Each test constructs a `_base_state()` dict, patches LLM/KB calls, and asserts on returned state updates

## Known Limitations

- KB context hard-capped at 6000 chars in generate_or_revise
- Job description truncated to 500 chars for KB search query
- Per-node exception swallowing -- LLM nodes return partial state rather than raising
- Compact loop runs up to 3 iterations per pipeline invocation (configurable via `max_compact_iterations`)
- Graph compiled at import time -- langgraph must be importable
- Prep-guide pipeline is Anthropic/cliproxy-only (needs server-side `web_search_20250305` tool + extended thinking). Server must gate the generate endpoint on `llm_provider` before invoking.
- Prep-guide KB context uses the same 6000-char cap as CV/CL.
