import unittest
from unittest.mock import Mock, patch

from backend.services.document_indexer import NoIndexableTextError, index_document
from backend.services.embedding_service import EmbeddingServiceError


class DocumentIndexerTests(unittest.TestCase):
    @patch("backend.services.document_indexer.store_document_chunks")
    @patch("backend.services.document_indexer.embed_documents")
    def test_embedding_failure_does_not_store_document(
        self,
        embed_documents: Mock,
        store_document_chunks: Mock,
    ) -> None:
        embed_documents.side_effect = EmbeddingServiceError("Ollama unavailable.")

        with self.assertRaises(EmbeddingServiceError):
            index_document(
                "sample.pdf",
                [{"page_number": 1, "text": "Text to index."}],
            )

        store_document_chunks.assert_not_called()

    @patch("backend.services.document_indexer.embed_documents")
    def test_document_with_only_empty_pages_is_not_indexed(self, embed_documents: Mock) -> None:
        with self.assertRaises(NoIndexableTextError):
            index_document("empty-text.pdf", [{"page_number": 1, "text": " \n"}])

        embed_documents.assert_not_called()


if __name__ == "__main__":
    unittest.main()
