# Enterprise AI Knowledge Assistant

## Project overview

The application extracts PDF text, indexes page-aware chunks with local Ollama embeddings, and stores them in persistent ChromaDB. It supports multi-document retrieval and grounded question answering using a local Ollama chat model. Answers include source references from the actual retrieved document metadata.

## Features

- Upload PDFs and extract text page by page.
- Index documents locally and search one or more indexed PDFs.
- Ask document-grounded questions and receive source references from stored document metadata.
- Persist the local vector index in ChromaDB.

## Technology stack

- Frontend: React and Vite.
- Backend: Python and FastAPI.
- PDF extraction: PyMuPDF.
- Embeddings and chat: Ollama with `nomic-embed-text:latest` and `qwen2.5:1.5b-instruct`.
- Vector storage: ChromaDB.

## Requirements

- Python 3.13 and the project `.venv`
- Node.js and npm
- Ollama with `nomic-embed-text:latest` and `qwen2.5:1.5b-instruct` installed

Create the project virtual environment and install backend dependencies from the project root:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

## Start the backend

From the project root:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

The API is at `http://127.0.0.1:8000`; Swagger documentation is at `http://127.0.0.1:8000/docs`. Ollama must be running at `http://localhost:11434`.

The backend reads these environment variables when it starts:

- `OLLAMA_BASE_URL` (default `http://localhost:11434`)
- `OLLAMA_EMBEDDING_MODEL` (default `nomic-embed-text`; Ollama resolves this to `nomic-embed-text:latest`)
- `OLLAMA_CHAT_MODEL` (default `qwen2.5:1.5b-instruct`)
- `OLLAMA_CHAT_TIMEOUT` (request timeout in seconds; default `120`)
- `RAG_MAX_COSINE_DISTANCE` (default `0.48`; matches farther than this are treated as insufficient context)

Set overrides in the same PowerShell window before starting Uvicorn, for example:

```powershell
$env:OLLAMA_CHAT_MODEL = "qwen2.5:1.5b-instruct"
$env:OLLAMA_CHAT_TIMEOUT = "120"
```

The chat request uses a low temperature, a 4,096-token context window, and a bounded response size for the local 8 GB RAM environment. No external paid API is used.

## Start the frontend

In another PowerShell window:

```powershell
Set-Location .\frontend
npm ci
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
npm run dev
```

Open `http://localhost:5173`. `VITE_API_BASE_URL` configures the backend URL.

## Document APIs

### Upload and index a PDF

`POST /api/documents/upload` accepts multipart form data with a `file` field. PDFs must be readable, non-empty, and no larger than 20 MB. The backend extracts every page, chunks page text, embeds it with Ollama, then stores it in ChromaDB. A success response includes the generated `document_id`, page and character totals, empty page numbers, chunk count, indexing status, and a short preview. Indexing errors do not return a successful response.

### Retrieve relevant passages

`GET /api/documents` lists indexed PDFs. `DELETE /api/documents/{document_id}` removes only that document's chunks.

`POST /api/search` searches all documents when `document_ids` is omitted, or restricts retrieval to the selected IDs:

```json
{
  "query": "What is the main objective of this project?",
  "top_k": 3,
  "document_ids": ["returned-document-id"]
}
```

Omit `document_ids` to search across all indexed PDFs. `top_k` defaults to 3 and must be between 1 and 20. Results include passage text, source filename, original page number, and ChromaDB cosine distance (lower is closer). The existing `POST /api/documents/{document_id}/search` endpoint remains available for single-document searches. These retrieval endpoints return passages and do not generate answers.

For `nomic-embed-text`, stored passages use the `search_document:` task prefix and questions use `search_query:`. After upgrading an existing database created without these prefixes, run this once from the project root to update only stored vectors from their existing text and preserve document IDs/metadata:

```powershell
.\.venv\Scripts\python.exe -m backend.services.embedding_migration
```

### Ask a document-grounded question

`POST /api/chat` retrieves chunks, passes only their text to the local chat model, and returns source references from the corresponding Chroma metadata:

```json
{
  "question": "Which technologies are used in this project?",
  "document_ids": ["returned-document-id"],
  "top_k": 3
}
```

Omit `document_ids` to search all indexed PDFs. Select one or more IDs to restrict the search. `top_k` is optional, defaults to 3, and must be between 1 and 20.

Successful response:

```json
{
  "question": "Which technologies are used in this project?",
  "answer": "A concise answer grounded in the retrieved passages.",
  "sources": [
    {
      "document_id": "returned-document-id",
      "filename": "uploaded-document.pdf",
      "page_number": 3,
      "excerpt": "Retrieved passage text supplied to the model."
    }
  ],
  "status": "success"
}
```

If retrieval finds no sufficiently close passage, the API returns an insufficient-information response with no unsupported source citations. Ollama connection/model failures return a service error; chat timeouts return HTTP 504. The system prompt treats PDF passages as untrusted evidence, and the application never asks the model to invent filenames or page references. The existing `POST /api/search` endpoint and response shape remain available.

## Storage and tests

ChromaDB persists its collection in `backend/vector_db/`, which is excluded from source control because it contains indexed document text. Default chunks are 800 characters with a 150-character overlap.

Run the backend unit tests:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s backend\tests -v
```

To run an actual Ollama/ChromaDB integration check, keep Ollama running with `nomic-embed-text` available, then upload a PDF through the frontend or `POST /api/documents/upload` and search it using the returned `document_id`.

## Main code areas

- `backend/main.py`: preserved home/health routes, PDF upload/indexing, and document search APIs.
- `backend/services/pdf_processor.py`: page-by-page extraction and empty-page statistics.
- `backend/services/text_chunker.py`: reusable page-aware chunking.
- `backend/services/embedding_service.py`: batched local Ollama embeddings, task prefixes, and response validation.
- `backend/services/llm_service.py`: configurable local Ollama chat model, bounded generation options, and response/error validation.
- `backend/services/rag_service.py`: query embedding, document-filtered retrieval, context limits, untrusted-context prompt, and metadata-based citations.
- `backend/services/vector_store.py`: persistent ChromaDB operations, multi-document filtering, listing, and deletion.
- `backend/services/document_indexer.py`: coordinates chunking, embedding, and storage.
- `frontend/src/components/ChatWindow.jsx`: multi-turn chat UI, document scope selection, loading/errors, and source references.
- `frontend/src/components/DocumentSearch.jsx`: retrieval query form and source-attributed results.
- `frontend/src/services/api.js`: Axios health, upload, search, and chat requests.
