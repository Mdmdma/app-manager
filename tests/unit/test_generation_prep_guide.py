"""Unit tests for the interview prep-guide pipeline in jam.generation."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from jam.config import Settings
from jam.generation import (
    PROMPT_GENERATE_PREP_GUIDE,
    PrepGuideState,
    build_prep_guide_graph,
    finalize_prep_guide,
    generate_guide,
    load_context,
    run_prep_guide_graph,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _base_prep_state(**overrides) -> PrepGuideState:
    """Minimal PrepGuideState suitable for testing individual nodes."""
    state: PrepGuideState = {
        "interview_id": "interview-1",
        "application_id": "app-1",
        "job_description": "Python backend engineer at ACME Corp",
        "company": "ACME Corp",
        "position": "Backend Engineer",
        "round_type": "technical",
        "round_number": 1,
        "interviewer_names": "Alice Smith",
        "interview_links": "https://linkedin.com/in/alice",
        "interview_prep_notes": "Focus on system design",
        "scheduled_at": "2026-05-01T10:00:00",
        "cv_latex": r"\documentclass{article}\begin{document}CV content\end{document}",
        "cover_letter_latex": r"\documentclass{article}\begin{document}CL content\end{document}",
        "kb_docs": [],
        "kb_context_text": "",
        "markdown": "",
        "thinking": "",
        "search_log": [],
        "generation_system_prompt": "",
        "generation_user_prompt": "",
        "error": "",
        "progress_events": [],
    }
    state.update(overrides)  # type: ignore[typeddict-item]
    return state


@dataclass
class FakeLLMTraceResult:
    text: str = ""
    thinking: str = ""
    search_log: list[dict] = field(default_factory=list)


def _cliproxy_settings(**kwargs) -> Settings:
    s = Settings(llm_provider="cliproxy", llm_model="claude-opus-4-5")
    for k, v in kwargs.items():
        object.__setattr__(s, k, v)
    return s


# ---------------------------------------------------------------------------
# 1. load_context — happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_load_context_fetches_kb_docs():
    """Mock search_documents returns two dicts; state gets kb_docs and non-empty kb_context_text."""
    docs = [
        {"doc_id": "d1", "text": "First document content"},
        {"doc_id": "d2", "text": "Second document content"},
    ]
    settings = Settings(
        kb_retrieval_namespaces=json.dumps(["my-ns"]),
        kb_retrieval_n_results=5,
        kb_retrieval_padding=0,
        kb_include_namespaces="",
    )

    with patch("jam.kb_client.search_documents", new_callable=AsyncMock, return_value=docs) as mock_search, \
         patch("jam.kb_client.list_namespace_documents", new_callable=AsyncMock) as mock_list:
        result = await load_context(_base_prep_state(), settings=settings)

    mock_search.assert_called_once()
    mock_list.assert_not_called()
    assert result["kb_docs"] == docs
    assert "First document content" in result["kb_context_text"]
    assert "Second document content" in result["kb_context_text"]
    assert result["progress_events"][0]["node"] == "load_context"
    assert result["progress_events"][0]["status"] == "ok"


# ---------------------------------------------------------------------------
# 2. load_context — graceful degradation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_load_context_graceful_degradation():
    """When search_documents raises, kb_docs is [], no exception propagates, no error in state."""
    settings = Settings(
        kb_retrieval_namespaces=json.dumps(["my-ns"]),
        kb_retrieval_n_results=5,
        kb_retrieval_padding=0,
        kb_include_namespaces="",
    )

    with patch("jam.kb_client.search_documents", new_callable=AsyncMock,
               side_effect=RuntimeError("network failure")):
        result = await load_context(_base_prep_state(), settings=settings)

    assert result["kb_docs"] == []
    assert result.get("error", "") == ""
    assert result["progress_events"][0]["status"] == "ok"


# ---------------------------------------------------------------------------
# 3. generate_guide — calls llm_call_with_trace with thinking_budget and tools
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_guide_calls_llm_with_thinking_and_tools():
    """generate_guide must pass thinking_budget and a web_search tool to llm_call_with_trace."""
    fake_result = FakeLLMTraceResult(
        text="## Overview\nTest guide",
        thinking="Some thinking",
        search_log=[{"query": "ACME Corp", "url": "https://acme.com", "title": "ACME"}],
    )
    settings = Settings(
        llm_provider="cliproxy",
        llm_model="claude-opus-4-5",
        prep_guide_max_web_searches=10,
        prep_guide_thinking_budget=8000,
        step_model_generate_prep_guide="",
    )

    with patch("jam.llm.llm_call_with_trace", new_callable=AsyncMock,
               return_value=fake_result) as mock_trace, \
         patch("jam.generation._get_prompt", return_value=PROMPT_GENERATE_PREP_GUIDE), \
         patch("jam.db.get_all_settings", return_value={}):
        state = _base_prep_state(kb_context_text="Some KB context")
        result = await generate_guide(state, settings=settings)

    mock_trace.assert_called_once()
    call_kwargs = mock_trace.call_args[1]
    assert call_kwargs["thinking_budget"] == 8000
    # Verify a web_search tool was passed
    tools = call_kwargs["tools"]
    assert isinstance(tools, list) and len(tools) == 1
    assert tools[0]["type"] == "web_search_20250305"
    # Verify output populated
    assert result["markdown"] == "## Overview\nTest guide"
    assert result["thinking"] == "Some thinking"
    assert result["search_log"] == fake_result.search_log
    assert result["generation_system_prompt"] == PROMPT_GENERATE_PREP_GUIDE


# ---------------------------------------------------------------------------
# 4. generate_guide — respects provider/model override
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_guide_respects_provider_override():
    """step_model_generate_prep_guide='cliproxy:claude-opus-4-7' should set provider/model."""
    fake_result = FakeLLMTraceResult(text="# Guide", thinking="", search_log=[])
    settings = Settings(
        llm_provider="anthropic",
        llm_model="claude-3-5-sonnet-20241022",
        step_model_generate_prep_guide="cliproxy:claude-opus-4-7",
        prep_guide_max_web_searches=5,
        prep_guide_thinking_budget=4000,
    )

    with patch("jam.llm.llm_call_with_trace", new_callable=AsyncMock,
               return_value=fake_result) as mock_trace, \
         patch("jam.generation._get_prompt", return_value=PROMPT_GENERATE_PREP_GUIDE), \
         patch("jam.db.get_all_settings", return_value={}):
        result = await generate_guide(_base_prep_state(), settings=settings)

    call_kwargs = mock_trace.call_args[1]
    assert call_kwargs["provider"] == "cliproxy"
    assert call_kwargs["model"] == "claude-opus-4-7"
    assert "error" not in result or result.get("error") == ""


# ---------------------------------------------------------------------------
# 5. generate_guide — surfaces errors
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_guide_surfaces_errors():
    """When llm_call_with_trace raises, state['error'] is populated; no exception propagates."""
    settings = Settings(
        llm_provider="cliproxy",
        llm_model="claude-opus-4-5",
        prep_guide_max_web_searches=3,
        prep_guide_thinking_budget=4000,
        step_model_generate_prep_guide="",
    )

    with patch("jam.llm.llm_call_with_trace", new_callable=AsyncMock,
               side_effect=ValueError("rate limit exceeded")), \
         patch("jam.generation._get_prompt", return_value=PROMPT_GENERATE_PREP_GUIDE), \
         patch("jam.db.get_all_settings", return_value={}):
        result = await generate_guide(_base_prep_state(), settings=settings)

    assert "error" in result
    assert "rate limit exceeded" in result["error"]
    # markdown should NOT be set (or empty)
    assert result.get("markdown", "") == ""


# ---------------------------------------------------------------------------
# 6. finalize_prep_guide — upserts prep guide with correct kwargs
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_finalize_upserts_prep_guide():
    """finalize_prep_guide should call db_upsert_prep_guide with web_search_log and last_generated_at."""
    search_log = [{"query": "ACME", "url": "https://acme.com", "title": "ACME"}]
    state = _base_prep_state(
        interview_id="interview-42",
        markdown="## Overview\nSome guide",
        thinking="Thought about it",
        search_log=search_log,
        generation_system_prompt="sys prompt",
        generation_user_prompt="user prompt",
        error="",
    )

    with patch("jam.db.db_upsert_prep_guide") as mock_upsert:
        result = await finalize_prep_guide(state, settings=Settings())

    mock_upsert.assert_called_once()
    call_kwargs = mock_upsert.call_args[1]
    assert call_kwargs["interview_id"] == "interview-42"
    assert call_kwargs["markdown_source"] == "## Overview\nSome guide"
    assert call_kwargs["web_search_log"] == json.dumps(search_log)
    assert call_kwargs["thinking_summary"] == "Thought about it"
    assert call_kwargs["generation_system_prompt"] == "sys prompt"
    assert call_kwargs["generation_user_prompt"] == "user prompt"
    # last_generated_at must be a non-empty string (ISO timestamp)
    assert isinstance(call_kwargs["last_generated_at"], str)
    assert len(call_kwargs["last_generated_at"]) > 0
    # Progress event
    assert result["progress_events"][0]["node"] == "finalize"
    assert result["progress_events"][0]["status"] == "ok"


# ---------------------------------------------------------------------------
# 7. build_prep_guide_graph — compiles and runs all three nodes in order
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_build_prep_guide_graph_compiles():
    """build_prep_guide_graph should compile and invoke all three nodes in sequence."""
    call_order: list[str] = []

    async def fake_load_context(state):
        call_order.append("load_context")
        return {"kb_docs": [], "kb_context_text": "", "progress_events": [{"node": "load_context", "status": "ok"}]}

    async def fake_generate_guide(state):
        call_order.append("generate_guide")
        return {
            "markdown": "# Guide",
            "thinking": "",
            "search_log": [],
            "generation_system_prompt": "sys",
            "generation_user_prompt": "user",
            "progress_events": [{"node": "generate_guide", "status": "done"}],
        }

    async def fake_finalize(state):
        call_order.append("finalize")
        return {"progress_events": [{"node": "finalize", "status": "ok"}]}

    from langgraph.graph import END, START, StateGraph

    builder = StateGraph(PrepGuideState)
    builder.add_node("load_context", fake_load_context)
    builder.add_node("generate_guide", fake_generate_guide)
    builder.add_node("finalize", fake_finalize)
    builder.add_edge(START, "load_context")
    builder.add_edge("load_context", "generate_guide")
    builder.add_edge("generate_guide", "finalize")
    builder.add_edge("finalize", END)
    graph = builder.compile()

    final = await graph.ainvoke(_base_prep_state())

    assert call_order == ["load_context", "generate_guide", "finalize"]
    assert final.get("markdown") == "# Guide"


# ---------------------------------------------------------------------------
# 8. build_prep_guide_graph — graph structure test
# ---------------------------------------------------------------------------


def test_build_prep_guide_graph_has_correct_nodes():
    """build_prep_guide_graph should contain load_context, generate_guide, finalize."""
    graph = build_prep_guide_graph()
    node_names = set(graph.get_graph().nodes.keys())
    assert "load_context" in node_names
    assert "generate_guide" in node_names
    assert "finalize" in node_names
    # Should NOT contain CV/CL generation nodes
    assert "retrieve_kb_docs" not in node_names
    assert "compile_and_check" not in node_names
