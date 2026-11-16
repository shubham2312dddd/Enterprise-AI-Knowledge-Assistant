# Enterprise AI Knowledge Assistant

An application for indexing PDF documents and answering questions with retrieved passages. The React frontend communicates with a FastAPI backend.

PDF text is extracted and stored as searchable chunks in ChromaDB. Local Ollama models provide embeddings and grounded answer generation.

**GitHub Repository:** [Enterprise AI Knowledge Assistant](https://github.com/shubham2312dddd/Enterprise-AI-Knowledge-Assistant)

## Contents

- [Problem Statement and Objectives](#problem-statement-and-objectives)
- [Features](#features)
- [Architecture and Request Flow](#architecture-and-request-flow)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Fresh Laptop Setup](#fresh-laptop-setup)
- [Ollama Setup](#ollama-setup)
- [Environment Variables](#environment-variables)
- [Local Development](#local-development)
- [Docker Deployment](#docker-deployment)
- [Application URLs](#application-urls)
- [API Endpoint Summary](#api-endpoint-summary)
- [Tests and Frontend Checks](#tests-and-frontend-checks)
- [CI/CD Pipeline](#cicd-pipeline)
- [Monitoring Setup](#monitoring-setup)
- [Importing the Grafana Dashboard](#importing-the-grafana-dashboard)
- [Known Limitations and Troubleshooting](#known-limitations-and-troubleshooting)

## Problem Statement and Objectives

Important knowledge is often spread across lengthy documents, making it difficult and time-consuming to find relevant information.

This project provides an AI-powered document assistant that:

- Accepts PDF uploads and extracts text.
- Indexes page-aware text chunks for semantic retrieval.
- Supports searching across indexed documents or selected documents.
- Generates answers using retrieved document passages.
- Provides source references for better answer verification.
- Uses locally configured embedding and language models through Ollama.

## Features

- **PDF Upload and Processing:** Upload PDF documents through the application interface or API.
- **Text Extraction and Chunking:** PyMuPDF extracts text page by page. Text is divided into chunks of approximately 800 characters with 150 characters of overlap.
- **Embeddings:** Ollama generates embeddings using `nomic-embed-text`.
- **Vector Storage:** ChromaDB stores document chunks, embeddings, and metadata persistently.
- **Semantic Search:** Search across all indexed documents or filter results using selected document IDs.
- **RAG-Based Question Answering:** Retrieves relevant passages before generating an answer.
- **Context-Aware Responses:** The system avoids generating unsupported answers when relevant information is unavailable.
- **Local LLM Integration:** Uses `qwen2.5:1.5b-instruct` for answer generation.
- **Document Management:** Upload, view, search, and delete indexed documents.
- **React Web Interface:** Provides a user-friendly interface for document upload, search, and AI chat.
- **Docker Deployment:** Runs the frontend and backend using Docker Compose.
- **Automated CI:** GitHub Actions runs backend tests, frontend checks, and Docker image builds.

## Architecture and Request Flow

```text
                 Browser
                    |
                    v
              React / Vite
                    |
                    v
               FastAPI
                    |
          +---------+---------+
          |                   |
          v                   v
      PDF Upload          Search / Chat
          |                   |
          v                   v
    PyMuPDF Extraction    Query Embedding
          |                   |
          v                   v
    Text Chunking          Ollama
          |                   |
          v                   v
    Document Embedding   ChromaDB Search
          |                   |
          v                   v
       ChromaDB          Retrieved Passages
                              |
                              v
                         Ollama LLM
                              |
                              v
                      Generated Answer
                              |
                              v
                     Source References
```

**Document ingestion flow:**

1. The user uploads a PDF.
2. The backend validates the document.
3. PyMuPDF extracts text and page information.
4. The text is divided into overlapping chunks.
5. Ollama generates embeddings.
6. ChromaDB stores the chunks, embeddings, and metadata.

**Question-answering flow:**

1. The user submits a question.
2. The backend generates an embedding for the query.
3. ChromaDB retrieves relevant document passages.
4. The retrieved context is sent to the Ollama chat model.
5. The model generates an answer based on the retrieved information.
6. The application returns the answer and source references.

## Technology Stack

| Area | Technologies |
| --- | --- |
| Frontend | React, Vite, Axios, lucide-react |
| Backend | Python, FastAPI, Uvicorn |
| PDF Processing | PyMuPDF |
| Embedding Model | Ollama, nomic-embed-text |
| Chat Model | Ollama, qwen2.5:1.5b-instruct |
| Vector Database | ChromaDB |
| Containerization | Docker, Docker Compose |
| CI | GitHub Actions |
| Monitoring | Grafana, Prometheus, Loki, Grafana Alloy, Node Exporter |

## Project Structure

```text
Enterprise-AI-Knowledge-Assistant/
|
├── .github/
│   └── workflows/
│       └── ci-cd.yml
|
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
|
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── services/
│   │   ├── assets/
│   │   ├── App.jsx
│   │   ├── App.css
│   │   ├── index.css
│   │   └── main.jsx
│   ├── public/
│   ├── package.json
│   └── package-lock.json
|
├── Dockerfile.backend
├── Dockerfile.frontend
├── docker-compose.yml
├── enterprise-ai-monitoring-dashboard.json
├── .dockerignore
├── .gitignore
└── README.md
```

The ChromaDB directory stores runtime vector data. In Docker Compose, persistent application data is stored using the external Docker volume `knowledge_assistant_data`.

## Prerequisites

Install the following software before running the project:

- Python 3.13
- Node.js 24 and npm
- Docker Desktop with Docker Compose
- Ollama
- Git

## Fresh Laptop Setup

Follow these steps to run the project on a new laptop.

### Step 1: Clone the GitHub Repository

```powershell
git clone https://github.com/shubham2312dddd/Enterprise-AI-Knowledge-Assistant.git

cd Enterprise-AI-Knowledge-Assistant
```

### Step 2: Install and Configure Ollama

Download and install Ollama from:

https://ollama.com/

Start Ollama and download the required models:

```powershell
ollama pull nomic-embed-text

ollama pull qwen2.5:1.5b-instruct
```

Verify the installed models:

```powershell
ollama list
```

### Step 3: Start Docker Desktop

Open Docker Desktop and ensure that Docker Engine is running.

Verify Docker:

```powershell
docker --version

docker compose version
```

### Step 4: Create the Persistent Docker Volume

The application uses an external Docker volume to preserve indexed document data.

Create it once:

```powershell
docker volume create knowledge_assistant_data
```

### Step 5: Build and Start the Application

From the project root, execute:

```powershell
docker compose up --build -d
```

Check the running containers:

```powershell
docker compose ps
```

### Step 6: Open the Application

Open the frontend:

http://localhost:5173

Backend API:

http://localhost:8000/docs

**Important:** Ollama runs separately from Docker. Keep Ollama running and make sure the required models are available. The Docker backend is configured to access the host Ollama service through `host.docker.internal`.

## Ollama Setup

The application uses two Ollama models:

| Model | Purpose |
| --- | --- |
| `nomic-embed-text` | Generates embeddings for documents and queries |
| `qwen2.5:1.5b-instruct` | Generates answers using retrieved context |

Install the models:

```powershell
ollama pull nomic-embed-text

ollama pull qwen2.5:1.5b-instruct
```

Verify:

```powershell
ollama list
```

The default Ollama API URL is:

```text
http://localhost:11434
```

For Docker deployment, the backend accesses Ollama through:

```text
http://host.docker.internal:11434
```

## Environment Variables

The backend supports the following configuration variables:

| Variable | Purpose |
| --- | --- |
| `OLLAMA_BASE_URL` | Ollama API base URL |
| `OLLAMA_EMBEDDING_MODEL` | Embedding model name |
| `OLLAMA_CHAT_MODEL` | Chat model name |
| `OLLAMA_CHAT_TIMEOUT` | Chat request timeout |
| `RAG_MAX_COSINE_DISTANCE` | Maximum cosine distance considered relevant |
| `CHROMA_DB_PATH` | Persistent ChromaDB directory |
| `VITE_API_BASE_URL` | Frontend API base URL |

Default configuration:

- Ollama URL: `http://localhost:11434`
- Embedding model: `nomic-embed-text`
- Chat model: `qwen2.5:1.5b-instruct`
- Chat timeout: 120 seconds
- RAG cosine-distance threshold: 0.48
- Local ChromaDB directory: `backend/vector_db/`

In Docker Compose, ChromaDB uses the persistent path `/app/backend/vector_db`, backed by the named external volume.

Do not commit local environment files or secret values.

## Local Development

### Backend Setup

From the project root:

```powershell
python -m venv .venv

.\.venv\Scripts\Activate.ps1

python -m pip install -r backend\requirements.txt

python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

The backend will be available at:

http://localhost:8000

### Frontend Setup

Open another terminal:

```powershell
cd frontend

npm ci

npm run dev
```

The frontend will be available at:

http://localhost:5173

## Docker Deployment

The root `docker-compose.yml` runs the main application services:

- Backend
- Frontend

The Dockerfiles can also be built individually.

### Build Backend Image

```powershell
docker build -f Dockerfile.backend -t knowledge-assistant-backend:1.0 .
```

### Build Frontend Image

```powershell
docker build -f Dockerfile.frontend -t knowledge-assistant-frontend:1.0 .
```

### Start the Complete Application

First, create the external volume if it does not already exist:

```powershell
docker volume create knowledge_assistant_data
```

Then build and start the application:

```powershell
docker compose up --build -d
```

Check the services:

```powershell
docker compose ps
```

View backend logs:

```powershell
docker compose logs -f backend
```

Stop the application:

```powershell
docker compose down
```

The persistent Docker volume is retained when containers are stopped or removed. Do not remove the volume if you want to preserve indexed documents.

## Application URLs

| Service | URL |
| --- | --- |
| Frontend | http://localhost:5173 |
| Backend | http://localhost:8000 |
| Backend Health | http://localhost:8000/health |
| FastAPI Swagger Documentation | http://localhost:8000/docs |
| Ollama API | http://localhost:11434 |

## API Endpoint Summary

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/` | Application status |
| `GET` | `/health` | Backend health check |
| `POST` | `/api/documents/upload` | Upload and index a PDF |
| `GET` | `/api/documents` | List indexed documents |
| `DELETE` | `/api/documents/{document_id}` | Delete an indexed document |
| `POST` | `/api/search` | Search across documents |
| `POST` | `/api/documents/{document_id}/search` | Search within one document |
| `POST` | `/api/chat` | Ask questions using retrieved document context |

Search and chat requests support `top_k` from 1 to 20, with a default value of 3.

Optional `document_ids` can be used to restrict search or chat to selected documents.

The upload endpoint accepts PDF files up to 20 MB.

For complete request and response details, visit the FastAPI Swagger documentation at `/docs`.

## Tests and Frontend Checks

### Backend Tests

Run the backend unit tests from the project root:

```powershell
python -m unittest discover -s backend\tests -v
```

### Frontend Lint

From the frontend directory:

```powershell
npm run lint
```

### Frontend Production Build

```powershell
npm run build
```

These checks help verify backend functionality and frontend code quality before deployment.

## CI/CD Pipeline

The project uses GitHub Actions for Continuous Integration.

Workflow file:

```text
.github/workflows/ci-cd.yml
```

### Continuous Integration (CI)

The GitHub Actions workflow automatically runs when code is pushed or a pull request is created for the configured branch.

The pipeline includes:

1. **Backend Tests:** Installs Python dependencies and runs backend unit tests.
2. **Frontend Checks:** Installs Node.js dependencies, runs linting, and creates a production build.
3. **Docker Image Build:** Builds the backend and frontend Docker images after the required CI jobs succeed.

### Continuous Deployment (CD)

Deployment is currently performed manually using Docker Compose.

After successful CI checks, the application can be deployed by running:

```powershell
docker compose up --build -d
```

### CI/CD Implementation Status

| Component | Status |
| --- | --- |
| GitHub Actions workflow | Implemented |
| Backend automated tests | Implemented |
| Frontend lint and build | Implemented |
| Docker image build validation | Implemented |
| Automated image publishing | Not implemented |
| Automated deployment | Not implemented |
| Manual Docker Compose deployment | Implemented |

**Note:** CI is automated through GitHub Actions. CD is currently a manual deployment process using Docker Compose.

## Monitoring Setup

The project also includes a separate monitoring environment for infrastructure monitoring.

The monitoring stack is maintained separately from the main application Compose project.

It includes:

- Grafana
- Prometheus
- Loki
- Grafana Alloy
- Node Exporter

The monitoring project must be obtained and configured separately on a new machine.

Start the monitoring services from the monitoring project's directory:

```powershell
docker compose up -d
```

Typical monitoring URLs:

| Service | URL |
| --- | --- |
| Grafana | http://localhost:3000 |
| Prometheus | http://localhost:9090 |
| Loki | http://localhost:3100 |
| Alloy UI | http://localhost:12345 |
| Node Exporter | http://localhost:9100/metrics |

The current monitoring configuration collects host-level metrics through Node Exporter and sends configured log files to Loki through Alloy.

**Monitoring limitation:** The current setup does not configure application-specific backend metrics or automatic forwarding of backend application logs.

## Importing the Grafana Dashboard

The repository contains the dashboard export:

[`enterprise-ai-monitoring-dashboard.json`](enterprise-ai-monitoring-dashboard.json)

To import it:

1. Open Grafana at http://localhost:3000.
2. Navigate to **Dashboards**.
3. Select **New → Import**.
4. Upload `enterprise-ai-monitoring-dashboard.json`.
5. Select the appropriate Prometheus and Loki data sources if prompted.
6. Import the dashboard.

The dashboard includes infrastructure metrics and monitoring panels. The log panels depend on the configured demo log sources and should not be interpreted as live application logs.

## Known Limitations and Troubleshooting

- **PDF text extraction:** The application extracts selectable PDF text. OCR for scanned or image-only PDFs is not currently supported.
- **Password-protected PDFs:** Password-protected documents are not supported.
- **Upload errors:** Uploads must be valid, readable PDFs within the 20 MB limit.
- **Ollama connection errors:** Ensure Ollama is running and both required models are installed.
- **Docker cannot access Ollama:** Verify that the backend container can reach the host Ollama service through `host.docker.internal`.
- **Insufficient answer context:** The RAG system may return an insufficient-information response when relevant passages are not retrieved.
- **Missing Docker volume:** Create the external volume using `docker volume create knowledge_assistant_data`.
- **Frontend cannot reach backend:** Verify the backend health endpoint and frontend API URL configuration.
- **Persistent data:** Keep the `knowledge_assistant_data` Docker volume to preserve indexed documents.
- **Monitoring limitations:** The current monitoring setup focuses on host-level metrics and configured demo logs rather than application-specific monitoring.
- **Deployment:** The application can be deployed using Docker Compose. Deployment is currently manual rather than an automated CD process.

---

**Project:** Enterprise AI Knowledge Assistant  
**Repository:** https://github.com/shubham2312dddd/Enterprise-AI-Knowledge-Assistant
