from __future__ import annotations

import asyncio
import json as _json
import logging
import os
import shutil
import tempfile
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

import httpx
from fastapi import BackgroundTasks, FastAPI, APIRouter, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse, Response, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator

from jam.html_page import HTML_PAGE
from jam import msgraph_client
from jam.db import (
    init_db, get_all_settings, set_setting, set_settings_batch, delete_setting, get_catalog,
    create_application as db_create_application,
    get_application as db_get_application,
    list_applications as db_list_applications,
    update_application as db_update_application,
    delete_application as db_delete_application,
    create_document as db_create_document,
    get_document as db_get_document,
    list_documents as db_list_documents,
    update_document as db_update_document,
    delete_document as db_delete_document,
    create_version as db_create_version,
    list_versions as db_list_versions,
    get_version as db_get_version,
    create_extra_question as db_create_extra_question,
    list_extra_questions as db_list_extra_questions,
    get_extra_question as db_get_extra_question,
    update_extra_question as db_update_extra_question,
    delete_extra_question as db_delete_extra_question,
    create_interview_round as db_create_interview_round,
    list_interview_rounds as db_list_interview_rounds,
    get_interview_round as db_get_interview_round,
    update_interview_round as db_update_interview_round,
    delete_interview_round as db_delete_interview_round,
    create_offer as db_create_offer,
    list_offers as db_list_offers,
    get_offer as db_get_offer,
    update_offer as db_update_offer,
    delete_offer as db_delete_offer,
    create_rejection as db_create_rejection,
    list_rejections as db_list_rejections,
    get_rejection as db_get_rejection,
    update_rejection as db_update_rejection,
    delete_rejection as db_delete_rejection,
    db_get_prep_guide,
    db_upsert_prep_guide,
)
from jam.llm import extract_job_info, extract_email_info
from jam.kb_client import ingest_url, ingest_text, close_client
from jam.generation import run_prep_guide_graph

_ENV_MAP = {
    "openai_api_key":    "OPENAI_API_KEY",
    "anthropic_api_key": "ANTHROPIC_API_KEY",
    "groq_api_key":      "GROQ_API_KEY",
    "ollama_base_url":   "OLLAMA_BASE_URL",
    "cliproxy_base_url": "CLIPROXY_BASE_URL",
    "cliproxy_api_key":  "CLIPROXY_API_KEY",
    "llm_provider":      "LLM_PROVIDER",
    "llm_model":         "LLM_MODEL",
    "gmail_client_id": "GMAIL_CLIENT_ID",
    "gmail_client_secret": "GMAIL_CLIENT_SECRET",
    "gmail_refresh_token": "GMAIL_REFRESH_TOKEN",
    "gmail_user_email": "GMAIL_USER_EMAIL",
    "search_enrichment_enabled": "JAM_SEARCH_ENRICHMENT_ENABLED",
}

_PLAIN_KEYS = {
    "llm_provider", "llm_model", "ollama_base_url", "cliproxy_base_url",
    "cv_latex_template", "cover_letter_latex_template",
    "gmail_client_id", "gmail_user_email",
    "kb_retrieval_namespaces", "kb_retrieval_n_results",
    "kb_retrieval_padding", "kb_include_namespaces",
    "personal_full_name", "personal_email", "personal_phone",
    "personal_website", "personal_address",
    "personal_photo", "personal_signature",
    "prompt_analyze_fit", "prompt_analyze_compress",
    "prompt_generate_first:cv", "prompt_generate_first:cover_letter",
    "prompt_generate_revise:cv", "prompt_generate_revise:cover_letter",
    "prompt_analyze_quality:cv", "prompt_analyze_quality:cover_letter",
    "step_model_generate_or_revise", "step_model_analyze_fit",
    "step_model_analyze_quality", "step_model_analyze_compress",
    "search_enrichment_enabled",
}

DEFAULT_CV_TEMPLATE = r"""\documentclass[10pt,a4paper]{article}

\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage[top=1.2cm, bottom=1.2cm, left=1.4cm, right=1.4cm]{geometry}
\usepackage{enumitem}
\usepackage{titlesec}
\usepackage{hyperref}
\usepackage{xcolor}
\usepackage{graphicx}

\definecolor{accent}{HTML}{1D4ED8}
\hypersetup{colorlinks=true, urlcolor=accent}
\pagestyle{empty}
\setlength{\parindent}{0pt}

\titleformat{\section}{\large\bfseries\color{accent}}{}{0em}{}%
  [{\color{accent}\vspace{1pt}\hrule height 0.6pt}]
\titlespacing{\section}{0pt}{8pt}{4pt}

\begin{document}

% ── Header ────────────────────────────────────────────────────────────────────
\noindent
\begin{minipage}[c]{0.2\textwidth}
    \includegraphics[width=0.69\textwidth]{photo.png}
\end{minipage}%
\hfill
\begin{minipage}[c]{0.45\textwidth}
    \centering
    \textbf{\Huge \scshape <<FULL-NAME: Jane Doe>>} \\[4pt]
    {\large\color{gray} <<TARGET-ROLE: Senior Software Engineer>>}
\end{minipage}%
\hfill
\begin{minipage}[c]{0.3\textwidth}
    \raggedleft
    \small \href{mailto:<<EMAIL: jane.doe@example.com>>}{\underline{<<EMAIL: jane.doe@example.com>>}} \\[3pt]
    \small <<PHONE: +49 170 123 4567>> \\[3pt]
    \small <<CITY-COUNTRY: Berlin, Germany>> \\[3pt]
    \small \href{https://linkedin.com/in/<<LINKEDIN-SLUG: jane-doe-123>>}{\underline{LinkedIn}} \\[3pt]
    \small \href{https://github.com/<<GITHUB-USER: janedoe>>}{\underline{GitHub}}
\end{minipage}
\vspace{4pt}

% ── Summary ───────────────────────────────────────────────────────────────────
\section{Summary}

<<SUMMARY: 2-3 sentences. State years of experience, core expertise, and a standout quality. Example: "7 years building distributed systems and data pipelines in Python and Go. Led engineering teams of up to 5 delivering products used by 200k users. Passionate about developer tooling and platform reliability.">>

% ── Experience ────────────────────────────────────────────────────────────────
\section{Experience}

\textbf{<<JOB-TITLE-1: Senior Software Engineer>>} \hfill <<DATE-FROM-1: Jan 2022>> -- <<DATE-TO-1: Present>>\\
\textit{<<COMPANY-1: Acme Corp>>} \hfill <<LOCATION-1: Berlin, Germany>>
\begin{itemize}[nosep,leftmargin=1.5em,topsep=2pt]
  \item <<ACHIEVEMENT-1: Quantified impact with action verb. Example: "Reduced API p99 latency by 40\% (800\,ms to 480\,ms) by introducing Redis caching.">>
  \item <<ACHIEVEMENT-2: Process or scale impact. Example: "Led monolith-to-microservices migration; raised deployment frequency from weekly to daily.">>
  \item <<ACHIEVEMENT-3: People or knowledge impact. Example: "Mentored 3 junior engineers; introduced code-review standards adopted across the organisation.">>
\end{itemize}

\vspace{4pt}
\textbf{<<JOB-TITLE-2: Software Engineer>>} \hfill <<DATE-FROM-2: Mar 2019>> -- <<DATE-TO-2: Dec 2021>>\\
\textit{<<COMPANY-2: Startup GmbH>>} \hfill <<LOCATION-2: Munich, Germany>>
\begin{itemize}[nosep,leftmargin=1.5em,topsep=2pt]
  \item <<ACHIEVEMENT-4: Technical achievement with scale. Example: "Built real-time data pipeline processing 50k events/s with Kafka and Apache Flink.">>
  \item <<ACHIEVEMENT-5: Product or business outcome. Example: "Delivered analytics dashboard adopted by 200+ enterprise clients; contributed to 15\% revenue uplift.">>
\end{itemize}

% ── Education ─────────────────────────────────────────────────────────────────
\section{Education}

\textbf{<<DEGREE: M.Sc. Computer Science>>} \hfill <<GRAD-YEAR: 2019>>\\
\textit{<<UNIVERSITY: Technical University of Munich>>} \hfill <<UNI-CITY: Munich, Germany>>

% ── Skills ────────────────────────────────────────────────────────────────────
\section{Skills}

\begin{tabular}{@{}l@{\hspace{1em}}l}
  \textbf{Programming:}    & <<LANGUAGES: Python, Go, TypeScript, SQL>> \\
  \textbf{Frameworks:}     & <<FRAMEWORKS: FastAPI, React, gRPC, dbt>> \\
  \textbf{Infrastructure:} & <<INFRA: AWS (ECS, RDS, Lambda), Kubernetes, Terraform, Docker>> \\
  \textbf{Languages:}      & <<SPOKEN-LANGUAGES: English (fluent), German (B2), French (A2)>> \\
\end{tabular}

\end{document}"""

