"""Gemini adapters."""

from adapters.base import BaseCLIAdapter
from adapters.base_http import BaseHTTPAdapter


class GeminiAdapter(BaseCLIAdapter):
    """Adapter for gemini CLI tool (Google AI)."""

    # Gemini API limits (conservative estimates based on production errors)
    # Gemini API rejects prompts around 30k+ tokens
    # Use 100k characters as safe threshold (~25k tokens at 4 chars/token)
    # This prevents "invalid argument" API errors seen in production
    MAX_PROMPT_CHARS = 100000

    def __init__(
        self,
        command: str = "gemini",
        args: list[str] | None = None,
        timeout: int = 60,
        default_reasoning_effort: str | None = None,
    ):
        """
        Initialize Gemini adapter.

        Args:
            command: Command to execute (default: "gemini")
            args: List of argument templates (from config.yaml)
            timeout: Timeout in seconds (default: 60)
            default_reasoning_effort: Ignored (Gemini doesn't support reasoning effort)

        Note:
            The gemini CLI uses `gemini -p "prompt"` or `gemini -m model -p "prompt"` syntax.
        """
        if args is None:
            raise ValueError("args must be provided from config.yaml")
        super().__init__(
            command=command,
            args=args,
            timeout=timeout,
            default_reasoning_effort=default_reasoning_effort,
        )

    def validate_prompt_length(self, prompt: str) -> bool:
        """
        Validate that prompt length is within Gemini API limits.

        Args:
            prompt: The prompt text to validate

        Returns:
            True if prompt is valid length, False if too long
        """
        return len(prompt) <= self.MAX_PROMPT_CHARS

    def _format_prompt_for_args(self, full_prompt: str) -> str:
        """
        Keep Gemini in headless prompt mode while moving large prompt content
        off the Windows command line.

        The Gemini CLI appends stdin content to the `-p/--prompt` value, so a
        minimal placeholder is sufficient here.
        """
        return ""

    def _build_stdin_input(self, full_prompt: str) -> bytes | None:
        """
        Send the actual prompt over stdin to avoid Windows command-line length
        limits for large deliberation dossiers.
        """
        return full_prompt.encode("utf-8")

    def parse_output(self, raw_output: str) -> str:
        """
        Parse gemini output.

        Gemini outputs clean responses without header/footer text,
        so we simply strip whitespace.

        Args:
            raw_output: Raw stdout from gemini

        Returns:
            Parsed model response
        """
        return raw_output.strip()


class GeminiAPIAdapter(BaseHTTPAdapter):
    """HTTP adapter for the Gemini Developer API.

    The Docker council server should not depend on the host-level `gemini` CLI
    being installed. This adapter uses the same GEMINI_API_KEY-backed HTTP API
    as the rest of the app while preserving the council participant adapter name
    (`gemini`).
    """

    provider_name = "Gemini API"

    def build_request(self, model: str, prompt: str):
        endpoint = f"/models/{model}:generateContent"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["x-goog-api-key"] = self.api_key

        body = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}],
                }
            ]
        }
        return endpoint, headers, body

    def parse_response(self, response_json: dict) -> str:
        candidates = response_json.get("candidates") or []
        if not candidates:
            prompt_feedback = response_json.get("promptFeedback")
            raise ValueError(
                f"{self.provider_name} response has no candidates"
                + (f": {prompt_feedback}" if prompt_feedback else "")
            )

        content = candidates[0].get("content") or {}
        parts = content.get("parts") or []
        text_parts = [part.get("text", "") for part in parts if isinstance(part, dict)]
        text = "\n".join(part for part in text_parts if part).strip()
        if not text:
            finish_reason = candidates[0].get("finishReason", "unknown")
            raise ValueError(
                f"{self.provider_name} returned empty content "
                f"(finishReason={finish_reason})"
            )
        return text
