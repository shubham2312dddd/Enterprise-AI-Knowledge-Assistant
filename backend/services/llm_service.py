import json
import math
import os
from collections.abc import Mapping
from typing import Any

import requests

from backend.services.embedding_service import OLLAMA_BASE_URL


CHAT_MODEL = os.getenv("OLLAMA_CHAT_MODEL", "qwen2.5:1.5b-instruct")
CHAT_TIMEOUT_SECONDS = float(os.getenv("OLLAMA_CHAT_TIMEOUT", "120"))
CHAT_NUM_CTX = 4096
CHAT_NUM_PREDICT = 256
CHAT_RESPONSE_FORMAT: dict[str, Any] = {
    "type": "object",
    "properties": {"answer": {"type": "string", "minLength": 1, "maxLength": 600}},
    "required": ["answer"],
    "additionalProperties": False,
}

if not math.isfinite(CHAT_TIMEOUT_SECONDS) or CHAT_TIMEOUT_SECONDS <= 0:
    raise ValueError("OLLAMA_CHAT_TIMEOUT must be a positive number of seconds.")


class OllamaChatError(RuntimeError):
    """Raised when Ollama cannot return a usable chat response."""


class ChatModelUnavailableError(OllamaChatError):
    """Raised when the configured chat model is missing from Ollama."""


class OllamaChatTimeoutError(OllamaChatError):
    """Raised when the local chat model exceeds its configured timeout."""


class OllamaChatResponseError(OllamaChatError):
    """Raised when Ollama returns an invalid chat response."""


def generate_grounded_answer(messages: list[dict[str, str]]) -> str:
    try:
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json={
                "model": CHAT_MODEL,
                "messages": messages,
                "stream": False,
                "format": CHAT_RESPONSE_FORMAT,
                "options": {
                    "temperature": 0.1,
                    "num_ctx": CHAT_NUM_CTX,
                    "num_predict": CHAT_NUM_PREDICT,
                },
                "keep_alive": "2m",
            },
            timeout=CHAT_TIMEOUT_SECONDS,
        )
    except requests.exceptions.Timeout as error:
        raise OllamaChatTimeoutError(
            "The local AI model took too long to respond. Try again with a shorter question."
        ) from error
    except requests.exceptions.ConnectionError as error:
        raise OllamaChatError(
            "The local Ollama service is unavailable. Start Ollama and try again."
        ) from error
    except requests.exceptions.RequestException as error:
        raise OllamaChatError("The local AI service could not process the request.") from error

    if response.status_code == 404:
        raise ChatModelUnavailableError(
            f"The Ollama chat model '{CHAT_MODEL}' is not installed."
        )
    if not 200 <= response.status_code < 300:
        raise OllamaChatError("The local AI service returned an unsuccessful response.")

    try:
        payload = response.json()
    except ValueError as error:
        raise OllamaChatResponseError(
            "The local AI service returned an invalid response."
        ) from error

    message = payload.get("message") if isinstance(payload, Mapping) else None
    content = message.get("content") if isinstance(message, Mapping) else None
    if not isinstance(content, str) or not content.strip():
        raise OllamaChatResponseError("The local AI service returned an empty response.")

    try:
        result = json.loads(content)
    except json.JSONDecodeError as error:
        raise OllamaChatResponseError(
            "The local AI service returned an invalid answer format."
        ) from error

    answer = result.get("answer") if isinstance(result, Mapping) else None
    if not isinstance(answer, str) or not answer.strip():
        raise OllamaChatResponseError(
            "The local AI service returned an empty or invalid answer."
        )

    return answer.strip()