DEFAULT_COVER_LETTER_TEMPLATE = r"""\documentclass[11pt,a4paper]{letter}

\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage[margin=2.5cm]{geometry}
\usepackage{hyperref}
\usepackage{graphicx}

\hypersetup{colorlinks=true, urlcolor=blue}

% Section marker used by jam's instructions panel — invisible in the compiled output.
\newcommand{\paragraph}[1]{}

\begin{document}

\begin{letter}{%
  <<HIRING-MANAGER-NAME: Ms. Sarah Müller>>\\
  <<COMPANY-NAME: Acme Corp GmbH>>\\
  <<COMPANY-ADDRESS: Unter den Linden 1, 10117 Berlin>>
}

\date{\today}
\opening{Dear <<SALUTATION: Ms. Müller>>,}

\paragraph{Opening}
<<OPENING-PARAGRAPH: 1-2 sentences. State the exact role, how you found it, and a brief hook. Example: "I am applying for the Senior Software Engineer position (Ref: JD-2026-142) at Acme Corp, which I discovered on your careers page. Your focus on open-source developer tooling aligns closely with my background in platform engineering.">>

\paragraph{Body}
<<BODY-PARAGRAPH: 2-4 sentences. Highlight one or two concrete accomplishments directly relevant to the job requirements. Example: "At Startup GmbH I led the redesign of our data ingestion pipeline, cutting processing latency by 60\% and enabling three new enterprise client onboardings within a single quarter. I also introduced automated dependency-audit tooling that was subsequently adopted across all backend teams.">>

\paragraph{Fit}
<<FIT-PARAGRAPH: 1-3 sentences. Explain why this specific company excites you and what makes you a strong mutual fit. Example: "I am particularly attracted to Acme Corp because of your investment in Rust-based infrastructure tooling and your culture of engineering excellence. I am confident I can contribute meaningfully from day one.">>

\paragraph{Closing}
<<CLOSING-PARAGRAPH: 1-2 sentences. Express enthusiasm and include a concrete call to action. Example: "I would welcome the opportunity to discuss my application in an interview. I am available from the week of 6 April onwards and happy to accommodate your schedule.">>

\closing{<<SIGN-OFF: Best regards>>,}

\vspace{-10pt}
\fromsig{\includegraphics[height=1.2cm]{signature.png}}

\end{letter}
\end{document}"""


# PDF cache: stores most recently compiled PDFs per document
_pdf_cache: dict[str, bytes] = {}

def _auto_create_documents(app_id: str) -> None:
    """Create default CV and Cover Letter documents for a new application."""
    stored = get_all_settings()
    cv_tpl = stored.get("cv_latex_template") or DEFAULT_CV_TEMPLATE
    cl_tpl = stored.get("cover_letter_latex_template") or DEFAULT_COVER_LETTER_TEMPLATE
    db_create_document(application_id=app_id, doc_type="cv", title="CV", latex_source=cv_tpl)
    db_create_document(application_id=app_id, doc_type="cover_letter", title="Cover Letter", latex_source=cl_tpl)


# Application status enum
class ApplicationStatus(str, Enum):
    not_applied_yet = "not_applied_yet"
    applied = "applied"
    screening = "screening"
    interviewing = "interviewing"
    offered = "offered"
    rejected = "rejected"
    accepted = "accepted"
    withdrawn = "withdrawn"


class WorkMode(str, Enum):
    remote = "remote"
    hybrid = "hybrid"
    onsite = "onsite"


# Pydantic models
class ApplicationCreate(BaseModel):
    """Request body for creating a new application."""
    company: str = Field(..., min_length=1, max_length=255)
    position: str = Field(..., min_length=1, max_length=255)
    status: ApplicationStatus = ApplicationStatus.not_applied_yet
    url: Optional[str] = Field(None, max_length=2048)
    notes: Optional[str] = Field(None, max_length=5000)
    salary_range: Optional[str] = Field(None, max_length=255)
    location: Optional[str] = Field(None, max_length=255)
    work_mode: Optional[WorkMode] = None
    contact_person: Optional[str] = Field(None, max_length=255)
    applied_date: Optional[str] = Field(None)  # ISO date string
    opening_date: Optional[str] = Field(None)  # ISO date string
    closing_date: Optional[str] = Field(None)  # ISO date string
    description: Optional[str] = Field(None, max_length=5000)
    full_text: Optional[str] = None


class ApplicationUpdate(BaseModel):
    """Request body for updating an application."""
    company: Optional[str] = Field(None, min_length=1, max_length=255)
    position: Optional[str] = Field(None, min_length=1, max_length=255)
    status: Optional[ApplicationStatus] = None
    url: Optional[str] = Field(None, max_length=2048)
    notes: Optional[str] = Field(None, max_length=5000)
    salary_range: Optional[str] = Field(None, max_length=255)
    location: Optional[str] = Field(None, max_length=255)
    work_mode: Optional[WorkMode] = None
    contact_person: Optional[str] = Field(None, max_length=255)
    applied_date: Optional[str] = None
    opening_date: Optional[str] = None
    closing_date: Optional[str] = None
    description: Optional[str] = Field(None, max_length=5000)
    full_text: Optional[str] = None


class Application(BaseModel):
    """Application domain model."""
    id: UUID
    company: str
    position: str
    status: ApplicationStatus
    url: Optional[str] = None
    notes: Optional[str] = None
    salary_range: Optional[str] = None
    location: Optional[str] = None
    work_mode: Optional[str] = None
    contact_person: Optional[str] = None
    opening_date: Optional[str] = None
    closing_date: Optional[str] = None
    description: Optional[str] = None
    full_text: Optional[str] = None
    applied_date: str  # ISO date string
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ImportFromUrlRequest(BaseModel):
    """Request body for importing a job posting from a URL."""
    url: str = Field(..., min_length=1, max_length=2048)


class ImportFromUrlResponse(BaseModel):
    """Response for URL import."""
    application: Application
    extraction: dict
    kb_ingested: bool


class ImportFromTextRequest(BaseModel):
    """Request body for importing a job posting from pasted text."""
    text: str = Field(..., min_length=1)

    @field_validator("text")
    @classmethod
    def text_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("text must not be blank")
        return v


# ImportFromTextResponse has the same shape as ImportFromUrlResponse.
ImportFromTextResponse = ImportFromUrlResponse


class SettingsRequest(BaseModel):
    """Request body for saving settings."""
    model_config = ConfigDict(populate_by_name=True)

    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None
    ollama_base_url: Optional[str] = None
    cliproxy_base_url: Optional[str] = None
    cliproxy_api_key: Optional[str] = None
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    cv_latex_template: Optional[str] = None
    cover_letter_latex_template: Optional[str] = None
    gmail_client_id: Optional[str] = None
    gmail_client_secret: Optional[str] = None
    gmail_refresh_token: Optional[str] = None
    gmail_user_email: Optional[str] = None
    kb_retrieval_namespaces: Optional[str] = None
    kb_retrieval_n_results: Optional[int] = None
    kb_retrieval_padding: Optional[int] = None
    kb_include_namespaces: Optional[str] = None
    personal_full_name: Optional[str] = None
    personal_email: Optional[str] = None
    personal_phone: Optional[str] = None
    personal_website: Optional[str] = None
    personal_address: Optional[str] = None
    personal_photo: Optional[str] = None
    personal_signature: Optional[str] = None
    prompt_analyze_fit: Optional[str] = None
    prompt_analyze_compress: Optional[str] = None
    # Doc-type-specific prompt overrides (use alias for colon-keyed DB names)
    prompt_generate_first_cv: Optional[str] = Field(None, alias="prompt_generate_first:cv")
    prompt_generate_first_cl: Optional[str] = Field(None, alias="prompt_generate_first:cover_letter")
    prompt_generate_revise_cv: Optional[str] = Field(None, alias="prompt_generate_revise:cv")
    prompt_generate_revise_cl: Optional[str] = Field(None, alias="prompt_generate_revise:cover_letter")
    prompt_analyze_quality_cv: Optional[str] = Field(None, alias="prompt_analyze_quality:cv")
    prompt_analyze_quality_cl: Optional[str] = Field(None, alias="prompt_analyze_quality:cover_letter")
    step_model_generate_or_revise: Optional[str] = None
    step_model_analyze_fit: Optional[str] = None
    step_model_analyze_quality: Optional[str] = None
    step_model_analyze_compress: Optional[str] = None
    search_enrichment_enabled: Optional[bool] = None


class DocType(str, Enum):
    cv = "cv"
    cover_letter = "cover_letter"


class DocumentCreate(BaseModel):
    doc_type: DocType
    title: str = Field("Untitled", max_length=255)
    latex_source: str = Field("", max_length=500000)
    prompt_text: str = Field("", max_length=100000)


class DocumentUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    latex_source: Optional[str] = Field(None, max_length=500000)
    prompt_text: Optional[str] = Field(None, max_length=100000)


class DocumentResponse(BaseModel):
    id: str
    application_id: str
    doc_type: DocType
    title: str
    latex_source: str
    prompt_text: str
    created_at: str
    updated_at: str


class DocumentVersionResponse(BaseModel):
    id: str
    document_id: str
    version_number: int
    latex_source: str
    prompt_text: str
    compiled_at: str


