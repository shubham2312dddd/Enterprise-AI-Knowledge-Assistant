import unittest
from unittest.mock import patch

import chromadb
import pymupdf
from fastapi.testclient import TestClient

from backend.main import MAX_UPLOAD_SIZE, app
from backend.services.embedding_service import EmbeddingServiceError


def create_pdf(page_texts: list[str]) -> bytes:
    document = pymupdf.open()
    for text in page_texts:
        page = document.new_page()
        if text:
            page.insert_text((72, 72), text)
    pdf_bytes = document.tobytes()
    document.close()
    return pdf_bytes


class DocumentApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def upload(self, filename: str, content: bytes):
        return self.client.post(
            "/api/documents/upload",
            files={"file": (filename, content, "application/pdf")},
        )

    def test_rejects_non_pdf_empty_and_unreadable_uploads(self) -> None:
        with patch("backend.main.extract_pdf_information") as extract_pdf:
            wrong_type = self.client.post(
                "/api/documents/upload",
                files={"file": ("notes.txt", b"not a pdf", "text/plain")},
            )
            empty_file = self.upload("empty.pdf", b"")

        self.assertEqual(wrong_type.status_code, 400)
        self.assertEqual(empty_file.status_code, 400)
        extract_pdf.assert_not_called()

        unreadable_file = self.upload("broken.pdf", b"not a pdf")
        self.assertEqual(unreadable_file.status_code, 400)

    def test_rejects_oversized_pdf_before_extraction(self) -> None:
        with patch("backend.main.extract_pdf_information") as extract_pdf:
            response = self.upload("large.pdf", b"x" * (MAX_UPLOAD_SIZE + 1))

        self.assertEqual(response.status_code, 413)
        extract_pdf.assert_not_called()

    def test_rejects_pdf_without_extractable_text(self) -> None:
        response = self.upload("image-only.pdf", create_pdf(["", "  \n"]))

        self.assertEqual(response.status_code, 422)
        self.assertIn("No selectable text", response.json()["detail"])

    def test_embedding_failure_returns_service_unavailable(self) -> None:
        with patch(
            "backend.services.document_indexer.embed_documents",
            side_effect=EmbeddingServiceError("Ollama is unavailable."),
        ):
            response = self.upload("unindexed.pdf", create_pdf(["Some searchable text."]))

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["detail"], "Ollama is unavailable.")

    def test_upload_search_citations_and_delete_are_document_isolated(self) -> None:
        collection = chromadb.EphemeralClient().create_collection(
            name="document_chunks",
            metadata={"hnsw:space": "cosine"},
        )
        embedded_texts: list[str] = []

        def fake_document_embeddings(texts: list[str]) -> list[list[float]]:
            embedded_texts.extend(texts)
            return [[1.0, 0.0] for _ in texts]

        with (
            patch("backend.services.vector_store.get_collection", return_value=collection),
            patch(
                "backend.services.document_indexer.embed_documents",
                side_effect=fake_document_embeddings,
            ),
            patch("backend.main.embed_query", return_value=[1.0, 0.0]),
            patch("backend.services.rag_service.embed_query", return_value=[1.0, 0.0]),
            patch(
                "backend.services.rag_service.generate_grounded_answer",
                return_value="The notes describe a routine inspection.",
            ),
        ):
            first_upload = self.upload(
                "orchid_notes.pdf",
                create_pdf([
                    "Orchid care notes: check soil moisture every Monday.",
                    "Orchid safety notes: inspect the greenhouse exit monthly.",
                ]),
            )
            second_upload = self.upload(
                "bicycle_policy.pdf",
                create_pdf(["Bicycle policy: inspect the outdoor racks every Friday."]),
            )

            self.assertEqual(first_upload.status_code, 200, first_upload.text)
            self.assertEqual(second_upload.status_code, 200, second_upload.text)
            first_document = first_upload.json()
            second_document = second_upload.json()
            self.assertNotEqual(first_document["document_id"], second_document["document_id"])
            self.assertEqual(first_document["page_count"], 2)
            self.assertEqual(first_document["total_chunks"], 2)
            self.assertEqual(second_document["filename"], "bicycle_policy.pdf")
            self.assertTrue(any("Orchid care notes" in text for text in embedded_texts))

            all_results = self.client.post(
                "/api/search",
                json={"query": "Where are the bicycle racks inspected?"},
            )
            selected_results = self.client.post(
                "/api/search",
                json={
                    "query": "What is the greenhouse exit inspection schedule?",
                    "document_ids": [first_document["document_id"]],
                    "top_k": 20,
                },
            )
            self.assertEqual(all_results.status_code, 200, all_results.text)
            self.assertLessEqual(all_results.json()["result_count"], 3)
            self.assertEqual(selected_results.status_code, 200, selected_results.text)
            self.assertEqual(
                {item["filename"] for item in selected_results.json()["results"]},
                {"orchid_notes.pdf"},
            )
            self.assertEqual(
                {item["page_number"] for item in selected_results.json()["results"]},
                {1, 2},
            )

            chat_result = self.client.post(
                "/api/chat",
                json={
                    "question": "When should the greenhouse exit be inspected?",
                    "document_ids": [first_document["document_id"]],
                },
            )
            self.assertEqual(chat_result.status_code, 200, chat_result.text)
            self.assertEqual(
                {source["filename"] for source in chat_result.json()["sources"]},
                {"orchid_notes.pdf"},
            )
            self.assertEqual(
                {source["page_number"] for source in chat_result.json()["sources"]},
                {1, 2},
            )

            delete_result = self.client.delete(
                f"/api/documents/{first_document['document_id']}"
            )
            remaining_documents = self.client.get("/api/documents")
            remaining_search = self.client.post(
                "/api/search",
                json={"query": "Where are the bicycle racks inspected?"},
            )

        self.assertEqual(delete_result.status_code, 200, delete_result.text)
        self.assertEqual(
            [document["document_id"] for document in remaining_documents.json()],
            [second_document["document_id"]],
        )
        self.assertEqual(
            {item["filename"] for item in remaining_search.json()["results"]},
            {"bicycle_policy.pdf"},
        )


if __name__ == "__main__":
    unittest.main()
