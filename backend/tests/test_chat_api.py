import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.main import app
from backend.services.embedding_service import EmbeddingServiceError
from backend.services.llm_service import (
    ChatModelUnavailableError,
    OllamaChatError,
    OllamaChatResponseError,
    OllamaChatTimeoutError,
)
from backend.services.vector_store import VectorStoreError


class ChatApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_returns_answer_and_actual_source_references(self) -> None:
        result = {
            "answer": "The project objective is described in the source.",
            "sources": [{
                "document_id": "doc-a",
                "filename": "actual.pdf",
                "page_number": 6,
                "excerpt": "Actual retrieved passage.",
            }],
            "status": "success",
        }
        with (
            patch("backend.main.document_exists", return_value=True),
            patch("backend.main.answer_question", return_value=result) as answer_question,
        ):
            response = self.client.post(
                "/api/chat",
                json={
                    "question": " What is the objective? ",
                    "document_ids": ["doc-a"],
                    "top_k": 7,
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["question"], "What is the objective?")
        self.assertEqual(response.json()["sources"][0]["filename"], "actual.pdf")
        self.assertEqual(response.json()["sources"][0]["page_number"], 6)
        answer_question.assert_called_once_with(
            "What is the objective?",
            ["doc-a"],
            7,
        )

    def test_searches_all_documents_when_document_ids_are_omitted(self) -> None:
        result = {
            "answer": "Supported answer.",
            "sources": [],
            "status": "success",
        }
        with patch("backend.main.answer_question", return_value=result) as answer_question:
            response = self.client.post("/api/chat", json={"question": "Question?"})

        self.assertEqual(response.status_code, 200)
        answer_question.assert_called_once_with("Question?", None, 3)

    def test_accepts_supported_explicit_top_k_values(self) -> None:
        result = {"answer": "Supported answer.", "sources": [], "status": "success"}
        for top_k in (1, 5, 20):
            with self.subTest(top_k=top_k):
                with patch("backend.main.answer_question", return_value=result) as answer_question:
                    response = self.client.post(
                        "/api/chat",
                        json={"question": "Question?", "top_k": top_k},
                    )

                self.assertEqual(response.status_code, 200)
                answer_question.assert_called_once_with("Question?", None, top_k)

    def test_rejects_empty_question_and_invalid_top_k(self) -> None:
        for request_body in (
            {"question": ""},
            {"question": "   "},
            {"question": "Question?", "top_k": 0},
            {"question": "Question?", "top_k": 21},
        ):
            with self.subTest(request_body=request_body):
                response = self.client.post("/api/chat", json=request_body)
                self.assertEqual(response.status_code, 422)

    def test_unknown_selected_document_returns_404(self) -> None:
        with (
            patch("backend.main.document_exists", return_value=False),
            patch("backend.main.answer_question") as answer_question,
        ):
            response = self.client.post(
                "/api/chat",
                json={"question": "Question?", "document_ids": ["missing"]},
            )

        self.assertEqual(response.status_code, 404)
        answer_question.assert_not_called()

    def test_maps_chat_model_failures_to_safe_http_errors(self) -> None:
        for error, expected_status in (
            (EmbeddingServiceError("safe embedding message"), 503),
            (VectorStoreError("safe vector message"), 503),
            (ChatModelUnavailableError("safe missing-model message"), 503),
            (OllamaChatTimeoutError("safe timeout message"), 504),
            (OllamaChatResponseError("safe response message"), 502),
            (OllamaChatError("safe service message"), 503),
        ):
            with self.subTest(error=type(error).__name__):
                with patch("backend.main.answer_question", side_effect=error):
                    response = self.client.post("/api/chat", json={"question": "Question?"})

                self.assertEqual(response.status_code, expected_status)
                self.assertEqual(response.json()["detail"], str(error))

    def test_existing_retrieval_search_endpoint_keeps_its_response_shape(self) -> None:
        passages = [{
            "chunk_id": "doc-a:0",
            "text": "Retrieved passage.",
            "filename": "actual.pdf",
            "page_number": 2,
            "chunk_index": 0,
            "distance": 0.2,
        }]
        with (
            patch("backend.main.embed_query", return_value=[0.1, 0.2]),
            patch("backend.main.search_document_chunks", return_value=passages),
        ):
            response = self.client.post(
                "/api/search",
                json={"query": "Find a passage", "top_k": 5},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["results"], passages)
        self.assertEqual(response.json()["result_count"], 1)


if __name__ == "__main__":
    unittest.main()