class ExtraQuestionCreate(BaseModel):
    question: str = ""
    answer: str = ""
    word_cap: Optional[int] = None
    sort_order: int = 0


class ExtraQuestionUpdate(BaseModel):
    question: Optional[str] = None
    answer: Optional[str] = None
    word_cap: Optional[int] = None
    sort_order: Optional[int] = None


class ExtraQuestionResponse(BaseModel):
    id: str
    application_id: str
    question: str
    answer: str
    word_cap: Optional[int] = None
    sort_order: int
    created_at: str
    updated_at: str


class InterviewRoundCreate(BaseModel):
    round_type: str = "other"
    round_number: int = 1
    scheduled_at: Optional[str] = None
    completed_at: Optional[str] = None
    interviewer_names: str = ""
    location: str = ""
    links: str = ""
    status: str = "scheduled"
    prep_notes: str = ""
    debrief_notes: str = ""
    questions_asked: str = ""
    went_well: str = ""
    to_improve: str = ""
    confidence: Optional[int] = None
    sort_order: int = 0
    scheduled_time: Optional[str] = None


class InterviewRoundUpdate(BaseModel):
    round_type: Optional[str] = None
    round_number: Optional[int] = None
    scheduled_at: Optional[str] = None
    completed_at: Optional[str] = None
    interviewer_names: Optional[str] = None
    location: Optional[str] = None
    links: Optional[str] = None
    status: Optional[str] = None
    prep_notes: Optional[str] = None
    debrief_notes: Optional[str] = None
    questions_asked: Optional[str] = None
    went_well: Optional[str] = None
    to_improve: Optional[str] = None
    confidence: Optional[int] = None
    sort_order: Optional[int] = None
    scheduled_time: Optional[str] = None


class InterviewRoundResponse(BaseModel):
    id: str
    application_id: str
    round_type: str
    round_number: int
    scheduled_at: Optional[str] = None
    completed_at: Optional[str] = None
    interviewer_names: str
    location: str
    links: str = ""
    status: str
    prep_notes: str
    debrief_notes: str
    questions_asked: str
    went_well: str
    to_improve: str
    confidence: Optional[int] = None
    sort_order: int
    scheduled_time: str = ""
    graph_event_id: Optional[str] = None
    created_at: str
    updated_at: str


class OfferCreate(BaseModel):
    status: str = "pending"
    base_salary: Optional[float] = None
    currency: str = "EUR"
    bonus: str = ""
    equity: str = ""
    signing_bonus: str = ""
    benefits: str = ""
    pto_days: Optional[int] = None
    remote_policy: str = ""
    start_date: Optional[str] = None
    expiry_date: Optional[str] = None
    notes: str = ""
    sort_order: int = 0


class OfferUpdate(BaseModel):
    status: Optional[str] = None
    base_salary: Optional[float] = None
    currency: Optional[str] = None
    bonus: Optional[str] = None
    equity: Optional[str] = None
    signing_bonus: Optional[str] = None
    benefits: Optional[str] = None
    pto_days: Optional[int] = None
    remote_policy: Optional[str] = None
    start_date: Optional[str] = None
    expiry_date: Optional[str] = None
    notes: Optional[str] = None
    sort_order: Optional[int] = None


class OfferResponse(BaseModel):
    id: str
    application_id: str
    status: str
    base_salary: Optional[float] = None
    currency: str
    bonus: str
    equity: str
    signing_bonus: str
    benefits: str
    pto_days: Optional[int] = None
    remote_policy: str
    start_date: Optional[str] = None
    expiry_date: Optional[str] = None
    notes: str
    sort_order: int
    created_at: str
    updated_at: str


class RejectionCreate(BaseModel):
    summary: str = ""
    reasons: str = ""
    links: str = ""
    raw_email: str = ""
    received_at: Optional[str] = None
    followup_status: str = "none"
    followup_notes: str = ""


class RejectionUpdate(BaseModel):
    summary: Optional[str] = None
    reasons: Optional[str] = None
    links: Optional[str] = None
    raw_email: Optional[str] = None
    received_at: Optional[str] = None
    followup_status: Optional[str] = None
    followup_notes: Optional[str] = None


class RejectionResponse(BaseModel):
    id: str
    application_id: str
    summary: str
    reasons: str
    links: str
    raw_email: str
    received_at: Optional[str] = None
    followup_status: str
    followup_notes: str
    created_at: str
    updated_at: str


class EmailIngestRequest(BaseModel):
    email_text: str = Field(..., min_length=20)


class EmailIngestResponse(BaseModel):
    kind: str
    confidence: str
    interview: Optional[InterviewRoundResponse] = None
    rejection: Optional[RejectionResponse] = None
    extraction: dict


class MSGraphSettingsResponse(BaseModel):
    connected: bool
    user_email: str = ""


class PrepGuideResponse(BaseModel):
    """Response model for interview prep guide endpoints."""
    markdown: str = ""
    generation_system_prompt: Optional[str] = None
    generation_user_prompt: Optional[str] = None
    web_search_log: Optional[str] = None
    thinking_summary: Optional[str] = None
    last_generated_at: Optional[str] = None
    updated_at: Optional[str] = None
    created_at: Optional[str] = None


class PrepGuideUpdateRequest(BaseModel):
    """Request body for updating (upserting) an interview prep guide."""
    markdown: str


async def _fetch_page_text(url: str) -> tuple[str, str]:
    """Fetch a URL and return ``(text, content_kind)``.

    *content_kind* is one of ``"html"``, ``"pdf"``, or ``"text"``.

    Supports HTML pages, PDFs, and plain-text files.  Content type is
    determined from the response ``Content-Type`` header, falling back to
    the URL extension when the header is ambiguous.
    """
    import re as _re

    async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
        resp = await client.get(url, headers={"User-Agent": "jam/0.1"})
        resp.raise_for_status()

        content_type = resp.headers.get("content-type", "")
        is_pdf = "application/pdf" in content_type or url.lower().endswith(".pdf")

        if is_pdf:
            import fitz  # pymupdf

            doc = fitz.open(stream=resp.content, filetype="pdf")
            pages = [page.get_text() for page in doc]
            doc.close()
            text = "\n".join(pages)
            kind = "pdf"
        elif "text/plain" in content_type:
            text = resp.text
            kind = "text"
        else:
            # Default: treat as HTML
            html = resp.text
            html = _re.sub(
                r"<(script|style)[^>]*>.*?</\1>",
                " ",
                html,
                flags=_re.DOTALL | _re.IGNORECASE,
            )
            text = _re.sub(r"<[^>]+>", " ", html)
            kind = "html"

        text = _re.sub(r"\s+", " ", text).strip()
        return text, kind


router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def index():
    """Serve the main web UI."""
    return HTMLResponse(content=HTML_PAGE)


@router.get("/health")
async def health():
    """Health check — reports jam status, kb reachability, and cliproxy reachability."""
    from jam.config import Settings

    settings = Settings()
    kb_status = "unreachable"
    cliproxy_status = "unreachable"
    async with httpx.AsyncClient(timeout=3) as client:
        try:
            resp = await client.get(f"{settings.kb_api_url.rstrip('/')}/health")
            if resp.status_code == 200:
                kb_status = "ok"
        except Exception:
            pass
        try:
            resp = await client.get(f"{settings.cliproxy_base_url.rstrip('/')}")
            if 200 <= resp.status_code < 300:
                cliproxy_status = "ok"
        except Exception:
            pass
    return {"status": "ok", "kb_status": kb_status, "cliproxy_status": cliproxy_status}


@router.get("/applications", response_model=list[Application])
async def list_applications():
    """Get all applications."""
    rows = db_list_applications()
    return [Application(**row) for row in rows]


@router.post("/applications", response_model=Application, status_code=201)
async def create_application(req: ApplicationCreate):
    """Create a new application."""
    from datetime import date

    applied_date = req.applied_date or date.today().isoformat()
    now = datetime.now(timezone.utc).isoformat()
    app_id = str(uuid4())
    row = db_create_application(
        id=app_id,
        company=req.company,
        position=req.position,
        status=req.status.value,
        url=req.url,
        notes=req.notes,
        salary_range=req.salary_range,
        location=req.location,
        work_mode=req.work_mode.value if req.work_mode else None,
        contact_person=req.contact_person,
        opening_date=req.opening_date,
        closing_date=req.closing_date,
        description=req.description,
        full_text=req.full_text,
        applied_date=applied_date,
        created_at=now,
        updated_at=now,
    )
    _auto_create_documents(app_id)
    return Application(**row)


