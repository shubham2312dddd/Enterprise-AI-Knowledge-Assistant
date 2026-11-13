import unittest
from unittest.mock import Mock, patch

import requests

from backend.services.embedding_service import (
    EmbeddingModelUnavailableError,
    EmbeddingServiceError,
    embed_documents,
    embed_query,
    embed_texts,
)


def embedding_response(vectors: list[list[float]]) -> Mock:
    response = Mock()
    response.status_code = 200
    response.json.return_value = {"embeddings": vectors}
    return response


class EmbeddingServiceTests(unittest.TestCase):
    @patch("backend.services.embedding_service.requests.post")
    def test_uses_nomic_document_and_query_task_prefixes(self, post: Mock) -> None:
        post.side_effect = [
            embedding_response([[0.1, 0.2]]),
            embedding_response([[0.3, 0.4]]),
        ]

        embed_documents(["a stored passage"])
        embed_query("a user question")

        self.assertEqual(
            post.call_args_list[0].kwargs["json"]["input"],
            ["search_document: a stored passage"],
        )
        self.assertEqual(
            post.call_args_list[1].kwargs["json"]["input"],
            ["search_query: a user question"],
        )
        self.assertEqual(post.call_args_list[0].kwargs["json"]["model"], "nomic-embed-text")
        self.assertEqual(post.call_args_list[1].kwargs["json"]["model"], "nomic-embed-text")

    @patch("backend.services.embedding_service.requests.post")
    def test_generates_a_fresh_embedding_request_for_each_question(self, post: Mock) -> None:
        post.side_effect = [
            embedding_response([[0.1, 0.2]]),
            embedding_response([[0.8, 0.9]]),
        ]

        first = embed_query("question about members")
        second = embed_query("question about deployment phases")

        self.assertEqual(post.call_count, 2)
        self.assertNotEqual(first, second)
        self.assertEqual(
            [call.kwargs["json"]["input"] for call in post.call_args_list],
            [
                ["search_query: question about members"],
                ["search_query: question about deployment phases"],
            ],
        )

    @patch("backend.services.embedding_service.requests.post")
    def test_batches_inputs_and_validates_embeddings(self, post: Mock) -> None:
        post.side_effect = [
            embedding_response([[0.1, 0.2], [0.3, 0.4]]),
            embedding_response([[0.5, 0.6]]),
        ]

        vectors = embed_texts(["first", "second", "third"], batch_size=2)

        self.assertEqual(len(vectors), 3)
        self.assertEqual(post.call_count, 2)
        self.assertEqual(post.call_args_list[0].kwargs["json"]["input"], ["first", "second"])

    @patch("backend.services.embedding_service.requests.post")
    def test_reports_missing_embedding_model(self, post: Mock) -> None:
        response = Mock(status_code=404)
        post.return_value = response

        with self.assertRaises(EmbeddingModelUnavailableError):
            embed_texts(["text"])

    @patch("backend.services.embedding_service.requests.post")
    def test_reports_ollama_connection_failure_without_internal_details(self, post: Mock) -> None:
        post.side_effect = requests.exceptions.ConnectionError("private connection detail")

        with self.assertRaises(EmbeddingServiceError) as raised:
            embed_texts(["text"])

        self.assertNotIn("private connection detail", str(raised.exception))

    @patch("backend.services.embedding_service.requests.post")
    def test_rejects_mismatched_response_count(self, post: Mock) -> None:
        post.return_value = embedding_response([])

        with self.assertRaises(EmbeddingServiceError):
            embed_texts(["text"])


if __name__ == "__main__":
    unittest.main()
