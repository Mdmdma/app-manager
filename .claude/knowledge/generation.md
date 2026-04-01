# generation Knowledge
<!-- source: jam/generation.py -->
<!-- hash: bab28a158df8 -->
<!-- updated: 2026-03-31 -->

## Public API

| Symbol | Type | Purpose |
|---|---|---|
| `DocumentGenerationState` | TypedDict | Full state schema for generation and critique graphs |
| `CompileError` | Exception | Raised when tectonic LaTeX compilation fails |
| `build_generation_graph()` | function | Construct and compile the full generation LangGraph |
| `build_critique_graph()` | function | Construct and compile the critique-only LangGraph (no generation/compilation) |
| `generation_graph` | CompiledGraph | Module-level compiled generation graph (reused across requests) |
| `critique_graph` | CompiledGraph | Module-level compiled critique graph (reused across requests) |
| `retrieve_kb_docs(state)` | async node | Fetch KB documents via semantic search + include namespaces |
| `generate_or_revise(state)` | async node | LLM call to populate template (first gen) or revise (subsequent) |
| `analyze_fit(state)` | async node | LLM call to assess job-fit and suggest improvements |
| `analyze_quality(state)` | async node | LLM call to check for AI-sounding phrases, vague claims, grammar |
| `apply_suggestions(state)` | async node | LLM call to apply fit + quality feedback to the LaTeX |
| `compile_and_check(state)` | async node | Compile LaTeX via tectonic, check page count |
| `reduce_size(state)` | async node | LLM call to shorten document to fit 1 page |
| `finalize(state)` | async node | Set `final_latex` from `current_latex` |
| `PROMPT_GENERATE_FIRST` | str constant | Default system prompt for first-time generation |
| `PROMPT_GENERATE_REVISE` | str constant | Default system prompt for revision |
| `PROMPT_ANALYZE_FIT` | str constant | Default system prompt for fit analysis |
| `PROMPT_ANALYZE_QUALITY` | str constant | Default system prompt for quality review |
| `PROMPT_APPLY_SUGGESTIONS` | str constant | Default system prompt for applying suggestions |
| `PROMPT_REDUCE_SIZE` | str constant | Default system prompt for size reduction |

## State TypedDict — `DocumentGenerationState`

### Inputs (set once before graph runs)
| Field | Type | Purpose |
|---|---|---|
| `doc_id` | `str` | Document UUID |
| `application_id` | `str` | Parent application UUID |
| `doc_type` | `str` | `"cv"` or `"cover_letter"` |
| `latex_template` | `str` | Original LaTeX source (unchanged reference) |
| `job_description` | `str` | Full job description text |
| `instructions_json` | `str` | `prompt_text` JSON from DB (sections with enabled flags) |
| `is_first_generation` | `bool` | True = populate template; False = revise existing |

### Image assets
| Field | Type | Purpose |
|---|---|---|
| `personal_photo` | `str` | Base64 data URI or "" |
| `personal_signature` | `str` | Base64 data URI or "" |

### Derived / populated during execution
| Field | Type | Purpose |
|---|---|---|
| `kb_docs` | `list[dict]` | KB documents fetched in `retrieve_kb_docs` |
| `inline_comments` | `list[str]` | Extracted from `% [COMMENT: ...]` markers in LaTeX |
| `locked_sections` | `list[str]` | Section keys where `enabled==False` in instructions JSON |

### Working copy
| Field | Type | Purpose |
|---|---|---|
| `current_latex` | `str` | Evolving LaTeX document through the pipeline |

### Agent outputs
| Field | Type | Purpose |
|---|---|---|
| `fit_feedback` | `str` | Fit analysis feedback from `analyze_fit` |
| `quality_feedback` | `str` | Quality review feedback from `analyze_quality` |

### Prompt transparency
| Field | Type | Purpose |
|---|---|---|
| `generation_system_prompt` | `str \| None` | System message sent to LLM during generation |
| `generation_user_prompt` | `str \| None` | User message sent to LLM (context + instructions) |