@router.post("/applications/from-url", response_model=ImportFromUrlResponse, status_code=201)
async def import_from_url(req: ImportFromUrlRequest):
    """Import a job posting from a URL: fetch, extract via LLM, create application, ingest into kb."""
    from datetime import date
    from jam.config import Settings

    # 1. Fetch and strip HTML
    try:
        text, content_kind = await _fetch_page_text(req.url)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=422, detail=f"Failed to fetch URL: {exc}")

    if not text or len(text) < 50:
        raise HTTPException(status_code=422, detail="Page content too short or empty")

    # 2. Extract job info via LLM
    settings = Settings()
    try:
        info = await extract_job_info(text, settings)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"LLM extraction failed: {exc}")

    company = info.get("company") or "Unknown"
    position = info.get("position") or "Unknown"

    # 3. Build notes from extracted fields
    notes_parts = []
    if info.get("requirements"):
        notes_parts.append(f"Requirements: {info['requirements']}")
    notes = "\n".join(notes_parts) or None

    # 4. Create the application
    now = datetime.now(timezone.utc).isoformat()
    app_id = str(uuid4())
    app_dict = db_create_application(
        id=app_id,
        company=company,
        position=position,
        status=ApplicationStatus.not_applied_yet.value,
        url=req.url,
        notes=notes,
        salary_range=info.get("salary_range"),
        location=info.get("location"),
        opening_date=info.get("opening_date"),
        closing_date=info.get("closing_date"),
        description=info.get("description"),
        full_text=text,
        applied_date=date.today().isoformat(),
        created_at=now,
        updated_at=now,
    )
    _auto_create_documents(app_id)

    # 5. Ingest into kb (fire-and-forget — don't fail if kb is down)
    kb_ingested = False
    try:
        if content_kind == "html":
            await ingest_url(req.url, settings)
        else:
            await ingest_text(text, req.url, settings)
        kb_ingested = True
    except Exception:
        pass

    return ImportFromUrlResponse(
        application=Application(**app_dict),
        extraction=info,
        kb_ingested=kb_ingested,
    )


@router.post("/applications/from-text", response_model=ImportFromTextResponse, status_code=201)
async def import_from_text(req: ImportFromTextRequest):
    """Import a job posting from pasted text: extract via LLM, create application, ingest into kb."""
    from datetime import date
    from jam.config import Settings

    text = req.text.strip()

    # 1. Validate text length
    if len(text) < 50:
        raise HTTPException(status_code=400, detail="Text is too short or empty")

    # 2. Extract job info via LLM
    settings = Settings()
    try:
        info = await extract_job_info(text, settings)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"LLM extraction failed: {exc}")

    company = info.get("company") or "Unknown"
    position = info.get("position") or "Unknown"

    # 3. Build notes from extracted fields
    notes_parts = []
    if info.get("requirements"):
        notes_parts.append(f"Requirements: {info['requirements']}")
    notes = "\n".join(notes_parts) or None

    # 4. Create the application (url=None since there's no URL)
    now = datetime.now(timezone.utc).isoformat()
    app_id = str(uuid4())
    app_dict = db_create_application(
        id=app_id,
        company=company,
        position=position,
        status=ApplicationStatus.not_applied_yet.value,
        url=None,
        notes=notes,
        salary_range=info.get("salary_range"),
        location=info.get("location"),
        opening_date=info.get("opening_date"),
        closing_date=info.get("closing_date"),
        description=info.get("description"),
        full_text=text,
        applied_date=date.today().isoformat(),
        created_at=now,
        updated_at=now,
    )
    _auto_create_documents(app_id)

    # 5. Ingest into kb (fire-and-forget — don't fail if kb is down)
    # Use ingest_text with an empty source_url since there's no URL
    kb_ingested = False
    try:
        await ingest_text(text, "", settings)
        kb_ingested = True
    except Exception:
        pass

    return ImportFromTextResponse(
        application=Application(**app_dict),
        extraction=info,
        kb_ingested=kb_ingested,
    )


@router.get("/applications/{app_id}", response_model=Application)
async def get_application(app_id: UUID):
    """Get a single application by ID."""
    row = db_get_application(str(app_id))
    if not row:
        raise HTTPException(status_code=404, detail="Application not found")
    return Application(**row)


@router.put("/applications/{app_id}", response_model=Application)
async def update_application(app_id: UUID, req: ApplicationUpdate):
    """Update an application."""
    row = db_get_application(str(app_id))
    if not row:
        raise HTTPException(status_code=404, detail="Application not found")
    fields = req.model_dump(exclude_none=True)
    if fields:
        # Convert status enum to its string value for db storage
        if "status" in fields:
            fields["status"] = fields["status"].value
        if "work_mode" in fields:
            fields["work_mode"] = fields["work_mode"].value
        fields["updated_at"] = datetime.now(timezone.utc).isoformat()
        row = db_update_application(str(app_id), fields)
    return Application(**row)


@router.delete("/applications/{app_id}", status_code=204)
async def delete_application(app_id: UUID):
    """Delete an application."""
    if not db_delete_application(str(app_id)):
        raise HTTPException(status_code=404, detail="Application not found")
    return None


@router.get("/catalog")
async def catalog_endpoint():
    """Return the LLM provider/model catalog."""
    return get_catalog()


@router.get("/kb/namespaces")
async def list_kb_namespaces():
    """Proxy: list all namespaces from the kb knowledge base."""
    from jam.config import Settings
    settings = Settings()
    base_url = settings.kb_api_url.rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{base_url}/namespaces")
            resp.raise_for_status()
            return resp.json()
    except Exception:
        return []


@router.post("/kb/test-retrieval")
async def test_kb_retrieval(body: dict):
    """Test KB document retrieval for debugging. Returns detailed error info."""
    from jam.kb_client import list_namespace_documents, search_documents
    from jam.config import Settings
    from collections import defaultdict

    settings = Settings()
    namespace_ids = body.get("namespace_ids", [])
    query = body.get("query", "test")

    result: dict = {
        "kb_api_url": settings.kb_api_url,
        "namespace_ids": namespace_ids,
        "query": query,
        "search_results": None,
        "search_error": None,
        "list_results": None,
        "list_error": None,
        "namespace_summaries": None,
    }

    # Test semantic search
    try:
        search_results = await search_documents(
            query, n_results=5, namespace_ids=namespace_ids if namespace_ids else None, settings=settings
        )
        result["search_results"] = search_results
    except Exception as e:
        result["search_error"] = str(e)

    # Test list_namespace_documents per namespace
    if namespace_ids:
        summaries: list[dict] = []
        for ns_id in namespace_ids:
            summary: dict = {"namespace_id": ns_id, "documents": [], "error": None}
            try:
                chunks = await list_namespace_documents([ns_id], settings=settings)
                by_doc: dict[str, dict] = {}
                for chunk in chunks:
                    doc_id = chunk.get("doc_id") or chunk.get("id", "")
                    if doc_id not in by_doc:
                        file_name = chunk.get("metadata", {}).get("file_name", doc_id)
                        by_doc[doc_id] = {"doc_id": doc_id, "file_name": file_name, "chunks": 0}
                    by_doc[doc_id]["chunks"] += 1
                summary["documents"] = list(by_doc.values())
            except Exception as e:
                summary["error"] = str(e)
            summaries.append(summary)
        result["namespace_summaries"] = summaries

    return result


@router.get("/settings")
async def get_settings_endpoint():
    """Return current settings (keys masked)."""
    stored = get_all_settings()
    response: dict = {
        "openai_api_key_set": bool(stored.get("openai_api_key")),
        "anthropic_api_key_set": bool(stored.get("anthropic_api_key")),
        "groq_api_key_set": bool(stored.get("groq_api_key")),
        "cliproxy_api_key_set": bool(stored.get("cliproxy_api_key")),
        "gmail_client_secret_set": bool(stored.get("gmail_client_secret", "")),
        "gmail_refresh_token_set": bool(stored.get("gmail_refresh_token", "")),
    }
    _BOOL_PLAIN_KEYS = {"search_enrichment_enabled"}
    for key in _PLAIN_KEYS:
        raw = stored.get(key)
        if raw is None:
            continue
        if key in _BOOL_PLAIN_KEYS:
            response[key] = raw.lower() in {"1", "true", "yes", "on"}
        elif raw:
            response[key] = raw
    return response


@router.post("/settings")
async def save_settings_endpoint(req: SettingsRequest):
    """Persist settings to the database."""
    updates = req.model_dump(exclude_none=True, by_alias=True)
    for tpl_key in ("cv_latex_template", "cover_letter_latex_template"):
        if tpl_key in updates and updates[tpl_key] == "":
            del updates[tpl_key]
    if not updates:
        raise HTTPException(status_code=422, detail="No settings provided")
    # Validate model belongs to selected provider
    if "llm_provider" in updates and "llm_model" in updates:
        catalog = get_catalog()
        provider = next(
            (p for p in catalog["providers"] if p["id"] == updates["llm_provider"]),
            None,
        )
        if provider:
            valid_models = {m["model_id"] for m in provider.get("llm_models", [])}
            if updates["llm_model"] not in valid_models:
                raise HTTPException(
                    status_code=422,
                    detail=f"Model '{updates['llm_model']}' does not belong to provider '{updates['llm_provider']}'",
                )
    # Validate per-step model overrides against catalog
    _STEP_MODEL_KEYS = [
        "step_model_generate_or_revise", "step_model_analyze_fit",
        "step_model_analyze_quality", "step_model_analyze_compress",
    ]
    step_model_updates = {k: v for k, v in updates.items() if k in _STEP_MODEL_KEYS and v}
    if step_model_updates:
        cat = get_catalog()
        valid_ids = {m["id"] for p in cat["providers"] for m in p.get("llm_models", [])}
        for key, val in step_model_updates.items():
            if val not in valid_ids:
                raise HTTPException(
                    status_code=422,
                    detail=f"Unknown model '{val}' for {key}",
                )
    # Normalise bools to "1"/"0" strings for DB storage (env-var parser expects these)
    _BOOL_KEYS = {"search_enrichment_enabled"}
    for bk in _BOOL_KEYS:
        if bk in updates:
            updates[bk] = "1" if updates[bk] else "0"
    set_settings_batch(updates)
    for key, value in updates.items():
        if key in _ENV_MAP:
            os.environ[_ENV_MAP[key]] = value
    return {"ok": True, "saved": list(updates.keys())}


