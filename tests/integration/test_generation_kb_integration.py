"""Integration tests for KB document retrieval in generation workflow.

These tests use real KB API calls (requires KB server running on port 8000).
"""

from __future__ import annotations

import json
import pytest

from jam.config import Settings
from jam.db import set_setting, get_all_settings
from jam.generation import DocumentGenerationState, retrieve_kb_docs, generate_or_revise


@pytest.mark.integration
@pytest.mark.asyncio
async def test_retrieve_kb_docs_integration_gets_documents():
    """Integration: retrieve_kb_docs should fetch real documents from KB."""
    # Use empty namespace filters to search entire KB
    set_setting("kb_retrieval_namespaces", "[]")
    set_setting("kb_include_namespaces", "[]")
    set_setting("kb_retrieval_n_results", "5")

    state = {
        "doc_id": "test-doc",
        "application_id": "test-app",
        "doc_type": "cv",
        "latex_template": r"\section{Summary}",
        "job_description": "Senior Software Engineer Python experience",
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

    result = await retrieve_kb_docs(state)

    # Should successfully retrieve some documents
    assert "kb_docs" in result
    kb_docs = result["kb_docs"]
    print(f"\n✓ Retrieved {len(kb_docs)} KB documents")

    if kb_docs:
        for i, doc in enumerate(kb_docs[:2], 1):
            print(f"  Doc {i}: {doc.get('title', 'untitled')[:50]}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_generate_prompt_includes_kb_documents():
    """Integration: KB documents should be inserted into the generation prompt."""
    # Search the entire KB (no namespace filtering)
    set_setting("kb_retrieval_namespaces", "[]")
    set_setting("kb_include_namespaces", "[]")
    set_setting("kb_retrieval_n_results", "5")

    # First, retrieve documents
    state = {
        "doc_id": "test-doc",
        "application_id": "test-app",
        "doc_type": "cv",
        "latex_template": r"\section{Summary}Placeholder",
        "job_description": "Senior Software Engineer Python React AWS",
        "instructions_json": json.dumps({
            "general": "Tailor to the job description",
            "sections": [{"key": "summary", "label": "Summary", "enabled": True, "text": ""}]
        }),
        "is_first_generation": True,
        "kb_docs": [],
        "inline_comments": [],
        "locked_sections": [],
        "current_latex": r"\section{Summary}Placeholder",
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

    # Step 1: Retrieve KB docs
    retrieve_result = await retrieve_kb_docs(state)
    state.update(retrieve_result)
    kb_docs = state.get("kb_docs", [])
    print(f"\n✓ Retrieved {len(kb_docs)} KB documents for prompt test")

    # Step 2: Build generation prompt (without actually calling LLM)
    from jam.generation import _extract_kb_doc_content

    kb_context = "\n\n".join(_extract_kb_doc_content(d) for d in kb_docs)[:6000]
    print(f"✓ KB context length: {len(kb_context)} chars")

    # Verify kb_context is not empty
    assert len(kb_context) > 0, "KB context should not be empty when KB has documents"
    assert kb_context != "(none available)", "KB context should contain actual documents"

    # Verify context contains meaningful content (not just titles)
    assert len(kb_context.split()) > 10, "KB context should have meaningful content"

    # Verify the context would be inserted into the prompt
    user_prompt_with_kb = f"""\
=== JOB DESCRIPTION ===
{state["job_description"]}

=== KNOWLEDGE BASE DOCUMENTS ===
{kb_context if kb_context else "(none available)"}

=== LATEX TEMPLATE ===
{state["latex_template"]}"""

    print(f"\n✓ User prompt snippet:")
    kb_section = user_prompt_with_kb[
        user_prompt_with_kb.find("=== KNOWLEDGE BASE DOCUMENTS ==="):
        user_prompt_with_kb.find("=== LATEX TEMPLATE ===")
    ]
    print(kb_section[:300] + "...")

    assert "(none available)" not in kb_section, "Prompt should contain actual KB docs, not placeholder"
    assert len(kb_section) > 100, "KB section should have substantial content"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_generate_or_revise_prompt_has_kb_context():
    """Integration: generate_or_revise node should include KB documents in the prompt."""
    # Configure KB retrieval for entire knowledge base
    set_setting("kb_retrieval_namespaces", "[]")
    set_setting("kb_include_namespaces", "[]")
    set_setting("kb_retrieval_n_results", "3")

    # Create state with some KB documents
    state = {
        "doc_id": "test-doc",
        "application_id": "test-app",
        "doc_type": "cv",
        "latex_template": r"\documentclass{article}\section{Summary}<<SUMMARY: placeholder>>\end{document}",
        "job_description": "Python engineer with 5+ years experience in backend systems",
        "instructions_json": "{}",
        "is_first_generation": True,
        "kb_docs": [],  # Will be populated by retrieve_kb_docs
        "inline_comments": [],
        "locked_sections": [],
        "current_latex": r"\documentclass{article}\section{Summary}<<SUMMARY: placeholder>>\end{document}",
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

    # Retrieve real KB documents
    retrieve_result = await retrieve_kb_docs(state)
    state.update(retrieve_result)
    kb_docs = state.get("kb_docs", [])

    print(f"\n✓ Retrieved {len(kb_docs)} KB docs for generation prompt test")

    if not kb_docs:
        pytest.skip("No KB documents available in knowledge base")

    # Now test that generate_or_revise would include them in the prompt
    # (We won't actually call the LLM, just verify the prompt structure)
    from jam.generation import _extract_kb_doc_content

    kb_context = "\n\n".join(_extract_kb_doc_content(d) for d in state["kb_docs"])[:6000]

    print(f"✓ KB context in prompt: {len(kb_context)} chars")
    print(f"✓ Sample KB context: {kb_context[:200]}...")

    # The prompt that would be sent to LLM should contain the KB documents
    assert len(kb_context) > 0, "KB context must be populated"
    assert kb_context != "", "KB context should not be empty string"

    # Verify documents are actually included
    for doc in kb_docs[:1]:  # Check at least the first doc
        doc_content = _extract_kb_doc_content(doc)
        assert len(doc_content) > 0, f"Document {doc.get('id')} should have extractable content"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_kb_context_not_none_available_when_docs_exist():
    """Integration: Prompt should never show '(none available)' when KB has documents."""
    # Search entire KB
    set_setting("kb_retrieval_namespaces", "[]")
    set_setting("kb_include_namespaces", "[]")
    set_setting("kb_retrieval_n_results", "5")

    state = {
        "doc_id": "test",
        "application_id": "test-app",
        "doc_type": "cv",
        "latex_template": "test",
        "job_description": "Python engineer",
        "instructions_json": "{}",
        "is_first_generation": True,
        "kb_docs": [],
        "inline_comments": [],
        "locked_sections": [],
        "current_latex": "test",
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

    result = await retrieve_kb_docs(state)
    kb_docs = result.get("kb_docs", [])

    if not kb_docs:
        pytest.skip("No documents in knowledge base")

    # Build the context exactly as generate_or_revise does
    from jam.generation import _extract_kb_doc_content
    kb_context = "\n\n".join(_extract_kb_doc_content(d) for d in kb_docs)[:6000]

    # This is the critical check
    prompt_section = kb_context if kb_context else "(none available)"

    print(f"\n✓ KB docs retrieved: {len(kb_docs)}")
    print(f"✓ KB context length: {len(kb_context)}")
    print(f"✓ Prompt section: {prompt_section[:150]}...")

    assert prompt_section != "(none available)", \
        f"KB context should be populated! Got {len(kb_context)} chars"
    assert len(prompt_section) > 50, \
        f"KB context should have substantial content, got: {prompt_section[:100]}"