### Compile loop
| Field | Type | Purpose |
|---|---|---|
| `page_count` | `int` | Number of pages in compiled PDF |
| `compile_attempts` | `int` | Size-reduction attempts so far (max 3) |
| `compile_error` | `str \| None` | Tectonic error message if compilation failed |

### SSE progress
| Field | Type | Purpose |
|---|---|---|
| `progress_events` | `Annotated[list[dict], operator.add]` | Accumulated progress events (append-only via `operator.add` reducer) |

### Final output
| Field | Type | Purpose |
|---|---|---|
| `final_latex` | `str \| None` | Final LaTeX source after pipeline completes |
| `final_pdf` | `bytes \| None` | Compiled PDF bytes (set only when page_count <= 1) |
| `error` | `str \| None` | Error message if pipeline failed |

## Configurable System Prompts

All 6 LLM nodes read their system prompt from DB settings via `_get_prompt(key, default)`, falling back to module-level constants if no DB value exists. Users can customize prompts through the Settings UI.

| DB Key | Default Constant | Placeholders |
|---|---|---|
| `prompt_generate_first` | `PROMPT_GENERATE_FIRST` | `{locked_sections_notice}` |
| `prompt_generate_revise` | `PROMPT_GENERATE_REVISE` | `{locked_sections_notice}` |
| `prompt_analyze_fit` | `PROMPT_ANALYZE_FIT` | (none) |
| `prompt_analyze_quality` | `PROMPT_ANALYZE_QUALITY` | (none) |
| `prompt_apply_suggestions` | `PROMPT_APPLY_SUGGESTIONS` | `{locked_sections_notice}` |
| `prompt_reduce_size` | `PROMPT_REDUCE_SIZE` | `{locked_sections_notice}`, `{page_count}` |

Placeholders are resolved via `.format_map(defaultdict(str, ...))` — missing placeholders in custom prompts produce empty strings (no crash).

## Graph Nodes

### Generation graph (`build_generation_graph`)

Linear pipeline with a conditional compile loop:

```
retrieve_kb_docs
  → generate_or_revise
    → analyze_fit
      → analyze_quality
        → apply_suggestions
          → compile_and_check
            ├─ page_count <= 1 → finalize → END
            ├─ compile_attempts >= 3 → finalize → END
            ├─ error or compile_error → END (end_on_error)
            └─ page_count > 1 → reduce_size → compile_and_check (loop)
```

| Node | Role | LLM call? | Key behavior |
|---|---|---|---|
| `retrieve_kb_docs` | Fetch KB docs via search + include namespaces | No | Reads DB settings with Settings fallback; over-fetches by `padding`, trims to `n_results`; deduplicates by `doc_id`; extracts inline comments and locked sections; loads personal_photo and personal_signature from DB |
| `generate_or_revise` | Populate template (first gen) or revise (subsequent) | Yes | Two distinct prompt paths based on `is_first_generation`; strips markdown fences; restores locked sections; appends image hints if photo/signature available |
| `analyze_fit` | Assess job-fit, list 3-5 improvements | Yes | Truncates job description to 3000 chars, document to 6000 chars |
| `analyze_quality` | Check for AI phrases, vague claims, grammar | Yes | Truncates document to 6000 chars |
| `apply_suggestions` | Apply fit + quality feedback to LaTeX | Yes | Strips markdown fences; restores locked sections |
| `compile_and_check` | Compile via tectonic, measure pages | No | Skips if upstream error; passes images to `_compile_latex_bytes`; sets `final_pdf` + `final_latex` if page_count <= 1 |
| `reduce_size` | Shorten to fit 1 page | Yes | Increments `compile_attempts`; strips fences; restores locked sections |
| `finalize` | Copy `current_latex` to `final_latex` | No | Terminal node |

### Critique graph (`build_critique_graph`)

Subset pipeline for analysis-only (no generation, no compilation):

```
analyze_fit → analyze_quality → finalize → END
```

### Conditional routing — `_route_after_compile`

| Condition | Route |
|---|---|
| `state["error"]` is truthy | `end_on_error` (→ END) |
| `state["compile_error"]` is truthy | `end_on_error` (→ END) |
| `page_count <= 1` | `finalize` |
| `compile_attempts >= _MAX_SIZE_ATTEMPTS` (3) | `finalize` |
| Otherwise | `reduce_size` |

