import unittest
from math import sqrt
from typing import Any
from unittest.mock import patch

from backend.services.vector_store import (
    DocumentAlreadyExistsError,
    DocumentNotFoundError,
    VectorStoreError,
    delete_document_chunks,
    list_indexed_documents,
    search_document_chunks,
    store_document_chunks,
)


class FakeCollection:
    def __init__(self) -> None:
        self.records: dict[str, dict[str, Any]] = {}
        self.fail_after_one_add = False

    def get(
        self,
        *,
        where: dict[str, Any] | None = None,
        limit: int | None = None,
        include: list[str],
    ) -> dict[str, list[Any]]:
        if "metadatas" not in include:
            raise AssertionError("The vector store must request chunk metadata.")
        matching = [
            (chunk_id, record)
            for chunk_id, record in self.records.items()
            if self._matches(record["metadata"], where)
        ]
        if limit is not None:
            matching = matching[:limit]
        return {
            "ids": [chunk_id for chunk_id, _ in matching],
            "metadatas": [record["metadata"] for _, record in matching],
        }

    def add(
        self,
        ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: list[dict[str, Any]],
    ) -> None:
        for index, (chunk_id, embedding, text, metadata) in enumerate(
            zip(ids, embeddings, documents, metadatas)
        ):
            self.records[chunk_id] = {
                "embedding": embedding,
                "text": text,
                "metadata": metadata,
            }
            if self.fail_after_one_add and index == 0:
                raise ValueError("simulated write failure")

    def delete(self, where: dict[str, str]) -> None:
        self.records = {
            chunk_id: record
            for chunk_id, record in self.records.items()
            if not self._matches(record["metadata"], where)
        }

    def query(
        self,
        *,
        query_embeddings: list[list[float]],
        n_results: int,
        where: dict[str, Any] | None = None,
        include: list[str],
    ) -> dict[str, list[list[Any]]]:
        if not query_embeddings or not query_embeddings[0]:
            raise AssertionError("The vector store must provide a query embedding.")
        if not {"documents", "metadatas", "distances"}.issubset(include):
            raise AssertionError("The vector store must request searchable result fields.")
        query_embedding = query_embeddings[0]
        matching = [
            (
                self._cosine_distance(query_embedding, record["embedding"]),
                chunk_id,
                record,
            )
            for chunk_id, record in self.records.items()
            if self._matches(record["metadata"], where)
        ]
        matching.sort(key=lambda result: result[0])
        matching = matching[:n_results]
        return {
            "ids": [[chunk_id for _, chunk_id, _ in matching]],
            "documents": [[record["text"] for _, _, record in matching]],
            "metadatas": [[record["metadata"] for _, _, record in matching]],
            "distances": [[distance for distance, _, _ in matching]],
        }

    @staticmethod
    def _matches(metadata: dict[str, Any], where: dict[str, Any] | None) -> bool:
        if where is None:
            return True
        selected = where["document_id"]
        if isinstance(selected, dict):
            return metadata["document_id"] in selected["$in"]
        return metadata["document_id"] == selected

    @staticmethod
    def _cosine_distance(left: list[float], right: list[float]) -> float:
        dot = sum(a * b for a, b in zip(left, right))
        left_norm = sqrt(sum(value * value for value in left))
        right_norm = sqrt(sum(value * value for value in right))
        return 1 - dot / (left_norm * right_norm)


class VectorStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.collection = FakeCollection()
        self.collection_patch = patch(
            "backend.services.vector_store.get_collection",
            return_value=self.collection,
        )
        self.collection_patch.start()
        self.addCleanup(self.collection_patch.stop)

    def test_persists_metadata_and_searches_only_the_requested_document(self) -> None:
        store_document_chunks(
            "doc-a",
            "a.pdf",
            [{"chunk_index": 0, "page_number": 4, "text": "alpha passage"}],
            [[0.1, 0.2]],
        )
        store_document_chunks(
            "doc-b",
            "b.pdf",
            [{"chunk_index": 0, "page_number": 9, "text": "beta passage"}],
            [[0.8, 0.9]],
        )

        results = search_document_chunks(
            "doc-a",
            [0.2, 0.3],
            top_k=5,
            include_document_id=True,
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["filename"], "a.pdf")
        self.assertEqual(results[0]["document_id"], "doc-a")
        self.assertEqual(results[0]["page_number"], 4)
        self.assertEqual(results[0]["text"], "alpha passage")
        self.assertLess(results[0]["distance"], 0.1)

    def test_existing_search_response_omits_document_id_by_default(self) -> None:
        store_document_chunks(
            "doc-a",
            "a.pdf",
            [{"chunk_index": 0, "page_number": 1, "text": "alpha passage"}],
            [[1.0, 0.0]],
        )

        results = search_document_chunks("doc-a", [1.0, 0.0], top_k=5)

        self.assertNotIn("document_id", results[0])

    def test_unknown_document_is_not_found(self) -> None:
        with self.assertRaises(DocumentNotFoundError):
            search_document_chunks("missing", [0.1, 0.2], top_k=5)

    def test_existing_document_id_is_not_overwritten(self) -> None:
        store_document_chunks(
            "doc-a",
            "a.pdf",
            [{"chunk_index": 0, "page_number": 1, "text": "original"}],
            [[0.1, 0.2]],
        )

        with self.assertRaises(DocumentAlreadyExistsError):
            store_document_chunks(
                "doc-a",
                "other.pdf",
                [{"chunk_index": 0, "page_number": 1, "text": "replacement"}],
                [[0.3, 0.4]],
            )

        self.assertEqual(self.collection.records["doc-a:0"]["text"], "original")

    def test_partial_write_is_rolled_back(self) -> None:
        self.collection.fail_after_one_add = True
        with self.assertRaises(VectorStoreError):
            store_document_chunks(
                "doc-a",
                "a.pdf",
                [
                    {"chunk_index": 0, "page_number": 1, "text": "first"},
                    {"chunk_index": 1, "page_number": 1, "text": "second"},
                ],
                [[0.1, 0.2], [0.3, 0.4]],
            )

        self.assertEqual(self.collection.records, {})

    def test_different_query_embeddings_can_return_different_chunks(self) -> None:
        store_document_chunks(
            "doc-a",
            "a.pdf",
            [{"chunk_index": 0, "page_number": 1, "text": "alpha passage"}],
            [[1.0, 0.0]],
        )
        store_document_chunks(
            "doc-b",
            "b.pdf",
            [{"chunk_index": 0, "page_number": 2, "text": "beta passage"}],
            [[0.0, 1.0]],
        )

        alpha_results = search_document_chunks(None, [1.0, 0.0], top_k=2)
        beta_results = search_document_chunks(None, [0.0, 1.0], top_k=2)

        self.assertEqual(alpha_results[0]["text"], "alpha passage")
        self.assertEqual(beta_results[0]["text"], "beta passage")
        self.assertNotEqual(alpha_results[0]["chunk_id"], beta_results[0]["chunk_id"])

    def test_multi_document_filter_and_document_listing_are_isolated(self) -> None:
        store_document_chunks(
            "doc-a",
            "a.pdf",
            [{"chunk_index": 0, "page_number": 1, "text": "alpha passage"}],
            [[1.0, 0.0]],
            total_pages=2,
            extracted_characters=14,
        )
        store_document_chunks(
            "doc-b",
            "b.pdf",
            [{"chunk_index": 0, "page_number": 3, "text": "beta passage"}],
            [[0.0, 1.0]],
        )

        results = search_document_chunks(
            None,
            [0.0, 1.0],
            top_k=5,
            document_ids=["doc-a"],
        )
        documents = list_indexed_documents()

        self.assertEqual([result["filename"] for result in results], ["a.pdf"])
        self.assertEqual(len(documents), 2)
        alpha = next(document for document in documents if document["document_id"] == "doc-a")
        self.assertEqual(alpha["total_pages"], 2)
        self.assertEqual(alpha["extracted_characters"], 14)

    def test_deleting_one_document_preserves_other_documents(self) -> None:
        for document_id, filename in (("doc-a", "a.pdf"), ("doc-b", "b.pdf")):
            store_document_chunks(
                document_id,
                filename,
                [{"chunk_index": 0, "page_number": 1, "text": filename}],
                [[1.0, 0.0]],
            )

        delete_document_chunks("doc-a")

        self.assertEqual(
            [document["document_id"] for document in list_indexed_documents()],
            ["doc-b"],
        )


if __name__ == "__main__":
    unittest.main()
