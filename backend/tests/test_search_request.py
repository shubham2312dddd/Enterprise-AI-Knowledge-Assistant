import unittest

from pydantic import ValidationError

from backend.main import MultiDocumentSearchRequest, SearchRequest


class SearchRequestTests(unittest.TestCase):
    def test_trims_a_non_empty_query(self) -> None:
        request = SearchRequest(query="  project objective  ")
        self.assertEqual(request.query, "project objective")
        self.assertEqual(request.top_k, 3)

    def test_rejects_empty_queries_and_out_of_range_top_k(self) -> None:
        for values in (
            {"query": "   "},
            {"query": "question", "top_k": 0},
            {"query": "question", "top_k": 21},
        ):
            with self.subTest(values=values):
                with self.assertRaises(ValidationError):
                    SearchRequest(**values)

    def test_search_across_all_documents_is_the_default(self) -> None:
        request = MultiDocumentSearchRequest(query="project objective")
        self.assertIsNone(request.document_ids)

    def test_selected_document_ids_are_trimmed_and_deduplicated(self) -> None:
        request = MultiDocumentSearchRequest(
            query="project objective",
            document_ids=[" doc-a ", "doc-a", "doc-b"],
        )
        self.assertEqual(request.document_ids, ["doc-a", "doc-b"])

    def test_selected_document_ids_cannot_be_empty(self) -> None:
        for document_ids in ([], ["  "]):
            with self.subTest(document_ids=document_ids):
                with self.assertRaises(ValidationError):
                    MultiDocumentSearchRequest(
                        query="project objective",
                        document_ids=document_ids,
                    )


if __name__ == "__main__":
    unittest.main()