@router.get("/templates/defaults")
async def get_default_templates():
    """Return the built-in default LaTeX templates."""
    return {
        "cv": DEFAULT_CV_TEMPLATE,
        "cover_letter": DEFAULT_COVER_LETTER_TEMPLATE,
    }


@router.get("/prompts/defaults")
async def get_default_prompts():
    """Return the built-in default system prompts (shared + doc-type-specific)."""
    from jam.generation import get_all_prompt_defaults
    return get_all_prompt_defaults()


# ── Gmail endpoints ────────────────────────────────────────────────────────────

@router.get("/gmail/auth-url")
async def gmail_auth_url():
    """Return OAuth authorization URL. 400 if client_id or client_secret not set."""
    from jam.config import Settings
    from jam.gmail_client import get_auth_url
    
    settings = Settings()
    try:
        url = get_auth_url(settings=settings)
        return {"url": url}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))




@router.get("/gmail/status")
async def gmail_status():
    """Return connection status, reading directly from DB so it survives restarts."""
    stored = get_all_settings()
    connected = bool(stored.get("gmail_refresh_token"))
    return {"connected": connected, "email": stored.get("gmail_user_email") if connected else None}


@router.post("/gmail/disconnect")
async def gmail_disconnect():
    """Clear stored Gmail tokens."""
    from jam.db import delete_setting

    delete_setting("gmail_refresh_token")
    delete_setting("gmail_user_email")
    os.environ.pop("GMAIL_REFRESH_TOKEN", None)
    os.environ.pop("GMAIL_USER_EMAIL", None)
    return {"ok": True}


# ── MS Graph helpers ──────────────────────────────────────────────────────────

_log = logging.getLogger(__name__)


async def _sync_round_to_graph(round_id: str, settings=None) -> None:
    """Push one interview round to Outlook Calendar. Idempotent.

    - Loads the round and parent application from the DB.
    - If status != 'scheduled' OR scheduled_at is empty:
        If graph_event_id is set: delete it from Graph, clear graph_event_id.
        Otherwise: no-op.
    - Else: upsert_event(...) and store the returned id in graph_event_id.
    - Skips entirely (no exception) if ms_graph_refresh_token is empty.
    - Swallows ALL exceptions and logs them via logging.
      NEVER raises -- this runs in a BackgroundTask and must not crash the worker.
    """
    try:
        from jam.config import Settings as _Settings
        settings = settings or _Settings()
        if not settings.ms_graph_refresh_token:
            return

        loop = asyncio.get_event_loop()
        round_row = await loop.run_in_executor(None, lambda: db_get_interview_round(round_id))
        if round_row is None:
            return

        app_row = await loop.run_in_executor(
            None, lambda: db_get_application(round_row["application_id"])
        )

        is_scheduled = (
            round_row.get("status") == "scheduled"
            and bool(round_row.get("scheduled_at"))
        )

        if not is_scheduled:
            existing_event_id = round_row.get("graph_event_id")
            if existing_event_id:
                await msgraph_client.delete_event(existing_event_id, settings)
                await loop.run_in_executor(
                    None,
                    lambda: db_update_interview_round(round_id, {"graph_event_id": None}),
                )
            return

        event_id = await msgraph_client.upsert_event(round_row, app_row, settings)
        await loop.run_in_executor(
            None,
            lambda: db_update_interview_round(round_id, {"graph_event_id": event_id}),
        )
    except Exception as exc:
        _log.warning("_sync_round_to_graph(%s) failed: %s", round_id, exc)


async def _delete_graph_event_by_id(graph_event_id: str, settings=None) -> None:
    """Delete a Graph calendar event by id. Swallows all exceptions."""
    try:
        from jam.config import Settings as _Settings
        settings = settings or _Settings()
        if not settings.ms_graph_refresh_token:
            return
        await msgraph_client.delete_event(graph_event_id, settings)
    except Exception as exc:
        _log.warning("_delete_graph_event_by_id(%s) failed: %s", graph_event_id, exc)


# ── MS Graph endpoints ────────────────────────────────────────────────────────

@router.get("/ms_graph/auth-url")
async def ms_graph_auth_url():
    """Return MS Graph OAuth authorization URL."""
    from jam.config import Settings
    settings = Settings()
    url = msgraph_client.get_auth_url(settings)
    return {"url": url}


@router.get("/ms_graph/status", response_model=MSGraphSettingsResponse)
async def ms_graph_status():
    """Return MS Graph connection status."""
    stored = get_all_settings()
    connected = bool(stored.get("ms_graph_refresh_token"))
    user_email = stored.get("ms_graph_user_email", "") if connected else ""
    return MSGraphSettingsResponse(connected=connected, user_email=user_email or "")


@router.post("/ms_graph/disconnect")
async def ms_graph_disconnect():
    """Clear stored MS Graph tokens and wipe graph_event_id from all rounds."""
    delete_setting("ms_graph_refresh_token")
    delete_setting("ms_graph_access_token")
    delete_setting("ms_graph_token_expires_at")
    delete_setting("ms_graph_user_email")
    os.environ.pop("MS_GRAPH_REFRESH_TOKEN", None)
    os.environ.pop("MS_GRAPH_ACCESS_TOKEN", None)
    os.environ.pop("MS_GRAPH_TOKEN_EXPIRES_AT", None)
    os.environ.pop("MS_GRAPH_USER_EMAIL", None)

    rounds_cleared = 0
    apps = db_list_applications()
    for app_row in apps:
        rounds = db_list_interview_rounds(app_row["id"])
        for r in rounds:
            if r.get("graph_event_id"):
                db_update_interview_round(r["id"], {"graph_event_id": None})
                rounds_cleared += 1

    return {"disconnected": True, "rounds_cleared": rounds_cleared}


@router.post("/ms_graph/sync")
async def ms_graph_sync():
    """Push all scheduled interview rounds to Outlook Calendar."""
    synced = 0
    errors = 0
    apps = db_list_applications()
    for app_row in apps:
        rounds = db_list_interview_rounds(app_row["id"])
        for r in rounds:
            if r.get("status") != "scheduled" or not r.get("scheduled_at"):
                continue
            try:
                await _sync_round_to_graph(r["id"])
                synced += 1
            except Exception as exc:
                _log.warning("ms_graph_sync round %s failed: %s", r["id"], exc)
                errors += 1

    return {"synced": synced, "errors": errors}


# ── Document endpoints ────────────────────────────────────────────────────────

@router.get(
    "/applications/{app_id}/documents",
    response_model=list[DocumentResponse],
)
async def list_documents_endpoint(
    app_id: UUID,
    doc_type: Optional[DocType] = Query(None),
):
    """List documents for an application, optionally filtered by type."""
    row = db_get_application(str(app_id))
    if not row:
        raise HTTPException(status_code=404, detail="Application not found")
    dt = doc_type.value if doc_type else None
    rows = db_list_documents(str(app_id), doc_type=dt)
    return [DocumentResponse(**r) for r in rows]


@router.post(
    "/applications/{app_id}/documents",
    response_model=DocumentResponse,
    status_code=201,
)
async def create_document_endpoint(app_id: UUID, req: DocumentCreate):
    """Create a new document for an application."""
    row = db_get_application(str(app_id))
    if not row:
        raise HTTPException(status_code=404, detail="Application not found")
    doc = db_create_document(
        application_id=str(app_id),
        doc_type=req.doc_type.value,
        title=req.title,
        latex_source=req.latex_source,
        prompt_text=req.prompt_text,
    )
    return DocumentResponse(**doc)


@router.get("/documents/{doc_id}", response_model=DocumentResponse)
async def get_document_endpoint(doc_id: str):
    """Get a single document."""
    doc = db_get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentResponse(**doc)


@router.put("/documents/{doc_id}", response_model=DocumentResponse)
async def update_document_endpoint(doc_id: str, req: DocumentUpdate):
    """Update a document."""
    doc = db_get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    fields = req.model_dump(exclude_none=True)
    updated = db_update_document(doc_id, fields)
    return DocumentResponse(**updated)


@router.delete("/documents/{doc_id}", status_code=204)
async def delete_document_endpoint(doc_id: str):
    """Delete a document."""
    if not db_delete_document(doc_id):
        raise HTTPException(status_code=404, detail="Document not found")
    return None


