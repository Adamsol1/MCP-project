"""
TDD tests for Knowledge Bank injection into PIR generation.

What we are testing:
  - DialogueService.generate_pir() calls KnowledgeService with a scan text
    built from the dialogue context fields
  - Matched file contents are read from disk and formatted with source labels
    so the AI knows exactly where each piece of background information comes from
    and can cite it in the PIR JSON output
  - The formatted background_knowledge string is passed to the MCP call_tool
  - Missing files are skipped gracefully without crashing
  - When nothing matches, the MCP call proceeds without background_knowledge
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.services.dialogue_service import DialogueService
from src.models.dialogue import DialogueContext


# ── Helper ───────────────────────────────────────────────────────────────────

def _get_bg(mock_mcp_client) -> str | None:
    """Extract background_knowledge from the last call_tool invocation."""
    call_kwargs = mock_mcp_client.call_tool.call_args[0][1]
    return call_kwargs.get("background_knowledge")


# ── Shared fixtures ─────────────────────────────────────────────────────────

@pytest.fixture
def mock_mcp_client():
    """Async-capable mock of MCPClient. call_tool returns a plain PIR string."""
    client = MagicMock()
    client.call_tool = AsyncMock(return_value="Generated PIR content")
    return client


@pytest.fixture
def context():
    """A fully-populated DialogueContext — enough to trigger knowledge matching."""
    ctx = DialogueContext()
    ctx.scope = "Norwegian energy infrastructure vulnerability assessment"
    ctx.timeframe = "Last 90 days"
    ctx.target_entities = ["Equinor", "Kårstø gas terminal"]
    ctx.threat_actors = ["Russian GRU", "APT28"]
    ctx.priority_focus = "Sabotage and disruption risk"
    return ctx


@pytest.fixture
def knowledge_files(tmp_path):
    """
    Creates a real (temporary) knowledge bank directory tree with two files.
    tmp_path is a built-in pytest fixture: a real temp dir, cleaned up after each test.
    """
    geo_dir = tmp_path / "knowledge_bank" / "geopolitical"
    geo_dir.mkdir(parents=True)
    (geo_dir / "norway_russia.md").write_text(
        "# Norway-Russia Relations\nKey strategic context here.", encoding="utf-8"
    )
    threat_dir = tmp_path / "knowledge_bank" / "threat_actors"
    threat_dir.mkdir(parents=True)
    (threat_dir / "russian_state.md").write_text(
        "# Russian State Actors\nAPT28 known TTPs.", encoding="utf-8"
    )
    return tmp_path


# ── Group 1: No knowledge service configured ────────────────────────────────

@pytest.mark.asyncio
async def test_generate_pir_without_knowledge_service_omits_background(mock_mcp_client, context):
    """
    When no KnowledgeService is injected, generate_pir must still work and
    must NOT pass a background_knowledge key to call_tool.
    """
    service = DialogueService(mock_mcp_client, None)
    await service.generate_pir(context)

    assert _get_bg(mock_mcp_client) is None  # key absent = no background injected


# ── Group 2: Knowledge service returns no matches ───────────────────────────

@pytest.mark.asyncio
async def test_no_matching_resources_passes_none_background(
    mock_mcp_client, context, tmp_path
):
    """
    When KnowledgeService returns [], background_knowledge must be None
    so the MCP prompt is not polluted with an empty section.
    """
    knowledge_service = MagicMock()
    knowledge_service.get_relevant_resources.return_value = []

    service = DialogueService(
        mock_mcp_client, None,
        knowledge_service=knowledge_service,
        knowledge_base_path=tmp_path,
    )
    await service.generate_pir(context)

    assert _get_bg(mock_mcp_client) is None


# ── Group 3: KnowledgeService receives the right scan text ──────────────────

@pytest.mark.asyncio
async def test_knowledge_service_receives_scan_text_from_context(
    mock_mcp_client, context, tmp_path
):
    """
    get_relevant_resources must be called with a string derived from the
    context fields. Scope, threat_actors, and priority_focus must all appear
    so that relevant files are triggered by the keyword matching.
    """
    knowledge_service = MagicMock()
    knowledge_service.get_relevant_resources.return_value = []

    service = DialogueService(
        mock_mcp_client, None,
        knowledge_service=knowledge_service,
        knowledge_base_path=tmp_path,
    )
    await service.generate_pir(context)

    scan_text = knowledge_service.get_relevant_resources.call_args[0][0]
    assert "Norwegian energy infrastructure" in scan_text
    assert "APT28" in scan_text
    assert "Sabotage" in scan_text


# ── Group 4: File contents and source attribution ───────────────────────────

@pytest.mark.asyncio
async def test_background_knowledge_starts_with_correct_header(
    mock_mcp_client, context, knowledge_files
):
    """
    The injected string must open with '## Background Knowledge' so the MCP
    prompt template renders it as a clearly labelled section.
    """
    knowledge_service = MagicMock()
    knowledge_service.get_relevant_resources.return_value = [
        "knowledge_bank/geopolitical/norway_russia.md",
    ]

    service = DialogueService(
        mock_mcp_client, None,
        knowledge_service=knowledge_service,
        knowledge_base_path=knowledge_files,
    )
    await service.generate_pir(context)

    bg = _get_bg(mock_mcp_client)
    assert bg is not None
    assert bg.startswith("## Background Knowledge")


@pytest.mark.asyncio
async def test_each_source_is_labeled_with_its_file_path(
    mock_mcp_client, context, knowledge_files
):
    """
    Each file's content must be preceded by a label that includes its file path.
    This lets the AI cite the exact source in its PIR JSON output and justify
    claims with a specific reference — the core goal of the Knowledge Bank.
    """
    knowledge_service = MagicMock()
    knowledge_service.get_relevant_resources.return_value = [
        "knowledge_bank/geopolitical/norway_russia.md",
    ]

    service = DialogueService(
        mock_mcp_client, None,
        knowledge_service=knowledge_service,
        knowledge_base_path=knowledge_files,
    )
    await service.generate_pir(context)

    bg = _get_bg(mock_mcp_client)
    assert bg is not None
    assert "norway_russia.md" in bg          # source path must appear as a label
    assert "Norway-Russia Relations" in bg   # content must follow the label


@pytest.mark.asyncio
async def test_multiple_sources_each_labeled_individually(
    mock_mcp_client, context, knowledge_files
):
    """
    When multiple files match, every file gets its own source label and content
    block. The AI must be able to distinguish which claim comes from which file.
    """
    knowledge_service = MagicMock()
    knowledge_service.get_relevant_resources.return_value = [
        "knowledge_bank/geopolitical/norway_russia.md",
        "knowledge_bank/threat_actors/russian_state.md",
    ]

    service = DialogueService(
        mock_mcp_client, None,
        knowledge_service=knowledge_service,
        knowledge_base_path=knowledge_files,
    )
    await service.generate_pir(context)

    bg = _get_bg(mock_mcp_client)
    assert bg is not None
    assert "norway_russia.md" in bg
    assert "Norway-Russia Relations" in bg
    assert "russian_state.md" in bg
    assert "Russian State Actors" in bg


# ── Group 5: Missing file handling ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_missing_file_is_skipped_and_pir_still_generated(
    mock_mcp_client, context, tmp_path
):
    """
    If a matched path does not exist on disk the call must NOT raise.
    PIR generation continues — a missing KB file is not a fatal error.
    """
    knowledge_service = MagicMock()
    knowledge_service.get_relevant_resources.return_value = [
        "knowledge_bank/geopolitical/does_not_exist.md",
    ]

    service = DialogueService(
        mock_mcp_client, None,
        knowledge_service=knowledge_service,
        knowledge_base_path=tmp_path,
    )

    await service.generate_pir(context)  # must not raise
    assert mock_mcp_client.call_tool.called


@pytest.mark.asyncio
async def test_one_valid_one_missing_injects_only_valid(
    mock_mcp_client, context, knowledge_files
):
    """
    When one file exists and one is missing, only the existing file's content
    and label appear in background_knowledge. The missing one is fully skipped.
    """
    knowledge_service = MagicMock()
    knowledge_service.get_relevant_resources.return_value = [
        "knowledge_bank/geopolitical/norway_russia.md",
        "knowledge_bank/geopolitical/does_not_exist.md",
    ]

    service = DialogueService(
        mock_mcp_client, None,
        knowledge_service=knowledge_service,
        knowledge_base_path=knowledge_files,
    )
    await service.generate_pir(context)

    bg = _get_bg(mock_mcp_client)
    assert bg is not None
    assert "Norway-Russia Relations" in bg
    assert "does_not_exist.md" not in bg
