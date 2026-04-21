# generation Knowledge
<!-- source: jam/generation.py -->
<!-- hash: 90e8b0a26a41 -->
<!-- updated: 2026-04-02 -->

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
| `get_all_prompt_defaults` | `() -> dict[str, str]` | Return all 11 prompt defaults (shared + doc-type-specific) for API |

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

**`get_all_prompt_defaults()`** — public helper returning all 8 keys (2 shared + 6 typed) for the API.

Per-step model override keys: `step_model_generate_or_revise`, `step_model_analyze_fit`, `step_model_analyze_quality`, `step_model_analyze_compress`

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

### Node details

- `retrieve_kb_docs`: 3-tier settings cascade (DB -> Settings env -> hardcoded defaults) for KB config. Over-fetches by padding, deduplicates by doc_id. **Skips calls entirely when their namespace list is empty** — only builds coroutines for configured sources. Uses `asyncio.gather()` to run whichever of `search_documents` / `list_namespace_documents` are needed concurrently (with `return_exceptions=True`).
- `generate_or_revise`: Three branches: (1) First gen (`is_first_generation` AND `compact_iteration == 0`) uses `PROMPT_GENERATE_FIRST` + template; (2) Compact loop (`compact_iteration > 0`) uses inline compression-focused prompt with only compress recommendations + current LaTeX (no KB docs, no job description); (3) User-triggered revision uses `PROMPT_GENERATE_REVISE` + full context. All branches restore locked sections after LLM call.
- `compile_and_check`: Calls `_compile_latex_bytes()` with optional images dict. Always stores `final_pdf` and `final_latex` in state.
- `analyze_fit`: Truncates job desc to 3000 chars, document to 6000 chars.
- `analyze_quality`: Truncates document to 6000 chars.
- `analyze_compress`: Skips LLM call when `page_count <= 1`. Otherwise provides text recommendations for compression. Increments `compact_iteration`. Escalates aggressiveness: standard on pass 1, "be more aggressive" on pass 2, "FINAL ATTEMPT" on pass 3+.
- `finalize`: Sets `final_latex` from `current_latex`.

## Dependencies

- Imports from: `jam.config` (Settings), `jam.db` (get_all_settings -- lazy), `jam.llm` (llm_call -- lazy), `jam.kb_client` (search_documents, list_namespace_documents -- lazy), `langgraph` (StateGraph, END -- lazy), `fitz` (pymupdf)
- Imported by: `jam/server.py` (generation_graph, critique_graph, prompt constants)

## Testing

- File: `tests/unit/test_generation.py`
- Mock targets: `jam.generation.llm_call`, `jam.generation.get_all_settings`, `jam.generation.search_documents`, `jam.generation.list_namespace_documents`, `jam.generation._compile_latex_bytes`, `jam.generation._pdf_page_count`, `shutil.which`
- Pattern: Each test constructs a `_base_state()` dict, patches LLM/KB calls, and asserts on returned state updates

## Known Limitations

- KB context hard-capped at 6000 chars in generate_or_revise
- Job description truncated to 500 chars for KB search query
- Per-node exception swallowing -- LLM nodes return partial state rather than raising
- Compact loop runs up to 3 iterations per pipeline invocation (configurable via `max_compact_iterations`)
- Graph compiled at import time -- langgraph must be importable
