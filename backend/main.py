
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from starlette.concurrency import run_in_threadpool

from backend.services.document_indexer import NoIndexableTextError, index_document
from backend.services.embedding_service import (
    EMBEDDING_MODEL,
    EmbeddingServiceError,
    embed_query,
)
from backend.services.llm_service import (
    ChatModelUnavailableError,
    OllamaChatError,
    OllamaChatResponseError,
    OllamaChatTimeoutError,
)
from backend.services.pdf_processor import InvalidPDFError, extract_pdf_information
from backend.services.rag_service import answer_question
from backend.services.vector_store import (
    DocumentNotFoundError,
    VectorStoreError,
    delete_document_chunks,
    document_exists,
    list_indexed_documents,
    search_document_chunks,
)

# Create FastAPI application
app = FastAPI(
    title="Enterprise AI Knowledge Assistant",
    description="AI-powered PDF question answering system",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)

MAX_UPLOAD_SIZE = 20 * 1024 * 1024


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    top_k: int = Field(default=3, ge=1, le=20)

    @field_validator("query")
    @classmethod
    def require_non_blank_query(cls, value: str) -> str:
        normalized_query = value.strip()
        if not normalized_query:
            raise ValueError("Query must not be empty.")
        return normalized_query


class MultiDocumentSearchRequest(SearchRequest):
    document_ids: list[str] | None = None

    @field_validator("document_ids")
    @classmethod
    def normalize_document_ids(cls, values: list[str] | None) -> list[str] | None:
        if values is None:
            return None
        if not values:
            raise ValueError("Select at least one document, or omit document_ids to search all.")
        normalized = [value.strip() for value in values]
        if any(not value for value in normalized):
            raise ValueError("Document IDs must not be empty.")
        return list(dict.fromkeys(normalized))


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    document_ids: list[str] | None = None
    top_k: int = Field(default=3, ge=1, le=20)

    @field_validator("question")
    @classmethod
    def require_non_blank_question(cls, value: str) -> str:
        normalized_question = value.strip()
        if not normalized_question:
            raise ValueError("Question must not be empty.")
        return normalized_question

    @field_validator("document_ids")
    @classmethod
    def normalize_document_ids(cls, values: list[str] | None) -> list[str] | None:
        if values is None:
            return None
        if not values:
            raise ValueError("Select at least one document, or omit document_ids to search all.")
        normalized = [value.strip() for value in values]
        if any(not value for value in normalized):
            raise ValueError("Document IDs must not be empty.")
        return list(dict.fromkeys(normalized))


# Home API
@app.get("/")
def home():
    return {
        "message": "Enterprise AI Knowledge Assistant is running!"
    }


# Health check API
@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "application": "Enterprise AI Knowledge Assistant"
    }


@app.post("/api/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    try:
        if not file.filename or not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Please upload a PDF file.")

        pdf_bytes = await file.read(MAX_UPLOAD_SIZE + 1)
        if not pdf_bytes:
            raise HTTPException(status_code=400, detail="The uploaded PDF is empty.")
        if len(pdf_bytes) > MAX_UPLOAD_SIZE:
            raise HTTPException(
                status_code=413,
                detail="The PDF exceeds the 20 MB upload limit.",
            )

        try:
            document_info = await run_in_threadpool(extract_pdf_information, pdf_bytes)
        except InvalidPDFError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

        try:
            indexing_info = await run_in_threadpool(
                index_document,
                file.filename,
                document_info["pages"],
            )
        except NoIndexableTextError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except EmbeddingServiceError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error
        except VectorStoreError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error

        return {
            "filename": file.filename,
            "document_id": indexing_info["document_id"],
            "total_pages": document_info["page_count"],
            "page_count": document_info["page_count"],
            "extracted_characters": document_info["character_count"],
            "character_count": document_info["character_count"],
            "empty_pages": document_info["empty_pages"],
            "total_chunks": indexing_info["total_chunks"],
            "indexing_status": "indexed",
            "text_preview": document_info["text_preview"],
        }
    finally:
        await file.close()


@app.get("/api/documents")
async def get_documents():
    try:
        return await run_in_threadpool(list_indexed_documents)
    except VectorStoreError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@app.delete("/api/documents/{document_id}")
async def remove_document(document_id: str):
    try:
        await run_in_threadpool(delete_document_chunks, document_id)
    except DocumentNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except VectorStoreError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    return {"document_id": document_id, "deleted": True}


@app.post("/api/chat")
async def chat(request: ChatRequest):
    if request.document_ids is not None:
        for document_id in request.document_ids:
            try:
                exists = await run_in_threadpool(document_exists, document_id)
            except VectorStoreError as error:
                raise HTTPException(status_code=503, detail=str(error)) from error
            if not exists:
                raise HTTPException(
                    status_code=404,
                    detail="One or more selected documents have not been indexed.",
                )

    try:
        result = await run_in_threadpool(
            answer_question,
            request.question,
            request.document_ids,
            request.top_k,
        )
    except DocumentNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except EmbeddingServiceError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except VectorStoreError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except ChatModelUnavailableError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except OllamaChatTimeoutError as error:
        raise HTTPException(status_code=504, detail=str(error)) from error
    except OllamaChatResponseError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    except OllamaChatError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error

    return {
        "question": request.question,
        **result,
    }


@app.post("/api/search")
async def search_documents(request: MultiDocumentSearchRequest):
    if request.document_ids is not None:
        if not request.document_ids:
            raise HTTPException(
                status_code=422,
                detail="Select at least one document, or omit document_ids to search all.",
            )
        for document_id in request.document_ids:
            try:
                exists = await run_in_threadpool(document_exists, document_id)
            except VectorStoreError as error:
                raise HTTPException(status_code=503, detail=str(error)) from error
            if not exists:
                raise HTTPException(
                    status_code=404,
                    detail="One or more selected documents have not been indexed.",
                )

    try:
        query_embedding = await run_in_threadpool(embed_query, request.query)
        results = await run_in_threadpool(
            search_document_chunks,
            None,
            query_embedding,
            request.top_k,
            request.document_ids,
        )
    except DocumentNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except EmbeddingServiceError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except VectorStoreError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error

    return {
        "query": request.query,
        "document_ids": request.document_ids,
        "embedding_model": EMBEDDING_MODEL,
        "embedding_dimension": len(query_embedding),
        "results": results,
        "result_count": len(results),
    }


@app.post("/api/documents/{document_id}/search")
async def search_document(document_id: str, request: SearchRequest):
    try:
        exists = await run_in_threadpool(document_exists, document_id)
    except VectorStoreError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    if not exists:
        raise HTTPException(status_code=404, detail="The requested document has not been indexed.")

    try:
        query_embedding = await run_in_threadpool(embed_query, request.query)
    except EmbeddingServiceError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error

    try:
        results = await run_in_threadpool(
            search_document_chunks,
            document_id,
            query_embedding,
            request.top_k,
        )
    except DocumentNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except VectorStoreError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error

    return {
        "document_id": document_id,
        "query": request.query,
        "embedding_model": EMBEDDING_MODEL,
        "embedding_dimension": len(query_embedding),
        "results": results,
        "result_count": len(results),
    }
