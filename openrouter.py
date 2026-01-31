"""OpenRouter API client for LLM calls."""

import os
import asyncio
import httpx
import logging
from typing import Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

OPENROUTER_API_URL = "https://openrouter.ai/api/v1"


class OpenRouterError(Exception):
    """OpenRouter API error."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class OpenRouterClient:
    """Client for OpenRouter API."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY not set")

    def _get_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/deliberate-api",
            "X-Title": "Deliberate API",
        }

    async def chat_completion(
        self,
        model: str,
        messages: list[dict[str, Any]],
        system_prompt: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> dict[str, Any]:
        """
        Make a chat completion request.

        Returns dict with:
        - content: str - The response text
        - tokens_used: int - Total tokens used
        """
        # Build messages with system prompt
        all_messages = []
        if system_prompt:
            all_messages.append({"role": "system", "content": system_prompt})
        all_messages.extend(messages)

        body: dict[str, Any] = {
            "model": model,
            "messages": all_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        # Retry with exponential backoff
        max_retries = 3
        last_error = None

        logger.info(f"OpenRouter request: model={model}, messages={len(all_messages)}")

        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{OPENROUTER_API_URL}/chat/completions",
                        headers=self._get_headers(),
                        json=body,
                        timeout=300.0,  # 5 min timeout
                    )

                    if response.status_code == 429:
                        wait_time = 2 ** (attempt + 1)
                        logger.warning(f"Rate limited, waiting {wait_time}s")
                        await asyncio.sleep(wait_time)
                        continue

                    if response.status_code != 200:
                        logger.error(f"OpenRouter error: {response.status_code} - {response.text}")
                        raise OpenRouterError(
                            f"Chat completion failed: {response.text}",
                            response.status_code,
                        )

                    data = response.json()
                    choices = data.get("choices", [])
                    if not choices:
                        raise OpenRouterError("No response choices returned")

                    message = choices[0].get("message", {})
                    content = message.get("content", "") or ""

                    usage = data.get("usage", {})
                    total_tokens = usage.get("total_tokens", 0)

                    logger.info(f"OpenRouter success: {total_tokens} tokens")
                    return {
                        "content": content,
                        "tokens_used": total_tokens,
                    }

            except httpx.TimeoutException:
                logger.warning(f"Timeout (attempt {attempt + 1}/{max_retries})")
                last_error = OpenRouterError(f"Request timed out")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** (attempt + 1))
            except httpx.HTTPError as e:
                logger.error(f"HTTP error: {str(e)}")
                last_error = OpenRouterError(f"HTTP error: {str(e)}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** (attempt + 1))

        raise last_error or OpenRouterError("Unknown error")


# Global client instance
_client: OpenRouterClient | None = None


def get_client() -> OpenRouterClient:
    """Get the global OpenRouter client."""
    global _client
    if _client is None:
        _client = OpenRouterClient()
    return _client