# ── Extra questions ──────────────────────────────────────────────────────────

@router.get(
    "/applications/{app_id}/questions",
    response_model=list[ExtraQuestionResponse],
)
async def list_questions(app_id: str):
    """List all extra questions for an application."""
    if not db_get_application(app_id):
        raise HTTPException(status_code=404, detail="Application not found")
    rows = db_list_extra_questions(app_id)
    return [ExtraQuestionResponse(**r) for r in rows]


@router.post(
    "/applications/{app_id}/questions",
    response_model=ExtraQuestionResponse,
    status_code=201,
)
async def create_question(app_id: str, req: ExtraQuestionCreate):
    """Create a new extra question for an application."""
    if not db_get_application(app_id):
        raise HTTPException(status_code=404, detail="Application not found")
    row = db_create_extra_question(
        application_id=app_id,
        question=req.question,
        answer=req.answer,
        word_cap=req.word_cap,
        sort_order=req.sort_order,
    )
    return ExtraQuestionResponse(**row)


@router.put("/questions/{question_id}", response_model=ExtraQuestionResponse)
async def update_question(question_id: str, req: ExtraQuestionUpdate):
    """Update an extra question."""
    if not db_get_extra_question(question_id):
        raise HTTPException(status_code=404, detail="Question not found")
    fields = req.model_dump(exclude_none=True)
    row = db_update_extra_question(question_id, fields)
    return ExtraQuestionResponse(**row)


@router.delete("/questions/{question_id}", status_code=204)
async def delete_question(question_id: str):
    """Delete an extra question."""
    if not db_delete_extra_question(question_id):
        raise HTTPException(status_code=404, detail="Question not found")
    return None


# ── Interview rounds ────────────────────────────────────────────────────────

@router.get(
    "/applications/{app_id}/interviews",
    response_model=list[InterviewRoundResponse],
)
async def list_interviews(app_id: str):
    """List all interview rounds for an application."""
    if not db_get_application(app_id):
        raise HTTPException(status_code=404, detail="Application not found")
    rows = db_list_interview_rounds(app_id)
    return [InterviewRoundResponse(**r) for r in rows]


@router.post(
    "/applications/{app_id}/interviews",
    response_model=InterviewRoundResponse,
    status_code=201,
)
async def create_interview(
    app_id: str, req: InterviewRoundCreate, background_tasks: BackgroundTasks
):
    """Create a new interview round for an application."""
    if not db_get_application(app_id):
        raise HTTPException(status_code=404, detail="Application not found")
    row = db_create_interview_round(
        application_id=app_id,
        round_type=req.round_type,
        round_number=req.round_number,
        scheduled_at=req.scheduled_at,
        completed_at=req.completed_at,
        interviewer_names=req.interviewer_names,
        location=req.location,
        links=req.links,
        status=req.status,
        prep_notes=req.prep_notes,
        debrief_notes=req.debrief_notes,
        questions_asked=req.questions_asked,
        went_well=req.went_well,
        to_improve=req.to_improve,
        confidence=req.confidence,
        sort_order=req.sort_order,
        scheduled_time=req.scheduled_time or "",
    )
    background_tasks.add_task(_sync_round_to_graph, row["id"])
    return InterviewRoundResponse(**row)


@router.put("/interviews/{interview_id}", response_model=InterviewRoundResponse)
async def update_interview(
    interview_id: str, req: InterviewRoundUpdate, background_tasks: BackgroundTasks
):
    """Update an interview round."""
    if not db_get_interview_round(interview_id):
        raise HTTPException(status_code=404, detail="Interview round not found")
    fields = req.model_dump(exclude_none=True)
    row = db_update_interview_round(interview_id, fields)
    background_tasks.add_task(_sync_round_to_graph, interview_id)
    return InterviewRoundResponse(**row)


