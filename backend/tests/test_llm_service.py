import json
import unittest
from unittest.mock import Mock, patch

import requests

from backend.services.llm_service import (
    CHAT_MODEL,
    CHAT_NUM_CTX,
    ChatModelUnavailableError,
    OllamaChatError,
    OllamaChatResponseError,
    OllamaChatTimeoutError,
    generate_grounded_answer,
)


def chat_response(content: str, status_code: int = 200) -> Mock:
    response = Mock()
    response.status_code = status_code
    response.json.return_value = {"message": {"content": content}}
    return response


class OllamaChatServiceTests(unittest.TestCase):
    def test_uses_qwen_as_the_configured_chat_model(self) -> None:
        self.assertEqual(CHAT_MODEL, "qwen2.5:1.5b-instruct")

    @patch("backend.services.llm_service.requests.post")
    def test_sends_bounded_low_temperature_chat_request(self, post: Mock) -> None:
        post.return_value = chat_response(json.dumps({"answer": "The answer is in the source."}))
        messages = [{"role": "system", "content": "Use context."}]

        answer = generate_grounded_answer(messages)

        self.assertEqual(answer, "The answer is in the source.")
        request = post.call_args
        payload = request.kwargs["json"]
        self.assertEqual(payload["model"], CHAT_MODEL)
        self.assertEqual(payload["messages"], messages)
        self.assertFalse(payload["stream"])
        self.assertEqual(payload["options"]["temperature"], 0.1)
        self.assertEqual(payload["options"]["num_ctx"], CHAT_NUM_CTX)
        self.assertLessEqual(payload["options"]["num_ctx"], 4096)
        self.assertEqual(request.kwargs["timeout"], 120)

    @patch("backend.services.llm_service.requests.post")
    def test_reports_missing_chat_model(self, post: Mock) -> None:
        post.return_value = chat_response("", status_code=404)

        with self.assertRaises(ChatModelUnavailableError):
            generate_grounded_answer([])

    @patch("backend.services.llm_service.requests.post")
    def test_reports_ollama_connection_failure_without_internal_details(self, post: Mock) -> None:
        post.side_effect = requests.exceptions.ConnectionError("private connection detail")

        with self.assertRaises(OllamaChatError) as raised:
            generate_grounded_answer([])

        self.assertNotIn("private connection detail", str(raised.exception))

    @patch("backend.services.llm_service.requests.post")
    def test_reports_model_timeout_without_internal_details(self, post: Mock) -> None:
        post.side_effect = requests.exceptions.Timeout("private timeout detail")

        with self.assertRaises(OllamaChatTimeoutError) as raised:
            generate_grounded_answer([])

        self.assertNotIn("private timeout detail", str(raised.exception))

    @patch("backend.services.llm_service.requests.post")
    def test_rejects_empty_or_invalid_model_responses(self, post: Mock) -> None:
        for content in ("", "not-json", '{"answer": "  "}'):
            with self.subTest(content=content):
                post.return_value = chat_response(content)
                with self.assertRaises(OllamaChatResponseError):
                    generate_grounded_answer([])


if __name__ == "__main__":
    unittest.main()
