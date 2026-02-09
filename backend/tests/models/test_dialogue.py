from src.models.dialogue import ClarifyingQuestion


def test_clarifying_question_creation():
    question = ClarifyingQuestion(
        question_text="What is the scope of your investigation?",
        question_type="scope"
    )

    assert question.question_text == "What is the scope of your investigation?"
    assert question.question_type == "scope"
    assert question.is_final is False  # Default value


def test_clarifying_question_with_is_final_true():
    question = ClarifyingQuestion(
        question_text="I have enough information. Ready to proceed?",
        question_type="confirmation",
        is_final=True
    )

    assert question.is_final is True