@router.delete("/interviews/{interview_id}", status_code=204)
async def delete_interview(
    interview_id: str, background_tasks: BackgroundTasks
):
    """Delete an interview round."""
    existing = db_get_interview_round(interview_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Interview round not found")
    graph_event_id = existing.get("graph_event_id")
    if not db_delete_interview_round(interview_id):
        raise HTTPException(status_code=404, detail="Interview round not found")
    if graph_event_id:
        background_tasks.add_task(_delete_graph_event_by_id, graph_event_id)
    return None


# ── Interview prep guides ────────────────────────────────────────────────────

@router.get(
    "/interviews/{interview_id}/prep-guide",
    response_model=PrepGuideResponse,
)
async def get_prep_guide(interview_id: str):
    """Return the prep guide for an interview round.

    Returns a PrepGuideResponse with all-default/None fields if no guide exists
    yet (no 404 — the UI always fetches and treats an empty guide as normal).
    404 only if the interview round itself does not exist.
    """
    if not db_get_interview_round(interview_id):
        raise HTTPException(status_code=404, detail="Interview round not found")
    row = db_get_prep_guide(interview_id)
    if row is None:
        return PrepGuideResponse()
    return PrepGuideResponse(
        markdown=row.get("markdown_source") or "",
        generation_system_prompt=row.get("generation_system_prompt"),
        generation_user_prompt=row.get("generation_user_prompt"),
        web_search_log=row.get("web_search_log"),
        thinking_summary=row.get("thinking_summary"),
        last_generated_at=row.get("last_generated_at"),
        updated_at=row.get("updated_at"),
        created_at=row.get("created_at"),
    )


@router.put(
    "/interviews/{interview_id}/prep-guide",
    response_model=PrepGuideResponse,
)
async def put_prep_guide(interview_id: str, body: PrepGuideUpdateRequest):
    """Upsert the markdown for an interview prep guide.

    Only updates markdown_source; leaves generation_*, web_search_log,
    thinking_summary untouched on an existing row.
    404 if the interview round does not exist.
    """
    if not db_get_interview_round(interview_id):
        raise HTTPException(status_code=404, detail="Interview round not found")
    row = db_upsert_prep_guide(interview_id, markdown_source=body.markdown)
    return PrepGuideResponse(
        markdown=row.get("markdown_source") or "",
        generation_system_prompt=row.get("generation_system_prompt"),
        generation_user_prompt=row.get("generation_user_prompt"),
        web_search_log=row.get("web_search_log"),
        thinking_summary=row.get("thinking_summary"),
        last_generated_at=row.get("last_generated_at"),
        updated_at=row.get("updated_at"),
        created_at=row.get("created_at"),
    )


@router.post("/interviews/{interview_id}/prep-guide/generate")
async def generate_prep_guide(interview_id: str):
    """Stream prep guide generation progress via Server-Sent Events.

    Each ``data:`` line is a JSON object with a ``node`` field.
    The final event has ``node: "done"`` and carries ``markdown``,
    ``generation_system_prompt``, ``generation_user_prompt``,
    ``web_search_log``, ``thinking_summary``, and an optional ``error``.
    """
    from jam.config import Settings

    settings = Settings()

    interview = db_get_interview_round(interview_id)
    if not interview:
        raise HTTPException(status_code=404, detail="Interview round not found")

    application = db_get_application(interview["application_id"])
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    if settings.llm_provider not in ("anthropic", "cliproxy"):
        raise HTTPException(
            status_code=400,
            detail="Prep guide generation requires anthropic or cliproxy provider",
        )

    # Load CV + cover letter LaTeX if they exist
    docs = db_list_documents(interview["application_id"])
    cv_doc = next((d for d in docs if d.get("doc_type") == "cv"), None)
    cl_doc = next((d for d in docs if d.get("doc_type") == "cover_letter"), None)

    initial_state = {
        "interview_id": interview["id"],
        "application_id": application["id"],
        "job_description": application.get("description") or application.get("full_text") or "",
        "company": application["company"],
        "position": application["position"],
        "round_type": interview.get("round_type", ""),
        "round_number": interview.get("round_number", 1),
        "interviewer_names": interview.get("interviewer_names", ""),
        "interview_links": interview.get("links", ""),
        "interview_prep_notes": interview.get("prep_notes", ""),
        "scheduled_at": interview.get("scheduled_at", ""),
        "cv_latex": cv_doc["latex_source"] if cv_doc else "",
        "cover_letter_latex": cl_doc["latex_source"] if cl_doc else "",
        "progress_events": [],
    }

    async def sse_gen():
        try:
            async for event in run_prep_guide_graph(initial_state, settings):
                yield f"data: {_json.dumps(event)}\n\n"
                if event.get("node") == "done":
                    # Persist the result
                    if not event.get("error"):
                        loop = asyncio.get_event_loop()
                        await loop.run_in_executor(
                            None,
                            lambda: db_upsert_prep_guide(
                                interview_id,
                                markdown_source=event.get("markdown", ""),
                                generation_system_prompt=event.get("generation_system_prompt"),
                                generation_user_prompt=event.get("generation_user_prompt"),
                                web_search_log=event.get("web_search_log"),
                                thinking_summary=event.get("thinking_summary"),
                                last_generated_at=datetime.now(timezone.utc).isoformat(),
                            ),
                        )
        except Exception as exc:
            yield f"data: {_json.dumps({'node': 'error', 'status': 'error', 'detail': str(exc)})}\n\n"

    return StreamingResponse(
        sse_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ── Offers ──────────────────────────────────────────────────────────────────

@router.get(
    "/applications/{app_id}/offers",
    response_model=list[OfferResponse],
)
async def list_offers_endpoint(app_id: str):
    """List all offers for an application."""
    if not db_get_application(app_id):
        raise HTTPException(status_code=404, detail="Application not found")
    rows = db_list_offers(app_id)
    return [OfferResponse(**r) for r in rows]


@router.post(
    "/applications/{app_id}/offers",
    response_model=OfferResponse,
    status_code=201,
)
async def create_offer_endpoint(app_id: str, req: OfferCreate):
    """Create a new offer for an application."""
    if not db_get_application(app_id):
        raise HTTPException(status_code=404, detail="Application not found")
    row = db_create_offer(
        application_id=app_id,
        status=req.status,
        base_salary=req.base_salary,
        currency=req.currency,
        bonus=req.bonus,
        equity=req.equity,
        signing_bonus=req.signing_bonus,
        benefits=req.benefits,
        pto_days=req.pto_days,
        remote_policy=req.remote_policy,
        start_date=req.start_date,
        expiry_date=req.expiry_date,
        notes=req.notes,
        sort_order=req.sort_order,
    )
    return OfferResponse(**row)


@router.put("/offers/{offer_id}", response_model=OfferResponse)
async def update_offer_endpoint(offer_id: str, req: OfferUpdate):
    """Update an offer."""
    if not db_get_offer(offer_id):
        raise HTTPException(status_code=404, detail="Offer not found")
    fields = req.model_dump(exclude_none=True)
    row = db_update_offer(offer_id, fields)
    return OfferResponse(**row)


@router.delete("/offers/{offer_id}", status_code=204)
async def delete_offer_endpoint(offer_id: str):
    """Delete an offer."""
    if not db_delete_offer(offer_id):
        raise HTTPException(status_code=404, detail="Offer not found")
    return None


# ── Email ingest ────────────────────────────────────────────────────────────

@router.post(
    "/applications/{app_id}/email/ingest",
    response_model=EmailIngestResponse,
    status_code=201,
)
async def ingest_email(app_id: str, req: EmailIngestRequest):
    """Classify a pasted email as interview invite or rejection and auto-create the record."""
    from jam.config import Settings

    if not db_get_application(app_id):
        raise HTTPException(status_code=404, detail="Application not found")

    text = req.email_text.strip()
    if not text:
        raise HTTPException(status_code=422, detail="email_text is empty after stripping")

    settings = Settings()
    try:
        info = await extract_email_info(text, settings)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"LLM extraction failed: {exc}")

    kind = info.get("kind", "unknown")

    if kind == "interview_invite":
        iv = info.get("interview") or {}
        non_null_fields: dict = {}
        for field in ("round_type", "scheduled_at", "scheduled_time", "interviewer_names", "location", "prep_notes"):
            val = iv.get(field)
            if val is not None:
                non_null_fields[field] = val
        links_list = iv.get("links") or []
        links = "\n".join(links_list)
        row = db_create_interview_round(
            application_id=app_id,
            status="scheduled",
            links=links,
            **non_null_fields,
        )
        return EmailIngestResponse(
            kind=kind,
            confidence=info.get("confidence", ""),
            interview=InterviewRoundResponse(**row),
            rejection=None,
            extraction=info,
        )

    elif kind == "rejection":
        rej = info.get("rejection") or {}
        summary = rej.get("summary") or ""
        reasons = rej.get("reasons") or ""
        links_list = rej.get("links") or []
        links = "\n".join(links_list)
        received_at = info.get("received_at")
        row = db_create_rejection(
            application_id=app_id,
            summary=summary,
            reasons=reasons,
            links=links,
            raw_email=text,
            received_at=received_at,
        )
        db_update_application(app_id, {
            "status": "rejected",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
        return EmailIngestResponse(
            kind=kind,
            confidence=info.get("confidence", ""),
            interview=None,
            rejection=RejectionResponse(**row),
            extraction=info,
        )

    else:
        raise HTTPException(
            status_code=422,
            detail={"message": "Could not classify email as interview or rejection", "extraction": info},
        )


# ── Rejections ──────────────────────────────────────────────────────────────

@router.get(
    "/applications/{app_id}/rejections",
    response_model=list[RejectionResponse],
)
async def list_rejections_endpoint(app_id: str):
    """List all rejections for an application."""
    if not db_get_application(app_id):
        raise HTTPException(status_code=404, detail="Application not found")
    rows = db_list_rejections(app_id)
    return [RejectionResponse(**r) for r in rows]


@router.post(
    "/applications/{app_id}/rejections",
    response_model=RejectionResponse,
    status_code=201,
)
async def create_rejection_endpoint(app_id: str, req: RejectionCreate):
    """Create a new rejection for an application."""
    if not db_get_application(app_id):
        raise HTTPException(status_code=404, detail="Application not found")
    row = db_create_rejection(
        application_id=app_id,
        summary=req.summary,
        reasons=req.reasons,
        links=req.links,
        raw_email=req.raw_email,
        received_at=req.received_at,
        followup_status=req.followup_status,
        followup_notes=req.followup_notes,
    )
    return RejectionResponse(**row)


@router.put("/rejections/{rejection_id}", response_model=RejectionResponse)
async def update_rejection_endpoint(rejection_id: str, req: RejectionUpdate):
    """Update a rejection."""
    if not db_get_rejection(rejection_id):
        raise HTTPException(status_code=404, detail="Rejection not found")
    fields = req.model_dump(exclude_none=True)
    row = db_update_rejection(rejection_id, fields)
    return RejectionResponse(**row)


@router.delete("/rejections/{rejection_id}", status_code=204)
async def delete_rejection_endpoint(rejection_id: str):
    """Delete a rejection."""
    if not db_delete_rejection(rejection_id):
        raise HTTPException(status_code=404, detail="Rejection not found")
    return None


def _parse_tectonic_error(raw_stderr: str) -> str:
    """Extract the most useful error line from tectonic stderr output."""
    lines = raw_stderr.splitlines()
    error_lines = [l for l in lines if l.startswith("error:")]
    if error_lines:
        # Return first error line (most relevant) + truncated raw for context
        summary = error_lines[0]
        if len(raw_stderr) > 500:
            return f"{summary}\n\n(full output truncated)\n{raw_stderr[:500]}"
        return f"{summary}\n\n{raw_stderr}"
    # No structured error found — return truncated raw output
    return raw_stderr[:2000]


def _write_settings_images(tmpdir: str, stored: dict) -> None:
    """Decode personal_photo / personal_signature data-URIs and write to tmpdir."""
    import base64
    for key, filename in [("personal_photo", "photo"), ("personal_signature", "signature")]:
        data_uri = stored.get(key, "")
        if not data_uri.startswith("data:"):
            continue
        try:
            header, b64 = data_uri.split(",", 1)
            # header like "data:image/png;base64"
            mime = header.split(":")[1].split(";")[0]  # "image/png"
            ext = mime.split("/")[1]  # "png"
            img_bytes = base64.b64decode(b64)
            with open(os.path.join(tmpdir, f"{filename}.{ext}"), "wb") as fh:
                fh.write(img_bytes)
        except Exception:
            pass  # skip malformed data URIs


async def _compile_latex(latex_source: str) -> bytes:
    """Compile LaTeX source to PDF bytes via tectonic.

    Raises HTTPException on failure.
    """
    if not latex_source.strip():
        raise HTTPException(status_code=422, detail="LaTeX source is empty")

    if not shutil.which("tectonic"):
        raise HTTPException(
            status_code=503,
            detail="tectonic is not installed on the server",
        )

    with tempfile.TemporaryDirectory() as tmpdir:
        tex_path = os.path.join(tmpdir, "document.tex")
        pdf_path = os.path.join(tmpdir, "document.pdf")
        with open(tex_path, "w") as f:
            f.write(latex_source)

        stored = get_all_settings()
        _write_settings_images(tmpdir, stored)

        proc = await asyncio.create_subprocess_exec(
            "tectonic", tex_path, "--untrusted",
            cwd=tmpdir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            error_msg = _parse_tectonic_error(
                stderr.decode(errors="replace") or stdout.decode(errors="replace")
            )
            raise HTTPException(
                status_code=422,
                detail=f"LaTeX compilation failed: {error_msg}",
            )

        if not os.path.exists(pdf_path):
            raise HTTPException(status_code=500, detail="PDF was not generated")

        with open(pdf_path, "rb") as f:
            return f.read()


def _inject_pdf_metadata(pdf_bytes: bytes, title: str = "", author: str = "") -> bytes:
    """Inject title and author metadata into PDF bytes using pymupdf."""
    import fitz
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    md = doc.metadata or {}
    md.update({"title": title, "author": author})
    doc.set_metadata(md)
    result = doc.tobytes()
    doc.close()
    return result


def _build_pdf_metadata(position: str = "") -> dict:
    """Build PDF metadata dict from application context and personal settings."""
    stored = get_all_settings()
    return {
        "title": position or "",
        "author": stored.get("personal_full_name", ""),
    }


@router.post("/documents/{doc_id}/compile")
async def compile_document_endpoint(doc_id: str):
    """Compile a document's LaTeX source to PDF via tectonic."""
    doc = db_get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    pdf_bytes = await _compile_latex(doc["latex_source"])

    db_create_version(
        document_id=doc_id,
        latex_source=doc["latex_source"],
        prompt_text=doc.get("prompt_text", ""),
    )

    app_row = db_get_application(doc["application_id"])
    position = app_row.get("position", "") if app_row else ""
    meta = _build_pdf_metadata(position=position)
    pdf_bytes = _inject_pdf_metadata(pdf_bytes, **meta)

    # Store in cache for GET endpoint
    _pdf_cache[doc_id] = pdf_bytes

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename=document-{doc_id[:8]}.pdf"},
    )



@router.head("/documents/{doc_id}/pdf")
@router.get("/documents/{doc_id}/pdf")
async def get_document_pdf(doc_id: str):
    """Return the most recently compiled PDF for a document."""
    pdf_bytes = _pdf_cache.get(doc_id)
    if pdf_bytes is None:
        raise HTTPException(status_code=404, detail="No compiled PDF available — compile first")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename=document-{doc_id[:8]}.pdf"},
    )

@router.get(
    "/documents/{doc_id}/versions",
    response_model=list[DocumentVersionResponse],
)
async def list_versions_endpoint(doc_id: str):
    """List version history for a document."""
    doc = db_get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    rows = db_list_versions(doc_id)
    return [DocumentVersionResponse(**r) for r in rows]


@router.post("/documents/versions/{version_id}/compile")
async def compile_version_endpoint(version_id: str):
    """Re-compile an old version's LaTeX source to PDF."""
    ver = db_get_version(version_id)
    if not ver:
        raise HTTPException(status_code=404, detail="Version not found")

    pdf_bytes = await _compile_latex(ver["latex_source"])

    doc = db_get_document(ver["document_id"])
    app_row = db_get_application(doc["application_id"]) if doc else None
    position = app_row.get("position", "") if app_row else ""
    meta = _build_pdf_metadata(position=position)
    pdf_bytes = _inject_pdf_metadata(pdf_bytes, **meta)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename=version-{version_id[:8]}.pdf"},
    )


class GenerateRequest(BaseModel):
    """Request body for the document generation endpoint."""
    is_first_generation: bool = False
    critique_only: bool = False
    fit_feedback: str | None = None       # User-edited feedback from UI
    quality_feedback: str | None = None   # User-edited feedback from UI


@router.post("/documents/{doc_id}/generate")
async def generate_document_endpoint(doc_id: str, req: GenerateRequest):
    """Stream agentic document generation progress via Server-Sent Events.

    The response is a ``text/event-stream`` where each ``data:`` line is a
    JSON object.  Progress events have ``node`` and ``status`` fields; the
    final event has ``node: "done"`` and carries ``latex``, ``page_count``,
    ``fit_feedback``, ``quality_feedback``, and an optional ``error`` field.
    """
    from jam.generation import generation_graph, critique_graph

    doc = db_get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    app_row = db_get_application(doc["application_id"])
    if not app_row:
        raise HTTPException(status_code=404, detail="Application not found")

    job_description = app_row.get("full_text") or app_row.get("description") or ""
    if not job_description.strip():
        raise HTTPException(
            status_code=422,
            detail="Application has no job description. Import from URL first.",
        )

    initial_state = {
        "doc_id": doc_id,
        "application_id": doc["application_id"],
        "doc_type": doc["doc_type"],
        "latex_template": doc["latex_source"],
        "job_description": job_description,
        "instructions_json": doc.get("prompt_text", ""),
        "is_first_generation": req.is_first_generation,
        "kb_docs": [],
        "inline_comments": [],
        "locked_sections": [],
        "current_latex": doc["latex_source"],
        "fit_feedback": req.fit_feedback if req.fit_feedback is not None else ("" if req.is_first_generation else (doc.get("fit_feedback") or "")),
        "quality_feedback": req.quality_feedback if req.quality_feedback is not None else ("" if req.is_first_generation else (doc.get("quality_feedback") or "")),
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

    graph = critique_graph if req.critique_only else generation_graph

    async def event_stream():
        final_state = None
        sent_count = 0
        try:
            async for chunk in graph.astream(
                initial_state, stream_mode="values"
            ):
                final_state = chunk
                events = chunk.get("progress_events", [])
                for evt in events[sent_count:]:
                    yield f"data: {_json.dumps(evt)}\n\n"
                sent_count = len(events)
        except Exception as exc:
            yield f"data: {_json.dumps({'node': 'error', 'status': 'error', 'detail': str(exc)})}\n\n"
            return

        # Persist final result to DB
        if final_state and final_state.get("final_latex") and not req.critique_only:
            db_update_document(doc_id, {
                "latex_source": final_state["final_latex"],
                "fit_feedback": final_state.get("fit_feedback", ""),
                "quality_feedback": final_state.get("quality_feedback", ""),
                "compress_feedback": final_state.get("compress_feedback", ""),
                "last_page_count": final_state.get("page_count", 0),
            })
            db_create_version(
                document_id=doc_id,
                latex_source=final_state["final_latex"],
                prompt_text=doc.get("prompt_text", ""),
            )
            if final_state.get("final_pdf"):
                meta = _build_pdf_metadata(position=app_row.get("position", ""))
                _pdf_cache[doc_id] = _inject_pdf_metadata(final_state["final_pdf"], **meta)

        if final_state:
            print(f"[generate] final_state keys: {list(final_state.keys())}")
            print(f"[generate] fit_feedback length={len(final_state.get('fit_feedback', ''))}")
            print(f"[generate] quality_feedback length={len(final_state.get('quality_feedback', ''))}")
        result_event = {
            "node": "done",
            "status": "done",
            "latex": final_state.get("final_latex") if final_state else None,
            "page_count": final_state.get("page_count", 0) if final_state else 0,
            "fit_feedback": final_state.get("fit_feedback", "") if final_state else "",
            "quality_feedback": final_state.get("quality_feedback", "") if final_state else "",
            "generation_system_prompt": final_state.get("generation_system_prompt") if final_state else None,
            "generation_user_prompt": final_state.get("generation_user_prompt") if final_state else None,
            "error": final_state.get("error") if final_state else "Unknown error",
        }
        yield f"data: {_json.dumps(result_event)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


app = FastAPI(title="jam API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router, prefix="/api/v1")


@app.get("/", response_class=HTMLResponse)
async def root_index():
    """Serve the main web UI at the site root."""
    return HTMLResponse(content=HTML_PAGE)


@app.get("/gmail/callback", response_class=HTMLResponse)
async def gmail_callback(code: str, state: str | None = None, iss: str | None = None):
    """Exchange OAuth code, store tokens, then close the popup via JS."""
    from jam.config import Settings
    from jam.gmail_client import exchange_code

    settings = Settings()
    try:
        result = exchange_code(code=code, settings=settings)
        set_settings_batch({
            "gmail_refresh_token": result["refresh_token"],
            "gmail_user_email": result["email"],
        })
        os.environ["GMAIL_REFRESH_TOKEN"] = result["refresh_token"]
        os.environ["GMAIL_USER_EMAIL"] = result["email"]
        return HTMLResponse("""<!doctype html>
<html><head><title>Connected</title></head><body>
<p>Gmail connected successfully. This window will close automatically.</p>
<script>window.close();</script>
</body></html>""")
    except Exception as e:
        return HTMLResponse(f"""<!doctype html>
<html><head><title>Error</title></head><body>
<p style="color:red">Connection failed: {e}</p>
<p>Close this window and try again.</p>
</body></html>""", status_code=400)


@app.get("/ms_graph/callback")
async def ms_graph_callback(code: str, state: str | None = None):
    """Exchange MS Graph OAuth code, store tokens, redirect to home."""
    from jam.config import Settings
    settings = Settings()
    result = await msgraph_client.exchange_code(code, settings)
    set_settings_batch({
        "ms_graph_refresh_token": result["refresh_token"],
        "ms_graph_access_token": result["access_token"],
        "ms_graph_token_expires_at": result["expires_at"],
        "ms_graph_user_email": result["user_email"],
    })
    os.environ["MS_GRAPH_REFRESH_TOKEN"] = result["refresh_token"]
    os.environ["MS_GRAPH_ACCESS_TOKEN"] = result["access_token"]
    os.environ["MS_GRAPH_TOKEN_EXPIRES_AT"] = result["expires_at"]
    os.environ["MS_GRAPH_USER_EMAIL"] = result["user_email"]
    return RedirectResponse("/?ms_graph_connected=1")


@app.on_event("startup")
async def startup():
    init_db()
    stored = get_all_settings()
    for db_key, env_var in _ENV_MAP.items():
        if db_key in stored:
            os.environ[env_var] = stored[db_key]


@app.on_event("shutdown")
async def shutdown():
    await close_client()
