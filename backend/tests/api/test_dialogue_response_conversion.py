import pytest
from fastapi import HTTPException

from src.api.dialogue import _convert_to_message_response
from src.models.dialogue import DialogueAction, DialogueResponse, Phase


@pytest.mark.parametrize(
    "action",
    [
        DialogueAction.ASK_QUESTION,
        DialogueAction.SHOW_SUMMARY,
        DialogueAction.SHOW_PIR,
        DialogueAction.MAX_QUESTIONS,
        DialogueAction.COMPLETE,
    ],
)
def test_convert_to_message_response_keeps_canonical_action(action: DialogueAction):
    response = DialogueResponse(action=action, content="payload")

    converted = _convert_to_message_response(
        response=response,
        stage="gathering",
        phase=Phase.DIRECTION,
    )

    assert converted.question == "payload"
    assert converted.action == action
    assert converted.stage == "gathering"
    assert converted.phase == "direction"
    assert set(converted.model_dump().keys()) == {
        "question",
        "action",
        "stage",
        "phase",
        "sub_state",
        "review_activity",
    }


def test_convert_to_message_response_raises_for_unknown_action():
    response = DialogueResponse(
        action=DialogueAction.ASK_QUESTION,
        content="payload",
    )
    # Assignment is intentionally unchecked in this model; force an invalid runtime value
    # to ensure converter validation fails fast.
    response.action = "invalid_action_name"  # type: ignore[assignment]

    with pytest.raises(HTTPException) as exc_info:
        _convert_to_message_response(
            response=response,
            stage="gathering",
            phase=Phase.DIRECTION,
        )

    assert exc_info.value.status_code == 500
    assert "Internal error: invalid dialogue action" in exc_info.value.detail
