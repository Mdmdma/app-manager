from __future__ import annotations

import asyncio
import os
import shutil
import tempfile
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

import httpx
from fastapi import FastAPI, APIRouter, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel, Field

from jam.html_page import HTML_PAGE
from jam.db import (
    init_db, get_all_settings, set_setting, set_settings_batch, get_catalog,
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
)
from jam.llm import extract_job_info
from jam.kb_client import ingest_url, ingest_text

_ENV_MAP = {
    "openai_api_key":    "OPENAI_API_KEY",
    "anthropic_api_key": "ANTHROPIC_API_KEY",
    "groq_api_key":      "GROQ_API_KEY",
    "ollama_base_url":   "OLLAMA_BASE_URL",
    "llm_provider":      "LLM_PROVIDER",
    "llm_model":         "LLM_MODEL",
}

_PLAIN_KEYS = {"llm_provider", "llm_model", "ollama_base_url", "cv_latex_template", "cover_letter_latex_template"}

DEFAULT_CV_TEMPLATE = r"""\documentclass[10pt,a4paper]{article}

\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage[top=1.2cm, bottom=1.2cm, left=1.4cm, right=1.4cm]{geometry}
\usepackage{enumitem}
\usepackage{titlesec}
\usepackage{hyperref}
\usepackage{xcolor}

\definecolor{accent}{HTML}{1D4ED8}
\hypersetup{colorlinks=true, urlcolor=accent}
\pagestyle{empty}
\setlength{\parindent}{0pt}

\titleformat{\section}{\large\bfseries\color{accent}}{}{0em}{}%
  [{\color{accent}\vspace{1pt}\hrule height 0.6pt}]
\titlespacing{\section}{0pt}{8pt}{4pt}

\begin{document}

% ── Header ────────────────────────────────────────────────────────────────────
{\centering
  {\Huge\bfseries <<FULL-NAME: Jane Doe>>}\\[4pt]
  {\large\color{gray} <<TARGET-ROLE: Senior Software Engineer>>}\\[5pt]
  \small
  \href{mailto:<<EMAIL: jane.doe@example.com>>}{<<EMAIL: jane.doe@example.com>>}
  \enspace$\cdot$\enspace
  <<PHONE: +49 170 123 4567>>
  \enspace$\cdot$\enspace
  <<CITY-COUNTRY: Berlin, Germany>>
  \enspace$\cdot$\enspace
  \href{https://linkedin.com/in/<<LINKEDIN-SLUG: jane-doe-123>>}{LinkedIn}
  \enspace$\cdot$\enspace
  \href{https://github.com/<<GITHUB-USER: janedoe>>}{GitHub}
\par}
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


class SettingsRequest(BaseModel):
    """Request body for saving settings."""
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None
    ollama_base_url: Optional[str] = None
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    cv_latex_template: Optional[str] = None
    cover_letter_latex_template: Optional[str] = None


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
    """Health check — reports jam status and kb reachability."""
    from jam.config import Settings

    settings = Settings()
    kb_status = "unreachable"
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            resp = await client.get(f"{settings.kb_api_url.rstrip('/')}/health")
            if resp.status_code == 200:
                kb_status = "ok"
    except Exception:
        pass
    return {"status": "ok", "kb_status": kb_status}


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


@router.get("/settings")
async def get_settings_endpoint():
    """Return current settings (keys masked)."""
    stored = get_all_settings()
    response: dict = {
        "openai_api_key_set": bool(stored.get("openai_api_key")),
        "anthropic_api_key_set": bool(stored.get("anthropic_api_key")),
        "groq_api_key_set": bool(stored.get("groq_api_key")),
    }
    for key in _PLAIN_KEYS:
        if stored.get(key):
            response[key] = stored[key]
    return response


@router.post("/settings")
async def save_settings_endpoint(req: SettingsRequest):
    """Persist settings to the database."""
    updates = req.model_dump(exclude_none=True)
    for tpl_key in ("cv_latex_template", "cover_letter_latex_template"):
        if tpl_key in updates and updates[tpl_key] == "":
            del updates[tpl_key]
    if not updates:
        raise HTTPException(status_code=422, detail="No settings provided")
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

    # Store in cache for GET endpoint
    _pdf_cache[doc_id] = pdf_bytes

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename=document-{doc_id[:8]}.pdf"},
    )



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

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename=version-{version_id[:8]}.pdf"},
    )


app = FastAPI(title="jam API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router, prefix="/api/v1")


@app.on_event("startup")
async def startup():
    init_db()
    stored = get_all_settings()
    for db_key, env_var in _ENV_MAP.items():
        if db_key in stored:
            os.environ[env_var] = stored[db_key]
