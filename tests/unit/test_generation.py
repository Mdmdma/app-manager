"""Unit tests for jam.generation — LangGraph document generation workflow."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from jam.generation import (
    PROMPT_ANALYZE_COMPRESS,
    PROMPT_ANALYZE_FIT,
    PROMPT_ANALYZE_QUALITY_CL,
    PROMPT_ANALYZE_QUALITY_CV,
    PROMPT_GENERATE_FIRST_CL,
    PROMPT_GENERATE_FIRST_CV,
    PROMPT_GENERATE_REVISE_CL,
    PROMPT_GENERATE_REVISE_CV,
    _compile_latex_bytes,
    _extract_inline_comments,
    _extract_kb_doc_content,
    _format_instructions,
    _get_prompt,
    _locked_sections,
    _resolve_step_model,
    _restore_locked_sections,
    _route_after_compile,
    _strip_latex_fences,
    analyze_compress,
    analyze_fit,
    analyze_quality,
    build_critique_graph,
    build_generation_graph,
    compile_and_check,
    generate_or_revise,
    get_all_prompt_defaults,
    retrieve_kb_docs,
)


# ── _extract_inline_comments ─────────────────────────────────────────────────


def test_extract_inline_comments_basic():
    latex = r"""
\section{Summary}
Some text here.
% [COMMENT: shorten this paragraph]
More text.
% [COMMENT: add quantified achievements]
"""
    comments = _extract_inline_comments(latex)
    assert comments == ["shorten this paragraph", "add quantified achievements"]


def test_extract_inline_comments_empty():
    latex = r"\section{Summary}\nSome text with no comments."
    assert _extract_inline_comments(latex) == []


def test_extract_inline_comments_case_insensitive():
    latex = "% [comment: lowercase works too]"
    comments = _extract_inline_comments(latex)
    assert comments == ["lowercase works too"]


def test_extract_inline_comments_whitespace_trimmed():
    latex = "%  [COMMENT:   spaces around   ]"
    comments = _extract_inline_comments(latex)
    assert comments == ["spaces around"]


# ── _locked_sections ─────────────────────────────────────────────────────────


def test_locked_sections_parses_json():
    data = json.dumps({
        "general": "",
        "sections": [
            {"key": "Summary", "label": "Summary", "text": "", "enabled": False},
            {"key": "Experience", "label": "Experience", "text": "", "enabled": True},
            {"key": "Skills", "label": "Skills", "text": "", "enabled": False},
        ],
    })
    result = _locked_sections(data)
    assert result == ["Summary", "Skills"]


def test_locked_sections_all_enabled():
    data = json.dumps({
        "sections": [
            {"key": "A", "enabled": True},
            {"key": "B", "enabled": True},
        ]
    })
    assert _locked_sections(data) == []


def test_locked_sections_invalid_json():
    assert _locked_sections("not json") == []


def test_locked_sections_empty_string():
    assert _locked_sections("") == []


def test_locked_sections_missing_enabled_defaults_to_unlocked():
    data = json.dumps({"sections": [{"key": "A"}]})
    assert _locked_sections(data) == []


# ── _format_instructions ─────────────────────────────────────────────────────


def test_format_instructions_includes_enabled_sections():
    data = json.dumps({
        "general": "Keep it concise",
        "sections": [
            {"key": "Summary", "label": "Summary", "text": "Focus on Python", "enabled": True},
            {"key": "Skills", "label": "Skills", "text": "Add TypeScript", "enabled": True},
        ],
    })
    result = _format_instructions(data)
    assert "Keep it concise" in result
    assert "Focus on Python" in result
    assert "Add TypeScript" in result


def test_format_instructions_skips_disabled_sections():
    data = json.dumps({
        "general": "",
        "sections": [
            {"key": "Summary", "label": "Summary", "text": "Don't change me", "enabled": False},
            {"key": "Skills", "label": "Skills", "text": "Add Go", "enabled": True},
        ],
    })
    result = _format_instructions(data)
    assert "Don't change me" not in result
    assert "Add Go" in result


def test_format_instructions_skips_empty_text():
    data = json.dumps({
        "general": "",
        "sections": [
            {"key": "Summary", "label": "Summary", "text": "", "enabled": True},
        ],
    })
    assert _format_instructions(data) == ""


def test_format_instructions_invalid_json():
    assert _format_instructions("garbage") == ""


# ── _restore_locked_sections ─────────────────────────────────────────────────


def test_restore_locked_sections_cv_preserves_locked():
    original = r"""
\section{Summary}
Original summary content here.
\section{Experience}
Original experience.
"""
    revised = r"""
\section{Summary}
AI-generated summary that replaced the original.
\section{Experience}
Updated experience section.
"""
    result = _restore_locked_sections(original, revised, ["Summary"], "cv")
    assert "Original summary content here" in result
    assert "AI-generated summary that replaced the original" not in result
    # Non-locked section should be revised
    assert "Updated experience section" in result


def test_restore_locked_sections_no_locked_returns_revised():
    original = r"\section{A}Original.\section{B}Also original."
    revised = r"\section{A}Revised.\section{B}Also revised."
    result = _restore_locked_sections(original, revised, [], "cv")
    assert result == revised


def test_restore_locked_sections_cover_letter_uses_paragraph():
    original = r"""
\paragraph{Opening}
Original opening paragraph.
\paragraph{Body}
Original body.
"""
    revised = r"""
