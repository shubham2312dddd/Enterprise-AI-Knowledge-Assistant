import unittest
from unittest.mock import patch

from backend.services.embedding_migration import reembed_existing_documents
from backend.services.embedding_service import EMBEDDING_MODEL, EMBEDDING_PROFILE
from backend.services.vector_store import VectorStoreError


class FakeCollection:
    def __init__(self) -> None:
        self.ids = ["doc-a:0", "doc-b:0"]
        self.documents = ["legacy chunk", "current chunk"]
        self.metadatas = [
            {"document_id": "doc-a", "filename": "a.pdf", "page_number": 1},
            {
                "document_id": "doc-b",
                "filename": "b.pdf",
                "page_number": 2,
                "embedding_model": EMBEDDING_MODEL,
                "embedding_profile": EMBEDDING_PROFILE,
            },
        ]
        self.embeddings = [[0.1, 0.2], [0.8, 0.9]]
        self.fail_next_update = False

    def get(self, include: list[str]) -> dict[str, list]:
        if not {"documents", "metadatas", "embeddings"}.issubset(include):
            raise AssertionError("Migration must read chunk content and rollback data.")
        return {
            "ids": self.ids[:],
            "documents": self.documents[:],
            "metadatas": [metadata.copy() for metadata in self.metadatas],
            "embeddings": self.embeddings[:],
        }

    def update(
        self,
        ids: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, str | int]],
    ) -> None:
        if self.fail_next_update:
            self.fail_next_update = False
            raise ValueError("simulated update failure")
        for chunk_id, embedding, metadata in zip(ids, embeddings, metadatas):
            index = self.ids.index(chunk_id)
            self.embeddings[index] = embedding
            self.metadatas[index] = metadata


class EmbeddingMigrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.collection = FakeCollection()
        self.collection_patch = patch(
            "backend.services.embedding_migration.get_collection",
            return_value=self.collection,
        )
        self.collection_patch.start()
        self.addCleanup(self.collection_patch.stop)

    @patch("backend.services.embedding_migration.embed_documents")
    def test_migrates_only_legacy_vectors_and_preserves_chunk_records(
        self,
        embed_documents: unittest.mock.Mock,
    ) -> None:
        embed_documents.return_value = [[0.3, 0.4]]

        updated_count = reembed_existing_documents()

        self.assertEqual(updated_count, 1)
        embed_documents.assert_called_once_with(["legacy chunk"])
        self.assertEqual(self.collection.ids, ["doc-a:0", "doc-b:0"])
        self.assertEqual(self.collection.documents, ["legacy chunk", "current chunk"])
        self.assertEqual(self.collection.embeddings, [[0.3, 0.4], [0.8, 0.9]])
        self.assertEqual(self.collection.metadatas[0]["embedding_profile"], EMBEDDING_PROFILE)

    @patch("backend.services.embedding_migration.embed_documents")
    def test_does_not_repeat_a_completed_migration(
        self,
        embed_documents: unittest.mock.Mock,
    ) -> None:
        self.collection.metadatas[0].update(
            embedding_model=EMBEDDING_MODEL,
            embedding_profile=EMBEDDING_PROFILE,
        )

        self.assertEqual(reembed_existing_documents(), 0)
        embed_documents.assert_not_called()

    @patch("backend.services.embedding_migration.embed_documents")
    def test_restores_old_vectors_if_migration_update_fails(
        self,
        embed_documents: unittest.mock.Mock,
    ) -> None:
        self.collection.fail_next_update = True
        embed_documents.return_value = [[0.3, 0.4]]

        with self.assertRaises(VectorStoreError):
            reembed_existing_documents()

        self.assertEqual(self.collection.embeddings, [[0.1, 0.2], [0.8, 0.9]])
        self.assertNotIn("embedding_profile", self.collection.metadatas[0])


if __name__ == "__main__":
    unittest.main()
