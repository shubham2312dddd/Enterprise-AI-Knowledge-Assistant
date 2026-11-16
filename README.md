# Enterprise AI Knowledge Assistant

An application for indexing PDF documents and answering questions with
retrieved passages. The React frontend communicates with a FastAPI backend.
PDF text is extracted and stored as searchable chunks in ChromaDB; local
Ollama models provide embeddings and grounded answer generation.

**GitHub repository:** [shubham2312dddd/Enterprise-AI-Knowledge-Assistant](https://github.com/shubham2312dddd/Enterprise-AI-Knowledge-Assistant)

## Contents

- [Problem Statement and Objectives](#problem-statement-and-objectives)
- [Features](#features)
- [Architecture and Request Flow](#architecture-and-request-flow)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Ollama Setup](#ollama-setup)
- [Environment Variables](#environment-variables)
- [Local Development](#local-development)
- [Main Application Docker Compose](#main-application-docker-compose)
- [Application URLs](#application-urls)
- [API Endpoint Summary](#api-endpoint-summary)
- [Tests and Frontend Checks](#tests-and-frontend-checks)
- [Separate Monitoring Compose Project](#separate-monitoring-compose-project)
- [Importing the Grafana Dashboard](#importing-the-grafana-dashboard)
- [Kubernetes and CI/CD Status](#kubernetes-and-cicd-status)
- [Known Limitations and Troubleshooting](#known-limitations-and-troubleshooting)

## Problem Statement and Objectives

Important knowledge is often spread across long documents, making it slow to
find a relevant passage and verify its source. This project provides a local
document workflow that:

- Accepts PDF uploads and extracts selectable text.
- Indexes page-aware text chunks for semantic retrieval.
- Supports searching all indexed documents or a selected subset.
- Generates answers from retrieved passages and returns source references.
- Keeps embeddings, vector storage, and language-model inference on services
  configured for the local environment.

## Features

- **PDF upload and processing:** Upload PDFs through the UI or API. Files are
  limited to 20 MB; invalid, empty, unreadable, password-protected, or
  non-indexable documents are rejected with an error.
- **Text extraction and chunking:** PyMuPDF extracts text by page. The chunker
  uses approximately 800 characters per chunk with 150 characters of overlap
  and preserves source page numbers.
- **Embeddings:** Ollama generates embeddings with `nomic-embed-text`. The
  implementation adds the model's `search_document:` and `search_query:`
  prefixes to document and query inputs respectively.
- **Vector storage:** ChromaDB stores the chunks, embeddings, and document/page
  metadata persistently. Similarity search uses cosine distance.
- **Semantic search:** Search all documents or filter by selected document
  IDs; results include retrieved text and source metadata.
- **RAG question answering:** The backend retrieves passages before asking the
  chat model to answer. It limits the context, applies a relevance threshold,
  and returns an insufficient-information response when relevant context is
  not found.
- **Local LLM integration:** Ollama serves the `qwen2.5:1.5b-instruct` chat
  model by default. The answer prompt treats retrieved document text as
  evidence rather than instructions and asks the model not to invent facts or
  citations.
- **Web application:** React and Vite frontend; FastAPI backend with upload,
  document management, search, chat, and health endpoints.

## Architecture and Request Flow

```text
Browser -> React / Vite -> FastAPI backend
                              |
            +-----------------+-----------------+
            |                                   |
      PDF upload                           Search / chat
            |                                   |
      PyMuPDF extraction                 Query embedding
            |                                   |
      Page-aware chunking                      Ollama
            |                                   |
      Document embeddings                       v
            |                             ChromaDB search
            +----------> ChromaDB               |
                                                v
                                       Retrieved passages
                                                |
                                 +--------------+---------+
                                 |                        |
                              Search                 Chat / RAG
                                                          |
                                                    Ollama chat
                                                          |
                                                          v
                                         Answer and source metadata
```

For ingestion, the backend validates the PDF, extracts text and page metadata,
chunks the text, obtains embeddings from Ollama, then stores the chunks in
ChromaDB. For search and chat, it embeds the query, searches ChromaDB, and
returns matching passages. Chat additionally sends bounded retrieved context
to the Ollama chat model and returns the answer with source references.

## Technology Stack

| Area | Technologies |
| --- | --- |
| Frontend | React, Vite, Axios, lucide-react |
| Backend | Python, FastAPI, Uvicorn |
| PDF processing | PyMuPDF |
| Embeddings and chat | Ollama, `nomic-embed-text`, `qwen2.5:1.5b-instruct` |
| Vector database | ChromaDB persistent client |
| Containers | Dockerfiles and Docker Compose |
| Monitoring companion stack | Grafana, Prometheus, Loki, Grafana Alloy, node-exporter |

## Project Structure

```text
.
├── backend/
│   ├── main.py
│   ├── requirements.txt
│   ├── services/
│   │   ├── document_indexer.py
│   │   ├── embedding_migration.py
│   │   ├── embedding_service.py
│   │   ├── llm_service.py
│   │   ├── pdf_processor.py
│   │   ├── rag_service.py
│   │   ├── text_chunker.py
│   │   └── vector_store.py
│   └── tests/
│       ├── test_chat_api.py
│       ├── test_document_api.py
│       ├── test_document_indexer.py
│       ├── test_embedding_migration.py
│       ├── test_embedding_service.py
│       ├── test_llm_service.py
│       ├── test_pdf_processor.py
│       ├── test_rag_service.py
│       ├── test_search_request.py
│       ├── test_text_chunker.py
│       └── test_vector_store.py
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ChatInput.jsx
│   │   │   ├── ChatWindow.jsx
│   │   │   ├── DocumentSearch.jsx
│   │   │   ├── FileUpload.jsx
│   │   │   ├── Header.jsx
│   │   │   └── Sidebar.jsx
│   │   ├── services/api.js
│   │   ├── assets/
│   │   │   ├── hero.png
│   │   │   ├── react.svg
│   │   │   └── vite.svg
│   │   ├── App.jsx
│   │   ├── App.css
│   │   ├── index.css
│   │   └── main.jsx
│   ├── public/
│   │   ├── favicon.svg
│   │   └── icons.svg
│   ├── package-lock.json
│   ├── package.json
│   └── .env.example
├── Dockerfile.backend
├── Dockerfile.frontend
├── docker-compose.yml
├── enterprise-ai-monitoring-dashboard.json
├── .dockerignore
├── .gitignore
└── PROJECT_PROGRESS.txt
```

The local ChromaDB directory is `backend/vector_db/`; it is runtime data and
is not required as source code. The main application Compose project stores
its data in the external Docker volume `knowledge_assistant_data`.

## Prerequisites

- Python 3.13 is the version used by `Dockerfile.backend`; use a compatible
  Python installation for local development.
- Node.js and npm. The frontend Docker build uses Node.js 24.
- Ollama installed and running, with both required models available.
- Docker Engine/Desktop with the Docker Compose plugin for container
  deployment.

## Ollama Setup

Install and start Ollama for your operating system, then fetch the models used
by the application:

```powershell
ollama pull nomic-embed-text
ollama pull qwen2.5:1.5b-instruct
ollama list
```

The backend defaults to an Ollama API at `http://localhost:11434`. Docker
Compose configures the backend to reach Ollama on the Docker host using
`host.docker.internal:11434`. Ensure Ollama is reachable from the backend
container when using Compose.

## Environment Variables

The backend reads these variables from its process environment. Set values in
the shell or deployment environment before starting the backend; the code does
not load a backend `.env` file.

| Variable | Purpose | Example value |
| --- | --- | --- |
| `OLLAMA_BASE_URL` | Ollama API base URL | `<OLLAMA_BASE_URL>` |
| `OLLAMA_EMBEDDING_MODEL` | Embedding model name | `<EMBEDDING_MODEL_NAME>` |
| `OLLAMA_CHAT_MODEL` | Chat model name | `<CHAT_MODEL_NAME>` |
| `OLLAMA_CHAT_TIMEOUT` | Chat request timeout in seconds | `<TIMEOUT_SECONDS>` |
| `RAG_MAX_COSINE_DISTANCE` | Maximum cosine distance considered relevant | `<DISTANCE_THRESHOLD>` |
| `CHROMA_DB_PATH` | Persistent ChromaDB directory | `<CHROMA_DB_DIRECTORY>` |
| `VITE_API_BASE_URL` | Frontend API base URL, read by Vite | `<BACKEND_API_BASE_URL>` |

The source defaults are `http://localhost:11434` for Ollama,
`nomic-embed-text` for embeddings, `qwen2.5:1.5b-instruct` for chat,
120 seconds for the chat timeout, and 0.48 for the RAG cosine-distance
threshold. ChromaDB defaults to `backend/vector_db/` locally. In Compose, the
backend path is `/app/backend/vector_db` and is backed by the named external
volume.

The frontend falls back to `http://127.0.0.1:8000` when
`VITE_API_BASE_URL` is unset. Vite variables are included in the frontend
bundle; do not put credentials or other secrets in frontend variables.
`Dockerfile.frontend` currently builds with `http://localhost:8000`, which is
suitable when the browser and published containers are on the same host.

Example PowerShell overrides (replace each placeholder with a value suitable
for your environment):

```powershell
$env:OLLAMA_BASE_URL = "<OLLAMA_BASE_URL>"
$env:OLLAMA_EMBEDDING_MODEL = "<EMBEDDING_MODEL_NAME>"
$env:OLLAMA_CHAT_MODEL = "<CHAT_MODEL_NAME>"
$env:OLLAMA_CHAT_TIMEOUT = "<TIMEOUT_SECONDS>"
$env:RAG_MAX_COSINE_DISTANCE = "<DISTANCE_THRESHOLD>"
$env:CHROMA_DB_PATH = "<CHROMA_DB_DIRECTORY>"
```

Do not commit local environment files or secret values.

## Local Development

### Backend

From the project root in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

The local backend uses the configured Ollama service and stores ChromaDB data
under `backend/vector_db/` unless `CHROMA_DB_PATH` is set.

### Frontend

In a second terminal:

```powershell
Set-Location frontend
npm ci
npm run dev
```

The Vite development server is normally available at
`http://localhost:5173`. Set `VITE_API_BASE_URL` in the Vite environment if
the backend is not at the default local URL.

## Main Application Docker Compose

The root `docker-compose.yml` is the **main application Compose project**. It
builds and runs only the `backend` and `frontend` services. It does not start
Grafana, Prometheus, Loki, Alloy, or node-exporter; those belong to the
separate monitoring project described below.

The Dockerfiles can be built individually from the project root:

```powershell
docker build -f Dockerfile.backend -t knowledge-assistant-backend:1.0 .
docker build -f Dockerfile.frontend -t knowledge-assistant-frontend:1.0 .
```

The Compose file declares `knowledge_assistant_data` as an **external** named
volume. It must exist before Compose starts; Compose will not create this
external volume automatically. Create it once if needed, then build and start
the services:

```powershell
docker volume create knowledge_assistant_data
docker compose up --build -d
docker compose ps
```

Compose starts the backend and frontend, publishes ports 8000 and 5173, and
waits for the backend health check before starting the frontend. The backend
uses the host Ollama service; Ollama and the required models must already be
available. The external volume preserves indexed ChromaDB data independently
of the Compose containers. Back up or retain this volume if the indexed
documents must be preserved.

For backend logs:

```powershell
docker compose logs -f backend
```

## Application URLs

| Service | URL |
| --- | --- |
| Frontend | `http://localhost:5173` |
| Backend root | `http://localhost:8000/` |
| Backend health | `http://localhost:8000/health` |
| FastAPI interactive API documentation | `http://localhost:8000/docs` |
| Ollama API (default local URL) | `http://localhost:11434` |

## API Endpoint Summary

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/` | Application status message |
| `GET` | `/health` | Backend health response |
| `POST` | `/api/documents/upload` | Upload a PDF as multipart form field `file`, extract and index it |
| `GET` | `/api/documents` | List indexed documents |
| `DELETE` | `/api/documents/{document_id}` | Delete one indexed document |
| `POST` | `/api/search` | Semantic search across all documents or selected `document_ids` |
| `POST` | `/api/documents/{document_id}/search` | Search within one document |
| `POST` | `/api/chat` | Answer a question from retrieved passages and return source information |

Search and chat JSON requests accept `top_k` from 1 to 20, defaulting to 3.
Search accepts a non-empty `query`; chat accepts a non-empty `question`.
Optional `document_ids` limits search or chat to selected indexed documents.
The upload endpoint accepts PDF files up to 20 MB. See `/docs` for the
interactive request and response schemas.

## Tests and Frontend Checks

Run the backend `unittest` suite from the project root:

```powershell
python -m unittest discover -s backend\tests -v
```

Run frontend lint and production build from `frontend/`:

```powershell
npm run lint
npm run build
```

The progress notes record prior successful test, lint, and build runs. Those
historical results are not a substitute for rerunning checks against the
version being submitted.

## Separate Monitoring Compose Project

Monitoring is provided by a **separate Compose project**, not by the root
application `docker-compose.yml` and not by a Compose file checked into this
repository. In the current development environment, the separate
configuration is at
`D:\Projects\Observability_Docker_Task\docker-compose.yml`. Obtain that
directory/configuration separately to reproduce monitoring on another
machine. Start its default services with:

```powershell
docker compose -f "D:\Projects\Observability_Docker_Task\docker-compose.yml" -p observability_docker_task up -d
```

The companion stack includes Grafana, Prometheus, Loki, Alloy, node-exporter,
and an `app-logger` demo service. Its published URLs are:

| Service | URL |
| --- | --- |
| Grafana | `http://localhost:3000` |
| Prometheus | `http://localhost:9090` |
| Loki | `http://localhost:3100` |
| Alloy UI | `http://localhost:12345` |
| node-exporter | `http://localhost:9100/metrics` |

The Prometheus configuration scrapes Prometheus itself and node-exporter.
Alloy tails log files from the companion project's `logs/` directory and
sends them to Loki. The application Compose file does not configure
application metrics or ship backend logs to this stack. The companion Compose
configuration declares Prometheus and Loki data-source configuration, but
does not mount that configuration into Grafana; configure the data sources in
Grafana if they are not already present. For a containerized Grafana, the
Compose network service URLs are `http://prometheus:9090` and
`http://loki:3100`.

## Importing the Grafana Dashboard

The dashboard export is
[`enterprise-ai-monitoring-dashboard.json`](enterprise-ai-monitoring-dashboard.json).
After Prometheus and Loki data sources are available in Grafana:

1. Open Grafana at `http://localhost:3000`.
2. Open **Dashboards** and choose **New > Import**.
3. Upload `enterprise-ai-monitoring-dashboard.json`.
4. Select the corresponding Prometheus and Loki data sources if Grafana
   prompts for them, then import the dashboard.

The JSON contains seven panels: WSL2 host CPU, memory, disk read/write, and
tmpfs metrics; Prometheus target status; and historical demo logs. The logs
panel is explicitly for demo logs, not application logs. The monitoring
configuration scrapes node-exporter for host metrics and Alloy tails the
companion project's demo log files. It does not configure application-specific
metrics or forward backend application logs.

## Kubernetes and CI/CD Status

### Kubernetes: Not implemented

No Kubernetes manifests or Helm chart are included. The Dockerfiles and
application Compose project are not Kubernetes deployment configuration.

### CI/CD: Pending

CI/CD is pending. No completed GitHub Actions pipeline is included in the
repository; there is currently no `.github/workflows/` directory. Automated
build, test, and release workflows should not be considered implemented until
the workflow is added and verified.

## Known Limitations and Troubleshooting

- **PDF text:** The implementation extracts selectable text; it does not
  provide OCR for scanned/image-only PDFs. Password-protected PDFs are not
  supported.
- **Upload errors:** Uploads must be valid, readable PDFs no larger than
  20 MB. A PDF with no extractable text cannot be indexed.
- **Ollama errors:** If embedding or chat requests fail, verify Ollama is
  running at the configured URL and both required models are installed. For
  Compose, verify the backend container can reach the host Ollama service.
- **No answer or insufficient context:** The RAG flow may abstain when no
  sufficiently relevant passage is retrieved. The default distance threshold
  is 0.48 and can be overridden with `RAG_MAX_COSINE_DISTANCE`.
- **Missing Compose volume:** If Compose reports that
  `knowledge_assistant_data` does not exist, create the external volume with
  `docker volume create knowledge_assistant_data`.
- **Frontend cannot reach backend:** Check the backend health URL and
  `VITE_API_BASE_URL`. In the Docker image, the frontend API URL is baked in
  at build time; it is not a runtime Compose setting.
- **Monitoring shows no application data:** The companion Prometheus setup
  scrapes Prometheus and node-exporter, while Alloy tails demo log files.
  Application-specific metrics and backend log forwarding are not configured.
- **Deployment maturity:** The repository has no Kubernetes or CI/CD
  configuration. Review deployment security and operational requirements
  before exposing the development application beyond a trusted local
  environment.