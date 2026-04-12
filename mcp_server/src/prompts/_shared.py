"""Shared helpers used across all prompt modules."""

# Maps BCP-47 language codes to human-readable names used in language instructions.
_LANGUAGE_NAMES: dict[str, str] = {
    "en": "English",
    "no": "Norwegian",
}

# Maps human-readable source names (as shown in the UI) to their MCP tool names.
SOURCE_TOOL_MAP: dict[str, list[str]] = {
    "Internal Knowledge Bank": ["list_knowledge_base", "read_knowledge_base"],
    "AlienVault OTX": ["query_otx"],
    # "MISP": ["search_misp"],  # MISP not configured on external server
    "Uploaded Documents": ["list_uploads", "search_local_data", "read_upload"],
    "Web Search": ["google_search"],
}


def _language_instruction(language: str, scope: str = "all output") -> str:
    """Return a standardised language instruction line for prepending to prompts.

    Args:
        language: BCP-47 language code, e.g. "en" or "no".
        scope: Human-readable description of what must be in that language.

    Returns:
        A single instruction line ready to prepend to the prompt.
    """
    language_name = _LANGUAGE_NAMES.get(language, "English")
    return f"LANGUAGE INSTRUCTION: You MUST write {scope} in {language_name}.\n\n"