\paragraph{Opening}
AI-generated opening.
\paragraph{Body}
AI-generated body.
"""
    result = _restore_locked_sections(original, revised, ["Opening"], "cover_letter")
    assert "Original opening paragraph" in result
    assert "AI-generated opening" not in result
    assert "AI-generated body" in result


def test_restore_locked_sections_missing_section_leaves_revised_unchanged():
    """If locked section key doesn't exist in original, don't crash."""
    original = r"\section{Summary}Some content."
    revised = r"\section{Summary}Revised."
    # "NonExistent" key is locked but doesn't exist in original — should be no-op
    result = _restore_locked_sections(original, revised, ["NonExistent"], "cv")
    assert result == revised


# ── _strip_latex_fences ──────────────────────────────────────────────────────


def test_strip_latex_fences_removes_latex_fence():
    assert _strip_latex_fences("```latex\n\\documentclass\n```") == "\\documentclass"


def test_strip_latex_fences_removes_tex_fence():
    assert _strip_latex_fences("```tex\n\\documentclass\n```") == "\\documentclass"


def test_strip_latex_fences_removes_bare_fence():
    assert _strip_latex_fences("```\n\\documentclass\n```") == "\\documentclass"


def test_strip_latex_fences_passthrough_plain():
    assert _strip_latex_fences("\\documentclass") == "\\documentclass"


# ── build_generation_graph ───────────────────────────────────────────────────


def test_build_generation_graph_structure():
    """Graph should compile and contain all expected nodes."""
    graph = build_generation_graph()
    node_names = set(graph.get_graph().nodes.keys())
    expected = {
        "retrieve_kb_docs",
        "generate_or_revise",
        "compile_and_check",
        "analyze_fit",
        "analyze_quality",
        "analyze_compress",
        "finalize",
    }
    assert expected.issubset(node_names)
    # Deleted nodes must NOT be present
    assert "apply_suggestions" not in node_names
    assert "reduce_size" not in node_names


def test_build_critique_graph_structure():
    """Critique graph should only contain analysis and finalize nodes (no generation)."""
    graph = build_critique_graph()
    node_names = set(graph.get_graph().nodes.keys())
    expected = {"analyze_fit", "analyze_quality", "finalize"}
    assert expected.issubset(node_names)
    # Generation and compilation nodes must NOT be present
    assert "retrieve_kb_docs" not in node_names
    assert "generate_or_revise" not in node_names
    assert "apply_suggestions" not in node_names
    assert "compile_and_check" not in node_names


# ── retrieve_kb_docs ─────────────────────────────────────────────────────────

def _base_state(**overrides):
    state = {
        "doc_id": "doc-1",
        "application_id": "app-1",
        "doc_type": "cv",
        "latex_template": r"\section{Summary}Placeholder",
        "job_description": "Python backend engineer at ACME Corp",
        "instructions_json": "",
        "is_first_generation": True,
        "kb_docs": [],
        "inline_comments": [],
        "locked_sections": [],
        "personal_photo": "",
        "personal_signature": "",
        "current_latex": "",
        "fit_feedback": "",
        "quality_feedback": "",
        "compress_feedback": "",
        "compact_iteration": 0,
        "max_compact_iterations": 3,
        "page_count": 0,
        "compile_error": None,
        "progress_events": [],
        "final_latex": None,
        "final_pdf": None,
        "error": None,
    }
    state.update(overrides)
    return state


@pytest.mark.asyncio
async def test_retrieve_kb_docs_uses_db_settings():
    """retrieve_kb_docs should read persisted settings and pass them through."""
    stored = {
        "kb_retrieval_namespaces": json.dumps(["my-ns"]),
        "kb_include_namespaces": "[]",
        "kb_retrieval_n_results": "10",
    }
    search_results = [{"id": "r1", "content": "result 1"}]

    with patch("jam.db.get_all_settings", return_value=stored) as mock_settings, \
         patch("jam.kb_client.search_documents", new_callable=AsyncMock, return_value=search_results) as mock_search, \
         patch("jam.kb_client.list_namespace_documents", new_callable=AsyncMock) as mock_list:

        result = await retrieve_kb_docs(_base_state())

    mock_settings.assert_called_once()
    mock_search.assert_called_once()
    call_kwargs = mock_search.call_args
    assert call_kwargs[1]["n_results"] == 10
    assert call_kwargs[1]["namespace_ids"] == ["my-ns"]
    mock_list.assert_not_called()  # no include namespaces
    assert result["kb_docs"] == search_results


@pytest.mark.asyncio
async def test_retrieve_kb_docs_includes_full_namespaces():
    """When kb_include_namespaces is set, those docs are fetched.
    When search_ns is empty, search_documents is skipped entirely."""
    stored = {
        "kb_retrieval_namespaces": "[]",
        "kb_include_namespaces": json.dumps(["personal-info"]),
        "kb_retrieval_n_results": "5",
    }
    include_docs = [{"doc_id": "i1", "text": "included doc"}]

    with patch("jam.db.get_all_settings", return_value=stored), \
         patch("jam.kb_client.search_documents", new_callable=AsyncMock) as mock_search, \
         patch("jam.kb_client.list_namespace_documents", new_callable=AsyncMock, return_value=include_docs) as mock_list:

        result = await retrieve_kb_docs(_base_state())

    mock_search.assert_not_called()
    mock_list.assert_called_once()
    assert mock_list.call_args[0][0] == ["personal-info"]
    assert len(result["kb_docs"]) == 1
    assert result["kb_docs"][0]["doc_id"] == "i1"


@pytest.mark.asyncio
async def test_retrieve_kb_docs_deduplicates_by_doc_id():
    """Search results from docs already included should be deduplicated."""
    stored = {
        "kb_retrieval_namespaces": json.dumps(["ns-a"]),
        "kb_include_namespaces": json.dumps(["ns-a"]),
        "kb_retrieval_n_results": "5",
    }
    # Include returns chunks with doc_id (real search API format)
    include_docs = [{"doc_id": "dup-1", "text": "included chunk", "chunk_index": 0}]
    # Search also returns a chunk from the same document, plus a unique one
    search_results = [
        {"doc_id": "dup-1", "text": "search chunk", "chunk_index": 1},
        {"doc_id": "unique-s", "text": "only in search", "chunk_index": 0},
    ]

    with patch("jam.db.get_all_settings", return_value=stored), \
         patch("jam.kb_client.search_documents", new_callable=AsyncMock, return_value=search_results), \
         patch("jam.kb_client.list_namespace_documents", new_callable=AsyncMock, return_value=include_docs):

        result = await retrieve_kb_docs(_base_state())

    doc_ids = [d.get("doc_id") or d.get("id") for d in result["kb_docs"]]
    # dup-1 should appear once (from include), not duplicated from search
    assert doc_ids.count("dup-1") == 1
    assert "unique-s" in doc_ids


@pytest.mark.asyncio
async def test_retrieve_kb_docs_defaults_when_no_settings():
    """When DB has no KB settings and no env overrides, both namespace lists are empty
    so neither search_documents nor list_namespace_documents are called."""
    with patch("jam.db.get_all_settings", return_value={}), \
         patch("jam.kb_client.search_documents", new_callable=AsyncMock, return_value=[]) as mock_search, \
         patch("jam.kb_client.list_namespace_documents", new_callable=AsyncMock) as mock_list:

        result = await retrieve_kb_docs(_base_state())

    mock_search.assert_not_called()
    mock_list.assert_not_called()
    assert result["kb_docs"] == []


@pytest.mark.asyncio
async def test_retrieve_kb_docs_progress_event_detail():
    """Progress event should report include count when only include namespace is configured.
    With search_ns empty, search_documents is skipped (0 searched)."""
    stored = {
        "kb_retrieval_namespaces": "[]",
        "kb_include_namespaces": json.dumps(["personal"]),
        "kb_retrieval_n_results": "3",
    }

    with patch("jam.db.get_all_settings", return_value=stored), \
         patch("jam.kb_client.search_documents", new_callable=AsyncMock) as mock_search, \
         patch("jam.kb_client.list_namespace_documents", new_callable=AsyncMock, return_value=[{"doc_id": "i1", "text": "b"}]):

        result = await retrieve_kb_docs(_base_state())

    mock_search.assert_not_called()
    evt = result["progress_events"][0]
    assert evt["status"] == "done"
    assert "1 KB docs" in evt["detail"]
    assert "0 searched" in evt["detail"]
    assert "1 included" in evt["detail"]


@pytest.mark.asyncio
async def test_retrieve_kb_docs_includes_all_chunks_from_namespace():
    """All chunks from include namespaces must appear in merged results, keyed by doc_id.
    When search_ns is empty, search_documents is skipped so only include chunks appear."""
    stored = {
        "kb_retrieval_namespaces": "[]",
        "kb_include_namespaces": json.dumps(["academic-record"]),
        "kb_retrieval_n_results": "3",
    }
    # Simulate 2 documents with multiple chunks each (real search API format)
    include_docs = [
        {"doc_id": "doc-bachelor", "text": "Bachelor chunk 0", "chunk_index": 0},
        {"doc_id": "doc-bachelor", "text": "Bachelor chunk 1", "chunk_index": 1},
        {"doc_id": "doc-master", "text": "Master chunk 0", "chunk_index": 0},
        {"doc_id": "doc-master", "text": "Master chunk 1", "chunk_index": 1},
    ]

    with patch("jam.db.get_all_settings", return_value=stored), \
         patch("jam.kb_client.search_documents", new_callable=AsyncMock) as mock_search, \
         patch("jam.kb_client.list_namespace_documents", new_callable=AsyncMock, return_value=include_docs):

        result = await retrieve_kb_docs(_base_state())

    mock_search.assert_not_called()
    docs = result["kb_docs"]
    # All 4 include chunks (search is skipped when search_ns is empty)
    assert len(docs) == 4
    assert docs[0]["text"] == "Bachelor chunk 0"
    assert docs[1]["text"] == "Bachelor chunk 1"
    assert docs[2]["text"] == "Master chunk 0"
    assert docs[3]["text"] == "Master chunk 1"


@pytest.mark.asyncio
async def test_retrieve_kb_docs_padding_over_fetch_then_trim():
    """When padding is set, should fetch n_results + padding, then trim back to n_results.
    A search namespace must be configured for search_documents to be called."""
    stored = {
        "kb_retrieval_namespaces": json.dumps(["ns-search"]),
        "kb_include_namespaces": "[]",
        "kb_retrieval_n_results": "3",
        "kb_retrieval_padding": "2",
    }
    # API returns 5 results (3 + 2 padding)
    search_results = [
        {"id": f"result-{i}", "content": f"result {i}"}
        for i in range(5)
    ]

    with patch("jam.db.get_all_settings", return_value=stored), \
         patch("jam.kb_client.search_documents", new_callable=AsyncMock, return_value=search_results) as mock_search, \
         patch("jam.kb_client.list_namespace_documents", new_callable=AsyncMock):

        result = await retrieve_kb_docs(_base_state())

    # Should have requested 5 (3 + 2), but only kept 3
    mock_search.assert_called_once()
    assert mock_search.call_args[1]["n_results"] == 5
    assert len(result["kb_docs"]) == 3
    assert result["kb_docs"][-1]["id"] == "result-2"


@pytest.mark.asyncio
async def test_retrieve_kb_docs_settings_fallback_when_db_empty():
    """When DB has no KB settings, should fall back to Settings (env var) values."""
    with patch("jam.db.get_all_settings", return_value={}), \
         patch("jam.generation.Settings") as mock_settings_class, \
         patch("jam.kb_client.search_documents", new_callable=AsyncMock, return_value=[]) as mock_search, \
         patch("jam.kb_client.list_namespace_documents", new_callable=AsyncMock) as mock_list:

        # Mock Settings instance to have env var values
        mock_instance = mock_settings_class.return_value
        mock_instance.kb_retrieval_namespaces = json.dumps(["env-ns"])
        mock_instance.kb_include_namespaces = json.dumps(["env-include"])
        mock_instance.kb_retrieval_n_results = 7
        mock_instance.kb_retrieval_padding = 1
        mock_instance.kb_api_url = "http://localhost:8000/api/v1"

        result = await retrieve_kb_docs(_base_state())

    # Should use Settings fallback values since DB is empty
    mock_search.assert_called_once()
    assert mock_search.call_args[1]["n_results"] == 8  # 7 + 1 padding
    assert mock_search.call_args[1]["namespace_ids"] == ["env-ns"]
    mock_list.assert_called_once()
    assert mock_list.call_args[0][0] == ["env-include"]


@pytest.mark.asyncio
async def test_retrieve_kb_docs_db_takes_precedence_over_settings():
    """When DB has values, they should take precedence over Settings env vars."""
    stored = {
        "kb_retrieval_namespaces": json.dumps(["db-ns"]),
        "kb_include_namespaces": json.dumps(["db-include"]),
        "kb_retrieval_n_results": "4",
        "kb_retrieval_padding": "0",
    }

    with patch("jam.db.get_all_settings", return_value=stored), \
         patch("jam.generation.Settings") as mock_settings_class, \
         patch("jam.kb_client.search_documents", new_callable=AsyncMock, return_value=[]) as mock_search, \
         patch("jam.kb_client.list_namespace_documents", new_callable=AsyncMock) as mock_list:

        # Mock Settings instance with different values
        mock_instance = mock_settings_class.return_value
        mock_instance.kb_retrieval_namespaces = json.dumps(["env-ns"])
        mock_instance.kb_include_namespaces = json.dumps(["env-include"])
        mock_instance.kb_retrieval_n_results = 99
        mock_instance.kb_retrieval_padding = 99
        mock_instance.kb_api_url = "http://localhost:8000/api/v1"

        result = await retrieve_kb_docs(_base_state())

    # Should use DB values, not Settings
    mock_search.assert_called_once()
    assert mock_search.call_args[1]["n_results"] == 4  # DB value, not Settings 99
    assert mock_search.call_args[1]["namespace_ids"] == ["db-ns"]
    mock_list.assert_called_once()
    assert mock_list.call_args[0][0] == ["db-include"]


# ── _extract_kb_doc_content ──────────────────────────────────────────────────


def test_extract_kb_doc_content_from_search_text_field():
    """Should prefer 'text' field from semantic search results."""
    doc = {"text": "Full document content from search", "summary": "Just a summary"}
    content = _extract_kb_doc_content(doc)
    assert content == "Full document content from search"


def test_extract_kb_doc_content_from_content_field():
    """Should fall back to 'content' field if available."""
    doc = {"content": "Direct content field"}
    content = _extract_kb_doc_content(doc)
    assert content == "Direct content field"


def test_extract_kb_doc_content_from_summary_with_title():
    """Should use 'summary' + 'title' from list_namespace_documents."""
    doc = {"title": "Document Title", "summary": "Summary of document"}
    content = _extract_kb_doc_content(doc)
    assert "Document Title" in content
    assert "Summary of document" in content


def test_extract_kb_doc_content_title_only():
    """Should fall back to title if no summary."""
    doc = {"title": "Just A Title"}
    content = _extract_kb_doc_content(doc)
    assert content == "Just A Title"


def test_extract_kb_doc_content_empty_doc():
    """Should return empty string for empty doc."""
    doc = {}
    content = _extract_kb_doc_content(doc)
    assert content == ""


def test_extract_kb_doc_content_precedence():
    """Verify precedence: text > content > summary > title."""
    # text wins
    doc = {"text": "A", "content": "B", "summary": "C", "title": "D"}
    assert _extract_kb_doc_content(doc) == "A"

    # content wins if no text
    doc = {"content": "B", "summary": "C", "title": "D"}
    assert _extract_kb_doc_content(doc) == "B"

    # summary+title wins if no text/content
    doc = {"summary": "C", "title": "D"}
    content = _extract_kb_doc_content(doc)
    assert "D" in content and "C" in content

    # title only if no text/content/summary
    doc = {"title": "D"}
    assert _extract_kb_doc_content(doc) == "D"


# ── generate_or_revise: KB context in revision prompt ──────────────────────


@pytest.mark.asyncio
async def test_generate_or_revise_revision_includes_kb_context():
    """Revision prompt (is_first_generation=False) must include KB documents."""
    kb_docs = [
        {"text": "Candidate has 5 years Python experience at ACME Corp"},
        {"text": "MSc Computer Science from ETH Zurich, graduated 2020"},
    ]
    state = _base_state(
        is_first_generation=False,
        kb_docs=kb_docs,
        current_latex=r"\section{Summary}Already generated content",
        fit_feedback="Add more quantified achievements",
        quality_feedback="Remove vague claims",
    )

    with patch("jam.llm.llm_call", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = r"\section{Summary}Revised content"
        result = await generate_or_revise(state)

    # Check the user prompt passed to llm_call contains KB docs
    user_prompt = mock_llm.call_args[0][1]
    assert "KNOWLEDGE BASE DOCUMENTS" in user_prompt
    assert "5 years Python experience" in user_prompt
    assert "ETH Zurich" in user_prompt


@pytest.mark.asyncio
async def test_generate_or_revise_first_gen_includes_kb_context():
    """First generation prompt must include KB documents."""
    kb_docs = [{"text": "Senior engineer with distributed systems expertise"}]
    state = _base_state(
        is_first_generation=True,
        kb_docs=kb_docs,
    )

    with patch("jam.llm.llm_call", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = r"\section{Summary}Generated content"
        result = await generate_or_revise(state)

    user_prompt = mock_llm.call_args[0][1]
    assert "KNOWLEDGE BASE DOCUMENTS" in user_prompt
    assert "distributed systems expertise" in user_prompt


# ── generate_or_revise: compact loop branch ────────────────────────────────


@pytest.mark.asyncio
async def test_generate_or_revise_compact_iteration_excludes_job_desc_and_kb():
    """Compact loop (compact_iteration > 0) must NOT include job_description or
    KB docs in the user prompt — only compress recommendations + current LaTeX."""
    kb_docs = [{"text": "Senior engineer with distributed systems expertise"}]
    state = _base_state(
        is_first_generation=False,
        kb_docs=kb_docs,
        current_latex=r"\section{Summary}Long content that needs trimming",
        compress_feedback="Remove the hobbies section. Shorten bullet points.",
        compact_iteration=1,
        page_count=2,
    )

    with patch("jam.llm.llm_call", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = r"\section{Summary}Shorter content"
        result = await generate_or_revise(state)

    user_prompt = mock_llm.call_args[0][1]
    assert "job_description" not in user_prompt.lower()
    assert "KNOWLEDGE BASE DOCUMENTS" not in user_prompt
    assert "distributed systems expertise" not in user_prompt
    # The current LaTeX must be present
    assert "CURRENT LATEX" in user_prompt


@pytest.mark.asyncio
async def test_generate_or_revise_compact_iteration_includes_compress_feedback():
    """Compact loop (compact_iteration > 0) must include compress_feedback in
    the user prompt."""
    state = _base_state(
        is_first_generation=False,
        kb_docs=[],
        current_latex=r"\section{Summary}Long content",
        compress_feedback="Remove hobbies section. Use 10pt font.",
        compact_iteration=2,
        page_count=2,
    )

    with patch("jam.llm.llm_call", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = r"\section{Summary}Shorter"
        result = await generate_or_revise(state)

    user_prompt = mock_llm.call_args[0][1]
    assert "COMPRESS RECOMMENDATIONS" in user_prompt
    assert "Remove hobbies section" in user_prompt
    assert "Use 10pt font" in user_prompt


@pytest.mark.asyncio
async def test_generate_or_revise_compact_iteration_uses_compressor_system_prompt():
    """Compact loop (compact_iteration > 0) must use the compression-focused
    system prompt, NOT PROMPT_GENERATE_REVISE."""
    state = _base_state(
        is_first_generation=False,
        kb_docs=[],
        current_latex=r"\section{Summary}Long content",
        compress_feedback="Shorten the summary.",
        compact_iteration=1,
        page_count=3,
    )

    with patch("jam.db.get_all_settings", return_value={}), \
         patch("jam.llm.llm_call", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = r"\section{Summary}Shorter"
        result = await generate_or_revise(state)

    system_prompt = mock_llm.call_args[0][0]
    # Must mention document compression context
    assert "document compressor" in system_prompt.lower()
    # Must NOT be the general revision prompt (check for a distinctive phrase)
    assert "PROMPT_GENERATE_REVISE" not in system_prompt
    # Must reference the page count
    assert "3" in system_prompt


# ── retrieve_kb_docs: include namespace bug-catching tests ──────────────────


@pytest.mark.asyncio
async def test_retrieve_kb_docs_include_ns_called_when_configured():
    """When kb_include_namespaces is set in DB, list_namespace_documents must be called
    and its results must appear in kb_docs."""
    stored = {
        "kb_retrieval_namespaces": json.dumps(["ns-search"]),
        "kb_include_namespaces": json.dumps(["ns-include"]),
        "kb_retrieval_n_results": "5",
    }
    include_docs = [
        {"doc_id": "inc-1", "text": "Full document from include namespace", "chunk_index": 0},
    ]
    search_results = [
        {"doc_id": "src-1", "text": "Search hit", "chunk_index": 0},
    ]

    with patch("jam.db.get_all_settings", return_value=stored), \
         patch("jam.kb_client.search_documents", new_callable=AsyncMock, return_value=search_results), \
         patch("jam.kb_client.list_namespace_documents", new_callable=AsyncMock, return_value=include_docs) as mock_list:

        result = await retrieve_kb_docs(_base_state())

    mock_list.assert_called_once()
    assert mock_list.call_args[0][0] == ["ns-include"]
    # Include docs must be present in the merged result
    texts = [d.get("text", "") for d in result["kb_docs"]]
    assert "Full document from include namespace" in texts


@pytest.mark.asyncio
async def test_retrieve_kb_docs_include_only_no_search_ns():
    """When only include namespaces are configured (no search namespaces),
    documents should still be retrieved and search_documents must NOT be called."""
    stored = {
        "kb_retrieval_namespaces": "[]",
        "kb_include_namespaces": json.dumps(["personal-info"]),
        "kb_retrieval_n_results": "5",
    }
    include_docs = [
        {"doc_id": "p1", "text": "My name is Jane, I am a software engineer", "chunk_index": 0},
        {"doc_id": "p1", "text": "I have 10 years experience in Python", "chunk_index": 1},
    ]

    with patch("jam.db.get_all_settings", return_value=stored), \
         patch("jam.kb_client.search_documents", new_callable=AsyncMock) as mock_search, \
         patch("jam.kb_client.list_namespace_documents", new_callable=AsyncMock, return_value=include_docs):

        result = await retrieve_kb_docs(_base_state())

    mock_search.assert_not_called()
    assert len(result["kb_docs"]) == 2
    assert result["kb_docs"][0]["text"] == "My name is Jane, I am a software engineer"
    assert result["kb_docs"][1]["text"] == "I have 10 years experience in Python"


@pytest.mark.asyncio
async def test_retrieve_kb_docs_search_error_still_returns_include_docs():
    """If semantic search raises an exception but include namespace fetch succeeds,
    include docs should still be returned."""
    stored = {
        "kb_retrieval_namespaces": json.dumps(["ns-a"]),
        "kb_include_namespaces": json.dumps(["ns-b"]),
        "kb_retrieval_n_results": "5",
    }
    include_docs = [{"doc_id": "i1", "text": "Important included content", "chunk_index": 0}]

    with patch("jam.db.get_all_settings", return_value=stored), \
         patch("jam.kb_client.search_documents", new_callable=AsyncMock, side_effect=RuntimeError("KB down")), \
         patch("jam.kb_client.list_namespace_documents", new_callable=AsyncMock, return_value=include_docs):

        result = await retrieve_kb_docs(_base_state())

    assert len(result["kb_docs"]) == 1
    assert result["kb_docs"][0]["text"] == "Important included content"


@pytest.mark.asyncio
async def test_retrieve_kb_docs_include_error_still_returns_search_docs():
    """If include namespace fetch fails but semantic search succeeds,
    search docs should still be returned."""
    stored = {
        "kb_retrieval_namespaces": json.dumps(["ns-a"]),
        "kb_include_namespaces": json.dumps(["ns-b"]),
        "kb_retrieval_n_results": "5",
    }
    search_results = [{"doc_id": "s1", "text": "Search result content", "chunk_index": 0}]

    with patch("jam.db.get_all_settings", return_value=stored), \
         patch("jam.kb_client.search_documents", new_callable=AsyncMock, return_value=search_results), \
         patch("jam.kb_client.list_namespace_documents", new_callable=AsyncMock, side_effect=RuntimeError("timeout")):

        result = await retrieve_kb_docs(_base_state())

    assert len(result["kb_docs"]) == 1
    assert result["kb_docs"][0]["text"] == "Search result content"


@pytest.mark.asyncio
async def test_retrieve_kb_docs_empty_include_ns_skips_list_call():
    """When kb_include_namespaces is '[]', list_namespace_documents must NOT be called."""
    stored = {
        "kb_retrieval_namespaces": json.dumps(["ns-a"]),
        "kb_include_namespaces": "[]",
        "kb_retrieval_n_results": "5",
    }

    with patch("jam.db.get_all_settings", return_value=stored), \
         patch("jam.kb_client.search_documents", new_callable=AsyncMock, return_value=[]), \
         patch("jam.kb_client.list_namespace_documents", new_callable=AsyncMock) as mock_list:

        await retrieve_kb_docs(_base_state())

    mock_list.assert_not_called()


@pytest.mark.asyncio
async def test_retrieve_kb_docs_empty_search_ns_skips_search_call():
    """When kb_retrieval_namespaces is '[]', search_documents must NOT be called —
    no embedding API call should be made even though namespace_ids=None would
    otherwise search all namespaces."""
    stored = {
        "kb_retrieval_namespaces": "[]",
        "kb_include_namespaces": "[]",
        "kb_retrieval_n_results": "5",
    }

    with patch("jam.db.get_all_settings", return_value=stored), \
         patch("jam.kb_client.search_documents", new_callable=AsyncMock) as mock_search, \
         patch("jam.kb_client.list_namespace_documents", new_callable=AsyncMock) as mock_list:

        result = await retrieve_kb_docs(_base_state())

    mock_search.assert_not_called()
    mock_list.assert_not_called()
    assert result["kb_docs"] == []


@pytest.mark.asyncio
async def test_retrieve_kb_docs_include_docs_content_reaches_prompt():
    """End-to-end: include namespace docs must appear in the LLM prompt via generate_or_revise."""
    include_docs = [
        {"doc_id": "cv-data", "text": "Jane Doe graduated from MIT with honors in 2019", "chunk_index": 0},
        {"doc_id": "cv-data", "text": "Led a team of 12 engineers at TechCorp", "chunk_index": 1},
    ]
    state = _base_state(
        is_first_generation=True,
        kb_docs=include_docs,
    )

    with patch("jam.llm.llm_call", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = r"\section{Summary}Generated"
        await generate_or_revise(state)

    user_prompt = mock_llm.call_args[0][1]
    assert "KNOWLEDGE BASE DOCUMENTS" in user_prompt
    assert "MIT with honors" in user_prompt
    assert "Led a team of 12 engineers" in user_prompt
    assert "(none available)" not in user_prompt


@pytest.mark.asyncio
async def test_generate_prompt_kb_context_truncation():
    """When KB docs exceed 6000 chars, context should be truncated without error."""
    # Create a doc with >6000 chars of content
    long_text = "A" * 7000
    state = _base_state(
        is_first_generation=True,
        kb_docs=[{"text": long_text}],
    )

    with patch("jam.llm.llm_call", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = r"\section{Summary}Generated"
        await generate_or_revise(state)

    user_prompt = mock_llm.call_args[0][1]
    # The kb_context portion should be truncated to 6000 chars
    assert "KNOWLEDGE BASE DOCUMENTS" in user_prompt
    # The full 7000 chars should NOT appear (truncated)
    assert long_text not in user_prompt


# ── _get_prompt ──────────────────────────────────────────────────────────────


def test_get_prompt_returns_db_value_when_present():
    """_get_prompt should return the stored value from DB settings."""
    with patch("jam.db.get_all_settings", return_value={"prompt_analyze_fit": "Custom fit prompt"}):
        result = _get_prompt("prompt_analyze_fit", PROMPT_ANALYZE_FIT)
    assert result == "Custom fit prompt"


def test_get_prompt_returns_default_when_key_missing():
    """_get_prompt should return the default when the key is absent from DB."""
    with patch("jam.db.get_all_settings", return_value={}):
        result = _get_prompt("prompt_analyze_fit", PROMPT_ANALYZE_FIT)
    assert result == PROMPT_ANALYZE_FIT


def test_get_prompt_returns_default_when_value_is_empty_string():
    """_get_prompt should fall back to default when stored value is empty string."""
    with patch("jam.db.get_all_settings", return_value={"prompt_analyze_fit": ""}):
        result = _get_prompt("prompt_analyze_fit", PROMPT_ANALYZE_FIT)
    assert result == PROMPT_ANALYZE_FIT


def test_get_prompt_returns_default_when_value_is_none():
    """_get_prompt should fall back to default when stored value is None."""
    with patch("jam.db.get_all_settings", return_value={"prompt_analyze_fit": None}):
        result = _get_prompt("prompt_analyze_fit", PROMPT_ANALYZE_FIT)
    assert result == PROMPT_ANALYZE_FIT


# ── _get_prompt: 4-tier resolution chain ────────────────────────────────────


def test_get_prompt_typed_db_setting_takes_priority():
    """Typed DB setting takes priority over hardcoded typed default."""
    stored = {
        "prompt_generate_first:cv": "CV-specific DB prompt. {locked_sections_notice}",
    }
    with patch("jam.db.get_all_settings", return_value=stored):
        result = _get_prompt("prompt_generate_first", PROMPT_GENERATE_FIRST_CV, doc_type="cv")
    assert result == "CV-specific DB prompt. {locked_sections_notice}"


def test_get_prompt_typed_hardcoded_default_used_when_no_db_settings():
    """Typed hardcoded default used when DB has no matching typed setting."""
    with patch("jam.db.get_all_settings", return_value={}):
        result_cv = _get_prompt("prompt_generate_first", PROMPT_GENERATE_FIRST_CV, doc_type="cv")
        result_cl = _get_prompt("prompt_generate_first", PROMPT_GENERATE_FIRST_CV, doc_type="cover_letter")
    assert result_cv == PROMPT_GENERATE_FIRST_CV
    assert result_cl == PROMPT_GENERATE_FIRST_CL


def test_get_prompt_shared_only_prompt_uses_db_then_hardcoded():
    """Shared-only prompts (analyze_fit, analyze_compress): DB key -> hardcoded default."""
    with patch("jam.db.get_all_settings", return_value={}):
        result = _get_prompt("prompt_analyze_fit", PROMPT_ANALYZE_FIT, doc_type="cv")
    assert result == PROMPT_ANALYZE_FIT


def test_get_prompt_shared_only_prompt_db_override():
    """Shared-only prompts use DB value when stored."""
    stored = {"prompt_analyze_fit": "Custom fit prompt."}
    with patch("jam.db.get_all_settings", return_value=stored):
        result = _get_prompt("prompt_analyze_fit", PROMPT_ANALYZE_FIT, doc_type="cv")
    assert result == "Custom fit prompt."


def test_get_prompt_split_prompt_no_shared_db_fallback():
    """For split prompts, a shared DB key does NOT override the typed hardcoded default."""
    stored = {"prompt_generate_first": "Shared DB prompt. {locked_sections_notice}"}
    with patch("jam.db.get_all_settings", return_value=stored):
        # Shared DB key is ignored; falls back to typed hardcoded default
        result_cv = _get_prompt("prompt_generate_first", PROMPT_GENERATE_FIRST_CV, doc_type="cv")
        result_cl = _get_prompt("prompt_generate_first", PROMPT_GENERATE_FIRST_CV, doc_type="cover_letter")
    assert result_cv == PROMPT_GENERATE_FIRST_CV
    assert result_cl == PROMPT_GENERATE_FIRST_CL


def test_get_prompt_split_prompt_empty_doc_type_falls_back_to_default_arg():
    """When doc_type is empty for a split prompt, the `default` argument is returned."""
    with patch("jam.db.get_all_settings", return_value={}):
        result = _get_prompt("prompt_generate_first", PROMPT_GENERATE_FIRST_CV, doc_type="")
    assert result == PROMPT_GENERATE_FIRST_CV


# ── get_all_prompt_defaults ────────────────────────────────────────────────────


def test_get_all_prompt_defaults_returns_all_keys():
    """get_all_prompt_defaults should return 9 keys: 3 shared + 6 typed (3 prompts x 2 doc types).
    No shared keys for generate_first, generate_revise, or analyze_quality."""
    defaults = get_all_prompt_defaults()
    # 3 shared-only keys (analyze_fit, analyze_compress, prep guide)
    assert "prompt_analyze_fit" in defaults
    assert "prompt_analyze_compress" in defaults
    assert "prompt_generate_prep_guide" in defaults
    # 6 typed keys (generate_first, generate_revise, analyze_quality each have cv + cover_letter)
    assert "prompt_generate_first:cv" in defaults
    assert "prompt_generate_first:cover_letter" in defaults
    assert "prompt_generate_revise:cv" in defaults
    assert "prompt_generate_revise:cover_letter" in defaults
    assert "prompt_analyze_quality:cv" in defaults
    assert "prompt_analyze_quality:cover_letter" in defaults
    # No shared keys for the 3 split prompts
    assert "prompt_generate_first" not in defaults
    assert "prompt_generate_revise" not in defaults
    assert "prompt_analyze_quality" not in defaults
    # Total 9 keys
    assert len(defaults) == 9


def test_get_all_prompt_defaults_values_match_constants():
    """Each key in get_all_prompt_defaults should map to the correct constant."""
    defaults = get_all_prompt_defaults()
    assert defaults["prompt_analyze_fit"] == PROMPT_ANALYZE_FIT
    assert defaults["prompt_analyze_compress"] == PROMPT_ANALYZE_COMPRESS
    assert defaults["prompt_generate_first:cv"] == PROMPT_GENERATE_FIRST_CV
    assert defaults["prompt_generate_first:cover_letter"] == PROMPT_GENERATE_FIRST_CL
    assert defaults["prompt_generate_revise:cv"] == PROMPT_GENERATE_REVISE_CV
    assert defaults["prompt_generate_revise:cover_letter"] == PROMPT_GENERATE_REVISE_CL
    assert defaults["prompt_analyze_quality:cv"] == PROMPT_ANALYZE_QUALITY_CV
    assert defaults["prompt_analyze_quality:cover_letter"] == PROMPT_ANALYZE_QUALITY_CL


# ── Prompt constants ──────────────────────────────────────────────────────────


def test_prompt_constants_are_non_empty_strings():
    """All prompt constants should be non-empty strings."""
    for name, constant in [
        ("PROMPT_GENERATE_FIRST_CV", PROMPT_GENERATE_FIRST_CV),
        ("PROMPT_GENERATE_FIRST_CL", PROMPT_GENERATE_FIRST_CL),
        ("PROMPT_GENERATE_REVISE_CV", PROMPT_GENERATE_REVISE_CV),
        ("PROMPT_GENERATE_REVISE_CL", PROMPT_GENERATE_REVISE_CL),
        ("PROMPT_ANALYZE_FIT", PROMPT_ANALYZE_FIT),
        ("PROMPT_ANALYZE_QUALITY_CV", PROMPT_ANALYZE_QUALITY_CV),
        ("PROMPT_ANALYZE_QUALITY_CL", PROMPT_ANALYZE_QUALITY_CL),
        ("PROMPT_ANALYZE_COMPRESS", PROMPT_ANALYZE_COMPRESS),
    ]:
        assert isinstance(constant, str) and constant, f"{name} must be a non-empty string"


def test_prompt_generate_first_cv_has_locked_sections_placeholder():
    """PROMPT_GENERATE_FIRST_CV must contain {locked_sections_notice} placeholder."""
    assert "{locked_sections_notice}" in PROMPT_GENERATE_FIRST_CV


def test_prompt_generate_first_cl_has_locked_sections_placeholder():
    """PROMPT_GENERATE_FIRST_CL must contain {locked_sections_notice} placeholder."""
    assert "{locked_sections_notice}" in PROMPT_GENERATE_FIRST_CL


def test_prompt_generate_revise_cv_has_locked_sections_placeholder():
    """PROMPT_GENERATE_REVISE_CV must contain {locked_sections_notice} placeholder."""
    assert "{locked_sections_notice}" in PROMPT_GENERATE_REVISE_CV


def test_prompt_generate_revise_cl_has_locked_sections_placeholder():
    """PROMPT_GENERATE_REVISE_CL must contain {locked_sections_notice} placeholder."""
    assert "{locked_sections_notice}" in PROMPT_GENERATE_REVISE_CL


def test_prompt_analyze_compress_has_both_placeholders():
    """PROMPT_ANALYZE_COMPRESS must contain both {page_count} and {locked_sections_notice}."""
    assert "{page_count}" in PROMPT_ANALYZE_COMPRESS
    assert "{locked_sections_notice}" in PROMPT_ANALYZE_COMPRESS


# ── generate_or_revise: DB-configurable system prompt ────────────────────────


@pytest.mark.asyncio
async def test_generate_or_revise_first_gen_uses_db_system_prompt():
    """When prompt_generate_first:cv is stored in DB, it should be used as the system prompt."""
    custom_prompt = "Custom first-gen prompt. {locked_sections_notice}"
    state = _base_state(is_first_generation=True, kb_docs=[])  # doc_type="cv"

    with patch("jam.db.get_all_settings", return_value={"prompt_generate_first:cv": custom_prompt}), \
         patch("jam.llm.llm_call", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = r"\section{Summary}Generated"
        await generate_or_revise(state)

    system_prompt = mock_llm.call_args[0][0]
    assert "Custom first-gen prompt." in system_prompt


@pytest.mark.asyncio
async def test_generate_or_revise_first_gen_fallback_to_default_prompt():
    """When no DB prompt is set, should fall back to the typed hardcoded default for the doc_type."""
    state = _base_state(is_first_generation=True, kb_docs=[])  # doc_type="cv"

    with patch("jam.db.get_all_settings", return_value={}), \
         patch("jam.llm.llm_call", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = r"\section{Summary}Generated"
        await generate_or_revise(state)

    system_prompt = mock_llm.call_args[0][0]
    # CV typed default contains this distinctive phrase
    assert "expert CV writer" in system_prompt


@pytest.mark.asyncio
async def test_generate_or_revise_revision_uses_db_system_prompt():
    """When prompt_generate_revise:cv is stored in DB, it should be used as the system prompt."""
    custom_prompt = "Custom revision prompt. {locked_sections_notice}"
    state = _base_state(
        is_first_generation=False,
        kb_docs=[],
        current_latex=r"\section{Summary}Existing content",
    )

    with patch("jam.db.get_all_settings", return_value={"prompt_generate_revise:cv": custom_prompt}), \
         patch("jam.llm.llm_call", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = r"\section{Summary}Revised"
        await generate_or_revise(state)

    system_prompt = mock_llm.call_args[0][0]
    assert "Custom revision prompt." in system_prompt


@pytest.mark.asyncio
async def test_generate_or_revise_custom_prompt_without_placeholder_does_not_crash():
    """A custom prompt without {locked_sections_notice} should not raise a KeyError."""
    custom_prompt = "No placeholders here at all."
    state = _base_state(is_first_generation=True, kb_docs=[])  # doc_type="cv"

    with patch("jam.db.get_all_settings", return_value={"prompt_generate_first:cv": custom_prompt}), \
         patch("jam.llm.llm_call", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = r"\section{Summary}Generated"
        result = await generate_or_revise(state)

    assert "error" not in result or result.get("error") is None
    assert mock_llm.called


# ── analyze_fit: DB-configurable system prompt ────────────────────────────────


@pytest.mark.asyncio
async def test_analyze_fit_uses_db_system_prompt():
    """When prompt_analyze_fit is stored in DB, it should be used as the system prompt."""
    custom_prompt = "Custom fit analysis prompt."
    state = _base_state(current_latex=r"\section{Summary}Content")

    with patch("jam.db.get_all_settings", return_value={"prompt_analyze_fit": custom_prompt}), \
         patch("jam.llm.llm_call", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = "Fit feedback"
        await analyze_fit(state)

    system_prompt = mock_llm.call_args[0][0]
    assert system_prompt == "Custom fit analysis prompt."


@pytest.mark.asyncio
async def test_analyze_fit_fallback_to_default_prompt():
    """When no DB prompt is set, analyze_fit should use PROMPT_ANALYZE_FIT default."""
    state = _base_state(current_latex=r"\section{Summary}Content")

    with patch("jam.db.get_all_settings", return_value={}), \
         patch("jam.llm.llm_call", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = "Fit feedback"
        await analyze_fit(state)

    system_prompt = mock_llm.call_args[0][0]
    assert system_prompt == PROMPT_ANALYZE_FIT


# ── analyze_quality: DB-configurable system prompt ───────────────────────────


@pytest.mark.asyncio
async def test_analyze_quality_uses_db_system_prompt():
    """When prompt_analyze_quality:cv is stored in DB, it should be used as the system prompt."""
    custom_prompt = "Custom quality review prompt."
    state = _base_state(current_latex=r"\section{Summary}Content")  # doc_type="cv"

    with patch("jam.db.get_all_settings", return_value={"prompt_analyze_quality:cv": custom_prompt}), \
         patch("jam.llm.llm_call", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = "Quality feedback"
        await analyze_quality(state)

    system_prompt = mock_llm.call_args[0][0]
    assert system_prompt == "Custom quality review prompt."


@pytest.mark.asyncio
async def test_analyze_quality_fallback_to_default_prompt():
    """When no DB prompt is set, analyze_quality should use the typed hardcoded default for the doc_type."""
    state = _base_state(current_latex=r"\section{Summary}Content")  # doc_type="cv"

    with patch("jam.db.get_all_settings", return_value={}), \
         patch("jam.llm.llm_call", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = "Quality feedback"
        await analyze_quality(state)

    system_prompt = mock_llm.call_args[0][0]
    assert system_prompt == PROMPT_ANALYZE_QUALITY_CV


# ── _compile_latex_bytes: images parameter ───────────────────────────────────

import base64
import os


@pytest.mark.asyncio
async def test_compile_latex_bytes_writes_image_files(tmp_path, monkeypatch):
    """When images dict is provided, image files should be written to the temp dir
    before tectonic runs, so \\includegraphics can find them."""
    # Create a minimal 1x1 PNG (smallest valid PNG)
    png_b64 = base64.b64encode(
        bytes([
            0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,  # PNG signature
            0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,  # IHDR chunk length + type
            0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,  # width=1, height=1
            0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53,  # bit depth, colour type, ...
            0xDE, 0x00, 0x00, 0x00, 0x0C, 0x49, 0x44, 0x41,  # IDAT chunk
            0x54, 0x08, 0xD7, 0x63, 0xF8, 0xCF, 0xC0, 0x00,
            0x00, 0x00, 0x02, 0x00, 0x01, 0xE2, 0x21, 0xBC,
            0x33, 0x00, 0x00, 0x00, 0x00, 0x49, 0x45, 0x4E,  # IEND chunk
            0x44, 0xAE, 0x42, 0x60, 0x82,
        ])
    ).decode()
    photo_uri = f"data:image/png;base64,{png_b64}"

    written_files: list[str] = []

    async def fake_subprocess(*args, **kwargs):
        """Capture which files exist in tmpdir when tectonic would be called."""
        # args[0] is "tectonic", args[1] is the .tex path
        tex_path = args[1]
        tmpdir = os.path.dirname(tex_path)
        written_files.extend(os.listdir(tmpdir))

        class FakeProc:
            returncode = 0
            async def communicate(self):
                return b"", b""

        # Also write a fake PDF so the function doesn't fail
        pdf_path = os.path.join(tmpdir, "document.pdf")
        with open(pdf_path, "wb") as fh:
            fh.write(b"%PDF-1.4 fake")
        return FakeProc()

    monkeypatch.setattr("shutil.which", lambda _: "/usr/bin/tectonic")
    monkeypatch.setattr("asyncio.create_subprocess_exec", fake_subprocess)

    # We only care about file writing, not valid PDF output; wrap _pdf_page_count
    with patch("jam.generation._pdf_page_count", return_value=1):
        try:
            await _compile_latex_bytes(r"\documentclass{article}\begin{document}Hi\end{document}",
                                       images={"photo": photo_uri})
        except Exception:
            pass  # PDF may be invalid; we only care about file writing

    assert "photo.png" in written_files, (
        f"Expected photo.png to be written to tmpdir; found: {written_files}"
    )


@pytest.mark.asyncio
async def test_compile_latex_bytes_no_images_does_not_crash(monkeypatch):
    """When images=None (default), compilation should proceed normally without errors."""
    async def fake_subprocess(*args, **kwargs):
        tex_path = args[1]
        tmpdir = os.path.dirname(tex_path)

        class FakeProc:
            returncode = 0
            async def communicate(self):
                return b"", b""

        pdf_path = os.path.join(tmpdir, "document.pdf")
        with open(pdf_path, "wb") as fh:
            fh.write(b"%PDF-1.4 fake")
        return FakeProc()

    monkeypatch.setattr("shutil.which", lambda _: "/usr/bin/tectonic")
    monkeypatch.setattr("asyncio.create_subprocess_exec", fake_subprocess)

    with patch("jam.generation._pdf_page_count", return_value=1):
        try:
            await _compile_latex_bytes(r"\documentclass{article}\begin{document}Hi\end{document}")
        except Exception:
            pass  # PDF validity is not under test here


@pytest.mark.asyncio
async def test_compile_latex_bytes_skips_invalid_data_uri(monkeypatch):
    """Entries whose value is not a data URI are silently skipped."""
    written_files: list[str] = []

    async def fake_subprocess(*args, **kwargs):
        tex_path = args[1]
        tmpdir = os.path.dirname(tex_path)
        written_files.extend(os.listdir(tmpdir))

        class FakeProc:
            returncode = 0
            async def communicate(self):
                return b"", b""

        pdf_path = os.path.join(tmpdir, "document.pdf")
        with open(pdf_path, "wb") as fh:
            fh.write(b"%PDF-1.4 fake")
        return FakeProc()

    monkeypatch.setattr("shutil.which", lambda _: "/usr/bin/tectonic")
    monkeypatch.setattr("asyncio.create_subprocess_exec", fake_subprocess)

    with patch("jam.generation._pdf_page_count", return_value=1):
        try:
            await _compile_latex_bytes(
                r"\documentclass{article}\begin{document}Hi\end{document}",
                images={"photo": "not-a-data-uri"},
            )
        except Exception:
            pass

    # Only the .tex file should be in the dir; no image file
    image_files = [f for f in written_files if not f.endswith(".tex")]
    assert not any(f.startswith("photo") for f in image_files), (
        f"Should not write image for invalid URI; found: {image_files}"
    )


# ── retrieve_kb_docs: personal_photo / personal_signature fields ─────────────


@pytest.mark.asyncio
async def test_retrieve_kb_docs_populates_personal_photo_from_settings():
    """personal_photo from stored settings should appear in returned state."""
    photo_uri = "data:image/png;base64,abc123"
    stored = {
        "kb_retrieval_namespaces": "[]",
        "kb_include_namespaces": "[]",
        "kb_retrieval_n_results": "5",
        "personal_photo": photo_uri,
    }

    with patch("jam.db.get_all_settings", return_value=stored), \
         patch("jam.kb_client.search_documents", new_callable=AsyncMock, return_value=[]), \
         patch("jam.kb_client.list_namespace_documents", new_callable=AsyncMock):

        result = await retrieve_kb_docs(_base_state())

    assert result["personal_photo"] == photo_uri
    assert result["personal_signature"] == ""


@pytest.mark.asyncio
async def test_retrieve_kb_docs_populates_personal_signature_from_settings():
    """personal_signature from stored settings should appear in returned state."""
    sig_uri = "data:image/jpeg;base64,xyz789"
    stored = {
        "kb_retrieval_namespaces": "[]",
        "kb_include_namespaces": "[]",
        "kb_retrieval_n_results": "5",
        "personal_signature": sig_uri,
    }

    with patch("jam.db.get_all_settings", return_value=stored), \
         patch("jam.kb_client.search_documents", new_callable=AsyncMock, return_value=[]), \
         patch("jam.kb_client.list_namespace_documents", new_callable=AsyncMock):

        result = await retrieve_kb_docs(_base_state())

    assert result["personal_signature"] == sig_uri
    assert result["personal_photo"] == ""


@pytest.mark.asyncio
async def test_retrieve_kb_docs_empty_images_when_not_in_settings():
    """When personal_photo and personal_signature are absent from DB, both default to ''."""
    stored = {
        "kb_retrieval_namespaces": "[]",
        "kb_include_namespaces": "[]",
        "kb_retrieval_n_results": "5",
    }

    with patch("jam.db.get_all_settings", return_value=stored), \
         patch("jam.kb_client.search_documents", new_callable=AsyncMock, return_value=[]), \
         patch("jam.kb_client.list_namespace_documents", new_callable=AsyncMock):

        result = await retrieve_kb_docs(_base_state())

    assert result["personal_photo"] == ""
    assert result["personal_signature"] == ""


# ── generate_or_revise: image hints in system prompt ─────────────────────────


@pytest.mark.asyncio
async def test_generate_or_revise_first_gen_includes_photo_hint_in_system_prompt():
    """When personal_photo is set, system prompt should contain photo filename hint."""
    state = _base_state(
        is_first_generation=True,
        kb_docs=[],
        personal_photo="data:image/png;base64,abc123",
    )

    with patch("jam.db.get_all_settings", return_value={}), \
         patch("jam.llm.llm_call", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = r"\section{Summary}Generated"
        result = await generate_or_revise(state)

    system_prompt = mock_llm.call_args[0][0]
    assert "photo.png" in system_prompt
    assert r"\includegraphics" in system_prompt


@pytest.mark.asyncio
async def test_generate_or_revise_revision_includes_signature_hint_in_system_prompt():
    """When personal_signature is set, system prompt should contain signature filename hint."""
    state = _base_state(
        is_first_generation=False,
        kb_docs=[],
        current_latex=r"\section{Summary}Existing",
        personal_signature="data:image/jpeg;base64,def456",
    )

    with patch("jam.db.get_all_settings", return_value={}), \
         patch("jam.llm.llm_call", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = r"\section{Summary}Revised"
        result = await generate_or_revise(state)

    system_prompt = mock_llm.call_args[0][0]
    assert "signature.jpeg" in system_prompt
    assert r"\includegraphics" in system_prompt


@pytest.mark.asyncio
async def test_generate_or_revise_no_images_no_hint_in_system_prompt():
    """When no images are set, system prompt should NOT contain image hints."""
    state = _base_state(
        is_first_generation=True,
        kb_docs=[],
        personal_photo="",
        personal_signature="",
    )

    with patch("jam.db.get_all_settings", return_value={}), \
         patch("jam.llm.llm_call", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = r"\section{Summary}Generated"
        result = await generate_or_revise(state)

    system_prompt = mock_llm.call_args[0][0]
    assert "photo" not in system_prompt or "candidate" not in system_prompt.split("photo")[0]
    # More directly: the includegraphics hint should not be there
    assert "includegraphics{photo" not in system_prompt
    assert "includegraphics{signature" not in system_prompt


# ── compile_and_check: passes images to _compile_latex_bytes ─────────────────


@pytest.mark.asyncio
async def test_compile_and_check_passes_images_when_set():
    """compile_and_check should forward personal_photo and personal_signature to
    _compile_latex_bytes as the images dict."""
    photo_uri = "data:image/png;base64,abc123"
    sig_uri = "data:image/jpeg;base64,def456"
    state = _base_state(
        current_latex=r"\documentclass{article}\begin{document}Hi\end{document}",
        personal_photo=photo_uri,
        personal_signature=sig_uri,
    )

    with patch("jam.generation._compile_latex_bytes", new_callable=AsyncMock) as mock_compile, \
         patch("jam.generation._pdf_page_count", return_value=1):
        mock_compile.return_value = b"%PDF-1.4"
        await compile_and_check(state)

    mock_compile.assert_called_once()
    call_kwargs = mock_compile.call_args[1]
    assert call_kwargs["images"] == {"photo": photo_uri, "signature": sig_uri}


@pytest.mark.asyncio
async def test_compile_and_check_passes_none_images_when_not_set():
    """compile_and_check should pass images=None when no personal assets are set."""
    state = _base_state(
        current_latex=r"\documentclass{article}\begin{document}Hi\end{document}",
        personal_photo="",
        personal_signature="",
    )

    with patch("jam.generation._compile_latex_bytes", new_callable=AsyncMock) as mock_compile, \
         patch("jam.generation._pdf_page_count", return_value=1):
        mock_compile.return_value = b"%PDF-1.4"
        await compile_and_check(state)

    mock_compile.assert_called_once()
    call_kwargs = mock_compile.call_args[1]
    assert call_kwargs["images"] is None


# ── _resolve_step_model ──────────────────────────────────────────────────────


def test_resolve_step_model_with_override():
    """Returns (provider, model) tuple when a valid catalog_id is stored."""
    with patch("jam.db.get_all_settings", return_value={"step_model_analyze_fit": "groq:llama-3.3-70b-versatile"}):
        result = _resolve_step_model("analyze_fit")
    assert result == ("groq", "llama-3.3-70b-versatile")


def test_resolve_step_model_no_override():
    """Returns (None, None) when the key is absent from stored settings."""
    with patch("jam.db.get_all_settings", return_value={}):
        result = _resolve_step_model("analyze_fit")
    assert result == (None, None)


def test_resolve_step_model_empty_string():
    """Returns (None, None) when the stored value is an empty string."""
    with patch("jam.db.get_all_settings", return_value={"step_model_analyze_fit": ""}):
        result = _resolve_step_model("analyze_fit")
    assert result == (None, None)


def test_resolve_step_model_invalid_format():
    """Returns (None, None) when the stored value has no colon separator."""
    with patch("jam.db.get_all_settings", return_value={"step_model_analyze_fit": "no-colon-here"}):
        result = _resolve_step_model("analyze_fit")
    assert result == (None, None)


# ── per-step model passed to llm_call ────────────────────────────────────────


@pytest.mark.asyncio
async def test_generate_node_passes_step_model():
    """generate_or_revise should forward the resolved provider/model to llm_call."""
    state = _base_state(is_first_generation=True, kb_docs=[])

    with patch("jam.generation._resolve_step_model", return_value=("anthropic", "claude-sonnet-4-6")), \
         patch("jam.llm.llm_call", new_callable=AsyncMock) as mock_llm, \
         patch("jam.db.get_all_settings", return_value={}):
        mock_llm.return_value = r"\section{Summary}Generated"
        await generate_or_revise(state)

    mock_llm.assert_called_once()
    _, kwargs = mock_llm.call_args
    assert kwargs.get("provider") == "anthropic"
    assert kwargs.get("model") == "claude-sonnet-4-6"


@pytest.mark.asyncio
async def test_analyze_fit_node_passes_step_model():
    """analyze_fit should forward the resolved provider/model to llm_call."""
    state = _base_state(current_latex=r"\section{Summary}Content")

    with patch("jam.generation._resolve_step_model", return_value=("anthropic", "claude-sonnet-4-6")), \
         patch("jam.llm.llm_call", new_callable=AsyncMock) as mock_llm, \
         patch("jam.db.get_all_settings", return_value={}):
        mock_llm.return_value = "Fit feedback"
        await analyze_fit(state)

    mock_llm.assert_called_once()
    _, kwargs = mock_llm.call_args
    assert kwargs.get("provider") == "anthropic"
    assert kwargs.get("model") == "claude-sonnet-4-6"


@pytest.mark.asyncio
async def test_node_uses_global_when_no_override():
    """When _resolve_step_model returns (None, None), llm_call is called with provider=None, model=None."""
    state = _base_state(current_latex=r"\section{Summary}Content")

    with patch("jam.generation._resolve_step_model", return_value=(None, None)), \
         patch("jam.llm.llm_call", new_callable=AsyncMock) as mock_llm, \
         patch("jam.db.get_all_settings", return_value={}):
        mock_llm.return_value = "Fit feedback"
        await analyze_fit(state)

    mock_llm.assert_called_once()
    _, kwargs = mock_llm.call_args
    assert kwargs.get("provider") is None
    assert kwargs.get("model") is None


# ── analyze_compress ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_analyze_compress_skips_when_one_page():
    """analyze_compress returns empty feedback when page_count <= 1."""
    state = _base_state()
    state["page_count"] = 1
    result = await analyze_compress(state)
    assert result["compress_feedback"] == ""
    assert result["progress_events"][0]["status"] == "skipped"


@pytest.mark.asyncio
async def test_analyze_compress_returns_feedback_when_over_one_page():
    """analyze_compress calls LLM when page_count > 1."""
    state = _base_state()
    state["page_count"] = 2
    state["current_latex"] = r"\documentclass{article}\begin{document}Hello\end{document}"

    with patch("jam.llm.llm_call", new_callable=AsyncMock, return_value="Remove bullet 3") as mock_llm, \
         patch("jam.db.get_all_settings", return_value={}):
        result = await analyze_compress(state)

    assert result["compress_feedback"] == "Remove bullet 3"
    mock_llm.assert_called_once()


@pytest.mark.asyncio
async def test_analyze_compress_uses_db_prompt():
    """When prompt_analyze_compress is stored in DB, it should be used as the system prompt."""
    custom_prompt = "Custom compress prompt. Pages: {page_count}. {locked_sections_notice}"
    state = _base_state(
        current_latex=r"\section{Summary}Long content",
        page_count=2,
    )

    with patch("jam.db.get_all_settings", return_value={"prompt_analyze_compress": custom_prompt}), \
         patch("jam.llm.llm_call", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = "Shorten bullet points"
        await analyze_compress(state)

    system_prompt = mock_llm.call_args[0][0]
    assert "Custom compress prompt." in system_prompt
    assert "2" in system_prompt  # page_count substituted


@pytest.mark.asyncio
async def test_analyze_compress_zero_page_count_skips():
    """analyze_compress skips (page_count == 0 is also <= 1)."""
    state = _base_state()
    state["page_count"] = 0
    result = await analyze_compress(state)
    assert result["compress_feedback"] == ""


# ── _route_after_compile ──────────────────────────────────────────────────────


def test_route_after_compile_returns_end_on_error():
    from langgraph.graph import END
    state = _base_state(error="something broke", page_count=2)
    assert _route_after_compile(state) == END


def test_route_after_compile_returns_end_on_compile_error():
    from langgraph.graph import END
    state = _base_state(error=None, compile_error="latex syntax error", page_count=2)
    assert _route_after_compile(state) == END


def test_route_after_compile_one_page_goes_to_analysis():
    """Single-page document skips compact loop and fans out to analysis."""
    state = _base_state(error=None, compile_error=None, page_count=1,
                        compact_iteration=0, max_compact_iterations=3)
    result = _route_after_compile(state)
    assert set(result) == {"analyze_fit", "analyze_quality"}


def test_route_after_compile_multipage_within_limit_goes_to_compress():
    """Multi-page document within iteration limit routes to analyze_compress."""
    state = _base_state(error=None, compile_error=None, page_count=2,
                        compact_iteration=0, max_compact_iterations=3)
    result = _route_after_compile(state)
    assert result == "analyze_compress"


def test_route_after_compile_multipage_at_limit_goes_to_analysis():
    """Multi-page document that exhausted all compact iterations fans out to analysis."""
    state = _base_state(error=None, compile_error=None, page_count=2,
                        compact_iteration=3, max_compact_iterations=3)
    result = _route_after_compile(state)
    assert set(result) == {"analyze_fit", "analyze_quality"}


# ── generate_or_revise: compress_feedback in revision prompt ─────────────────


@pytest.mark.asyncio
async def test_generate_revision_includes_compress_feedback():
    """When compress_feedback is set, revision prompt must include it."""
    state = _base_state(
        is_first_generation=False,
        compress_feedback="Shorten the experience section",
        current_latex=r"\documentclass{article}...",
    )

    with patch("jam.llm.llm_call", new_callable=AsyncMock, return_value="revised latex") as mock_llm, \
         patch("jam.db.get_all_settings", return_value={}):
        await generate_or_revise(state)

    user_prompt = mock_llm.call_args[0][1]  # second positional arg
    assert "COMPRESS RECOMMENDATIONS" in user_prompt
    assert "Shorten the experience section" in user_prompt


@pytest.mark.asyncio
async def test_generate_revision_omits_compress_section_when_empty():
    """When compress_feedback is empty, the COMPRESS RECOMMENDATIONS section must NOT appear."""
    state = _base_state(
        is_first_generation=False,
        compress_feedback="",
        current_latex=r"\documentclass{article}...",
    )

    with patch("jam.llm.llm_call", new_callable=AsyncMock, return_value="revised latex") as mock_llm, \
         patch("jam.db.get_all_settings", return_value={}):
        await generate_or_revise(state)

    user_prompt = mock_llm.call_args[0][1]
    assert "COMPRESS RECOMMENDATIONS" not in user_prompt


# ── _LLM_SEM semaphore ────────────────────────────────────────────────────────


def test_llm_semaphore_exists():
    import asyncio
    from jam.generation import _LLM_SEM
    assert isinstance(_LLM_SEM, asyncio.Semaphore)


@pytest.mark.asyncio
async def test_analyze_quality_reports_error_on_llm_failure():
    state = _base_state()
    state["current_latex"] = "\\documentclass{article}\\begin{document}Hello\\end{document}"
    with patch("jam.llm.llm_call", new_callable=AsyncMock, side_effect=Exception("timeout")) as mock_llm, \
         patch("jam.db.get_all_settings", return_value={}):
        result = await analyze_quality(state)
    assert result["quality_feedback"] == ""
    assert result["progress_events"][0]["status"] == "error"
    assert "timeout" in result["progress_events"][0]["detail"]


@pytest.mark.asyncio
async def test_analyze_fit_acquires_llm_semaphore():
    import asyncio
    from jam.generation import _LLM_SEM
    state = _base_state()
    state["current_latex"] = "\\documentclass{article}..."
    state["job_description"] = "test job"

    acquired_during_call = False

    async def checking_llm_call(*args, **kwargs):
        nonlocal acquired_during_call
        # If semaphore value is 0, it means we're holding it
        acquired_during_call = _LLM_SEM._value == 0
        return "feedback"

    with patch("jam.llm.llm_call", new_callable=AsyncMock, side_effect=checking_llm_call), \
         patch("jam.db.get_all_settings", return_value={}):
        await analyze_fit(state)
    assert acquired_during_call, "LLM semaphore should be held during llm_call"


# ── compact loop — analyze_compress iteration tracking ───────────────────────


@pytest.mark.asyncio
async def test_analyze_compress_increments_compact_iteration():
    """analyze_compress should return compact_iteration incremented by 1."""
    state = _base_state(
        page_count=2,
        compact_iteration=0,
        max_compact_iterations=3,
        current_latex=r"\documentclass{article}\begin{document}Hello\end{document}",
    )

    with patch("jam.llm.llm_call", new_callable=AsyncMock, return_value="shorten bullets"), \
         patch("jam.db.get_all_settings", return_value={}):
        result = await analyze_compress(state)

    assert result["compact_iteration"] == 1


@pytest.mark.asyncio
async def test_analyze_compress_no_escalation_on_first_iteration():
    """First iteration (compact_iteration==0) uses the standard prompt — no escalation suffix."""
    state = _base_state(
        page_count=2,
        compact_iteration=0,
        max_compact_iterations=3,
        current_latex=r"\documentclass{article}\begin{document}Hello\end{document}",
    )

    with patch("jam.llm.llm_call", new_callable=AsyncMock, return_value="cut bullets") as mock_llm, \
         patch("jam.db.get_all_settings", return_value={}):
        await analyze_compress(state)

    system_prompt = mock_llm.call_args[0][0]
    assert "Previous compression was insufficient" not in system_prompt
    assert "FINAL ATTEMPT" not in system_prompt


@pytest.mark.asyncio
async def test_analyze_compress_escalates_on_second_iteration():
    """Second iteration (compact_iteration==1) adds the 'be more aggressive' suffix."""
    state = _base_state(
        page_count=2,
        compact_iteration=1,
        max_compact_iterations=3,
        current_latex=r"\documentclass{article}\begin{document}Hello\end{document}",
    )

    with patch("jam.llm.llm_call", new_callable=AsyncMock, return_value="cut more") as mock_llm, \
         patch("jam.db.get_all_settings", return_value={}):
        await analyze_compress(state)

    system_prompt = mock_llm.call_args[0][0]
    assert "Previous compression was insufficient" in system_prompt
    assert "Be more aggressive" in system_prompt


@pytest.mark.asyncio
async def test_analyze_compress_escalates_on_third_iteration():
    """Third iteration (compact_iteration==2) adds the 'FINAL ATTEMPT' suffix."""
    state = _base_state(
        page_count=2,
        compact_iteration=2,
        max_compact_iterations=3,
        current_latex=r"\documentclass{article}\begin{document}Hello\end{document}",
    )

    with patch("jam.llm.llm_call", new_callable=AsyncMock, return_value="remove sections") as mock_llm, \
         patch("jam.db.get_all_settings", return_value={}):
        await analyze_compress(state)

    system_prompt = mock_llm.call_args[0][0]
    assert "FINAL ATTEMPT" in system_prompt


@pytest.mark.asyncio
async def test_analyze_compress_prompt_includes_iteration_count():
    """The system prompt should include the current attempt number and max."""
    state = _base_state(
        page_count=2,
        compact_iteration=1,
        max_compact_iterations=3,
        current_latex=r"\documentclass{article}\begin{document}Hello\end{document}",
    )

    with patch("jam.llm.llm_call", new_callable=AsyncMock, return_value="cut") as mock_llm, \
         patch("jam.db.get_all_settings", return_value={}):
        await analyze_compress(state)

    system_prompt = mock_llm.call_args[0][0]
    # compact_iteration=1 means this is attempt 2 (1+1)
    assert "2" in system_prompt
    assert "3" in system_prompt


@pytest.mark.asyncio
async def test_analyze_compress_skips_when_one_page_does_not_increment():
    """When page_count <= 1, analyze_compress skips LLM and does NOT increment compact_iteration."""
    state = _base_state(page_count=1, compact_iteration=0)
    result = await analyze_compress(state)
    assert result["compress_feedback"] == ""
    assert result["progress_events"][0]["status"] == "skipped"
    # compact_iteration must NOT be in the returned dict when skipping
    assert "compact_iteration" not in result


# ── compact loop — generate_or_revise uses revision path on compact iterations ─


@pytest.mark.asyncio
async def test_generate_or_revise_uses_compact_path_on_compact_iteration():
    """When compact_iteration > 0, use the compression-focused prompt path (not revision)."""
    state = _base_state(
        is_first_generation=True,
        compact_iteration=1,
        compress_feedback="Shorten bullets",
        current_latex=r"\section{Summary}Generated CV",
        kb_docs=[{"text": "Some KB info"}],
        page_count=2,
    )

    with patch("jam.llm.llm_call", new_callable=AsyncMock, return_value=r"\section{Summary}Shorter CV") as mock_llm, \
         patch("jam.db.get_all_settings", return_value={}):
        result = await generate_or_revise(state)

    system_prompt = mock_llm.call_args[0][0]
    # Compact path uses the document compressor system prompt
    assert "document compressor" in system_prompt.lower()
    # The user prompt should include COMPRESS RECOMMENDATIONS but NOT KB docs
    user_prompt = mock_llm.call_args[0][1]
    assert "COMPRESS RECOMMENDATIONS" in user_prompt
    assert "Shorten bullets" in user_prompt
    assert "KNOWLEDGE BASE DOCUMENTS" not in user_prompt


@pytest.mark.asyncio
async def test_generate_or_revise_uses_first_gen_path_when_iteration_zero():
    """When is_first_generation=True and compact_iteration=0, use the first-gen prompt path."""
    state = _base_state(
        is_first_generation=True,
        compact_iteration=0,
        kb_docs=[{"text": "KB doc"}],
    )

    with patch("jam.llm.llm_call", new_callable=AsyncMock, return_value=r"\section{Summary}First gen") as mock_llm, \
         patch("jam.db.get_all_settings", return_value={}):
        await generate_or_revise(state)

    system_prompt = mock_llm.call_args[0][0]
    assert "writer" in system_prompt.lower() or "populate" in system_prompt.lower()


# ── compact loop — prompt constant placeholders ───────────────────────────────


def test_prompt_analyze_compress_has_iteration_placeholders():
    """PROMPT_ANALYZE_COMPRESS must contain {compact_iteration} and {max_compact_iterations}."""
    assert "{compact_iteration}" in PROMPT_ANALYZE_COMPRESS
    assert "{max_compact_iterations}" in PROMPT_ANALYZE_COMPRESS
