"""Unit tests for jam.generation — LangGraph document generation workflow."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from jam.generation import (
    _extract_inline_comments,
    _extract_kb_doc_content,
    _format_instructions,
    _locked_sections,
    _restore_locked_sections,
    _strip_latex_fences,
    build_generation_graph,
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
        "analyze_fit",
        "analyze_quality",
        "apply_suggestions",
        "compile_and_check",
        "reduce_size",
        "finalize",
    }
    assert expected.issubset(node_names)


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
        "current_latex": "",
        "fit_feedback": "",
        "quality_feedback": "",
        "page_count": 0,
        "compile_attempts": 0,
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
    """When kb_include_namespaces is set, those docs are fetched and merged."""
    stored = {
        "kb_retrieval_namespaces": "[]",
        "kb_include_namespaces": json.dumps(["personal-info"]),
        "kb_retrieval_n_results": "5",
    }
    search_results = [{"id": "s1", "content": "search result"}]
    include_docs = [{"id": "i1", "content": "included doc", "title": "My Info"}]

    with patch("jam.db.get_all_settings", return_value=stored), \
         patch("jam.kb_client.search_documents", new_callable=AsyncMock, return_value=search_results), \
         patch("jam.kb_client.list_namespace_documents", new_callable=AsyncMock, return_value=include_docs) as mock_list:

        result = await retrieve_kb_docs(_base_state())

    mock_list.assert_called_once()
    assert mock_list.call_args[0][0] == ["personal-info"]
    # include docs come first, then search results
    assert result["kb_docs"][0]["id"] == "i1"
    assert result["kb_docs"][1]["id"] == "s1"


@pytest.mark.asyncio
async def test_retrieve_kb_docs_deduplicates_by_id():
    """Documents appearing in both include and search should not be duplicated."""
    stored = {
        "kb_retrieval_namespaces": json.dumps(["ns-a"]),
        "kb_include_namespaces": json.dumps(["ns-a"]),
        "kb_retrieval_n_results": "5",
    }
    doc = {"id": "dup-1", "content": "same doc"}
    search_results = [doc, {"id": "unique-s", "content": "only in search"}]
    include_docs = [doc]

    with patch("jam.db.get_all_settings", return_value=stored), \
         patch("jam.kb_client.search_documents", new_callable=AsyncMock, return_value=search_results), \
         patch("jam.kb_client.list_namespace_documents", new_callable=AsyncMock, return_value=include_docs):

        result = await retrieve_kb_docs(_base_state())

    ids = [d["id"] for d in result["kb_docs"]]
    assert ids.count("dup-1") == 1
    assert "unique-s" in ids


@pytest.mark.asyncio
async def test_retrieve_kb_docs_defaults_when_no_settings():
    """When DB has no KB settings, defaults are used (all namespaces, 5 results)."""
    with patch("jam.db.get_all_settings", return_value={}), \
         patch("jam.kb_client.search_documents", new_callable=AsyncMock, return_value=[]) as mock_search, \
         patch("jam.kb_client.list_namespace_documents", new_callable=AsyncMock) as mock_list:

        result = await retrieve_kb_docs(_base_state())

    mock_search.assert_called_once()
    assert mock_search.call_args[1]["n_results"] == 5
    assert mock_search.call_args[1]["namespace_ids"] is None  # empty list → None
    mock_list.assert_not_called()
    assert result["kb_docs"] == []


@pytest.mark.asyncio
async def test_retrieve_kb_docs_progress_event_detail():
    """Progress event should report both search and include counts."""
    stored = {
        "kb_retrieval_namespaces": "[]",
        "kb_include_namespaces": json.dumps(["personal"]),
        "kb_retrieval_n_results": "3",
    }

    with patch("jam.db.get_all_settings", return_value=stored), \
         patch("jam.kb_client.search_documents", new_callable=AsyncMock, return_value=[{"id": "s1", "content": "a"}]), \
         patch("jam.kb_client.list_namespace_documents", new_callable=AsyncMock, return_value=[{"id": "i1", "content": "b"}]):

        result = await retrieve_kb_docs(_base_state())

    evt = result["progress_events"][0]
    assert evt["status"] == "done"
    assert "2 KB docs" in evt["detail"]
    assert "1 searched" in evt["detail"]
    assert "1 included" in evt["detail"]


@pytest.mark.asyncio
async def test_retrieve_kb_docs_padding_over_fetch_then_trim():
    """When padding is set, should fetch n_results + padding, then trim back to n_results."""
    stored = {
        "kb_retrieval_namespaces": "[]",
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