## Helper Functions (private)

| Function | Purpose |
|---|---|
| `_get_prompt(key, default)` | Load prompt template from DB settings, fall back to default constant |
| `_extract_inline_comments(latex)` | Parse `% [COMMENT: ...]` markers from LaTeX source |
| `_locked_sections(instructions_json)` | Return section keys where `enabled==False` |
| `_extract_kb_doc_content(doc)` | Extract text from KB doc (precedence: `text` > `content` > `summary+title` > `title`) |
| `_format_instructions(instructions_json)` | Format enabled sections for LLM prompt |
| `_restore_locked_sections(original, revised, keys, doc_type)` | Re-insert locked section content from original into revised LaTeX; uses `\section{}` for CV, `\paragraph{}` for cover letter |
| `_strip_latex_fences(text)` | Remove markdown code fences (``` ```latex ``` ```) that LLMs sometimes wrap around output |
| `_compile_latex_bytes(latex_source, images)` | Async tectonic subprocess; optionally writes base64 image data URIs as files; returns PDF bytes; raises `CompileError` |
| `_pdf_page_count(pdf_bytes)` | Count pages in PDF bytes via pymupdf/fitz |

## Constants

| Name | Value | Purpose |
|---|---|---|
| `_COMMENT_RE` | `r"%\s*\[COMMENT:\s*(.*?)\]"` | Regex for inline comment extraction |
| `_MAX_SIZE_ATTEMPTS` | `3` | Maximum reduce_size loop iterations |

## Dependencies

- **Imports from**: `jam.config` (Settings), `jam.db` (get_all_settings — lazy import in `retrieve_kb_docs` and `_get_prompt`), `jam.kb_client` (search_documents, list_namespace_documents — lazy import), `jam.llm` (llm_call — lazy import in all LLM nodes), `langgraph.graph` (StateGraph, END — lazy import in builders), `fitz` (pymupdf — page counting), `collections.defaultdict` (safe placeholder formatting)
- **Imported by**: `jam/server.py` (imports `generation_graph`, `critique_graph` lazily inside the generate endpoint; imports prompt constants in `/prompts/defaults` endpoint)

## KB Retrieval Settings Cascade

Settings are resolved with a DB-first, Settings-fallback pattern in `retrieve_kb_docs`:

1. `get_all_settings()` from `jam.db` (persisted user preferences)
2. `Settings()` from `jam.config` (environment variables)
3. Hardcoded defaults (`n_results=5`, `padding=0`, empty namespace lists)

Key settings: `kb_retrieval_namespaces` (JSON list), `kb_include_namespaces` (JSON list), `kb_retrieval_n_results` (int), `kb_retrieval_padding` (int).

## Testing

- **Unit file**: `tests/unit/test_generation.py`
- **Integration file**: `tests/integration/test_generation_kb_integration.py`
- **Mock targets** (patch at the lazy-import location):
  - `jam.db.get_all_settings` — KB settings lookup and prompt loading
  - `jam.kb_client.search_documents` — semantic search
  - `jam.kb_client.list_namespace_documents` — full namespace fetch
  - `jam.llm.llm_call` — all LLM calls (generation, analysis, suggestions, reduction)
  - `jam.generation.Settings` — when testing Settings fallback behavior

## Known Limitations

- `generation_graph` and `critique_graph` are compiled at module import time (line 759/781), which means `langgraph` must be importable whenever `jam.generation` is imported
- `Settings()` is instantiated per-call inside each LLM node (no caching or injection)
- KB context is hard-truncated to 6000 chars in `generate_or_revise` — long documents may lose context
- Job description is truncated to 500 chars for the search query, 3000 chars in the fit-analysis prompt
- `_compile_latex_bytes` requires `tectonic` system binary in PATH
- The reduce-size loop caps at 3 attempts; documents exceeding 1 page after 3 attempts proceed to finalize without a valid PDF
- All LLM nodes swallow exceptions and return partial state with error info rather than raising
- `_get_prompt` does a full `get_all_settings()` DB read per node invocation (no caching)
