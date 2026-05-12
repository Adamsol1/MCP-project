"""Tests for MCP response-size limiting."""

from models.schema import DeliberationResult, RoundResponse, Summary
from server import _limit_full_debate_rounds


def _result_with_rounds(rounds: int, participants: int) -> DeliberationResult:
    return DeliberationResult(
        status="complete",
        mode="conference",
        rounds_completed=rounds,
        participants=[f"Analyst {i}" for i in range(1, participants + 1)],
        summary=Summary(
            consensus="Consensus.",
            key_agreements=[],
            key_disagreements=[],
            final_recommendation="Recommendation.",
        ),
        transcript_path="transcripts/demo.md",
        full_debate=[
            RoundResponse(
                round=round_number,
                participant=f"Analyst {participant_number}",
                response=f"Round {round_number} response {participant_number}",
                timestamp="2026-05-12T00:00:00",
            )
            for round_number in range(1, rounds + 1)
            for participant_number in range(1, participants + 1)
        ],
    )


def test_full_debate_limit_uses_rounds_not_entry_count():
    result = _result_with_rounds(rounds=2, participants=3)

    payload = _limit_full_debate_rounds(result, max_rounds=3)

    assert payload["full_debate_truncated"] is False
    assert payload["total_rounds"] == 2
    assert len(payload["full_debate"]) == 6


def test_full_debate_limit_keeps_all_participants_for_included_rounds():
    result = _result_with_rounds(rounds=5, participants=3)

    payload = _limit_full_debate_rounds(result, max_rounds=2)

    assert payload["full_debate_truncated"] is True
    assert payload["total_rounds"] == 5
    assert {entry["round"] for entry in payload["full_debate"]} == {4, 5}
    assert len(payload["full_debate"]) == 6
