
#Dialogue_question integration tests

import json
import time

import pytest

from src.server import dialogue_question, generate_pir


@pytest.fixture(autouse=True)
def rate_limit_pause():
    yield
    time.sleep(13)


FULL_CONTEXT = {
    "scope": "identify attack patterns against critical infrastructure",
    "timeframe": "last 6 months",
    "target_entities": ["Norway", "NATO member states"],
    "threat_actors": ["APT29"],
    "priority_focus": "attack vectors",
    "perspectives": ["neutral"],
}

EMPTY_CONTEXT = {
    "scope": "",
    "timeframe": "",
    "target_entities": [],
    "threat_actors": [],
    "priority_focus": "",
    "perspectives": [],
}


@pytest.mark.integration
class TestDialogueQuestion:
  #test for checking if ai response has required fields
  def test_returns_required_fields(self):
    #Call the method with fastMCP
    result = dialogue_question.fn(
      user_message="Investigate APT29 attacks against NATO",
        missing_fields=["scope", "timeframe"],
        perspectives=["neutral"],
        context=EMPTY_CONTEXT,
    )
    #Checks if response contains the required fields
    assert "question" in result
    assert "type" in result
    assert "has_sufficient_context" in result
    assert "context" in result

  def test_has_sufficient_context_is_false_when_missing_fields(self):
    #Call the method
    result = dialogue_question.fn(
        user_message="Investigate APT29 attacks against NATO",
        missing_fields=["scope", "timeframe"],
        perspectives=["neutral"],
        context=EMPTY_CONTEXT,
    )

    #Check the response. Should return False.
    assert not result["has_sufficient_context"]

  def test_has_sufficient_context_is_true_when_no_missing_fields(self):
    #Call the method
    result = dialogue_question.fn(
        user_message="Investigate APT29 attacks against NATO",
        missing_fields=[],
        perspectives=["neutral"],
        context=FULL_CONTEXT,
    )
    #Should return true
    assert result["has_sufficient_context"]

  #test for checking if AI correctly extracts fields.
  #NB! This test may be unreliable since AI output is non-deterministic.
  def test_extracts_threat_actor_from_user_message(self):
    #Call method
    result = dialogue_question.fn(
      user_message="Investigate APT29 attacks against NATO",
        missing_fields=[],
        perspectives=["neutral"],
        context=EMPTY_CONTEXT,
    )

    #threat_actors is a list, so we normalize each entry
    normalized = [a.lower().strip() for a in result["context"]["threat_actors"]]
    assert "apt29" in normalized

  #test for checking that the AI does not stop when user sends a vague answer. e.g (initial query = "hallo")
  def test_vague_message_returns_question(self):
    result = dialogue_question.fn(
        user_message="hallo",
        missing_fields=["scope", "timeframe", "target_entities", "threat_actors", "priority_focus"],
        perspectives=["neutral"],
        context=EMPTY_CONTEXT,
    )

    #Should still return a valid, non-empty question
    assert result["question"]
    assert isinstance(result["question"], str)
    assert len(result["question"]) > 5

  #test for checking that norwegian input is handled correctly
  def test_norwegian_input_returns_valid_question(self):
    result = dialogue_question.fn(
        user_message="Undersøk APT29 sine angrep mot norsk kritisk infrastruktur",
        missing_fields=["scope", "timeframe"],
        perspectives=["neutral"],
        context=EMPTY_CONTEXT,
    )

    #Should return a valid question without errors
    assert result["question"]
    assert isinstance(result["question"], str)


@pytest.mark.integration
class TestGeneratePir:
  #test for checking if generate_pir returns valid json with required fields
  def test_pir_valid_json_structure(self):
    result = generate_pir.fn(
        scope="identify attack patterns against critical infrastructure",
        timeframe="last 6 months",
        target_entities=["Norway"],
        perspectives=["neutral"],
        threat_actors=["APT29"],
        priority_focus="attack vectors",
    )

    #Result should be valid JSON
    parsed = json.loads(result)
    assert "result" in parsed
    assert "pirs" in parsed
    assert "reasoning" in parsed

  #test for checking that pirs list is not empty and contains required fields
  def test_pir_list_not_empty(self):
    result = generate_pir.fn(
        scope="identify attack patterns against critical infrastructure",
        timeframe="last 6 months",
        target_entities=["Norway"],
        perspectives=["neutral"],
        threat_actors=["APT29"],
        priority_focus="attack vectors",
    )

    parsed = json.loads(result)
    assert len(parsed["pirs"]) >= 1

    #Each PIR should have the required fields
    for pir in parsed["pirs"]:
      assert "question" in pir
      assert "priority" in pir
      assert "rationale" in pir

  #test for checking that modifications changes the content of the PIR
  #NB! This test may be unreliable since AI output is non-deterministic.
  def test_modifications_changes_content(self):
    #Generate initial PIR
    original = generate_pir.fn(
        scope="identify attack patterns against critical infrastructure",
        timeframe="last 6 months",
        target_entities=["Norway"],
        perspectives=["neutral"],
        threat_actors=["APT29"],
        priority_focus="attack vectors",
    )

    #Regenerate with modifications
    modified = generate_pir.fn(
        scope="identify attack patterns against critical infrastructure",
        timeframe="last 6 months",
        target_entities=["Norway"],
        perspectives=["neutral"],
        threat_actors=["APT29"],
        priority_focus="attack vectors",
        modifications="Focus only on ransomware attacks, remove APT29",
    )

    time.sleep(13)  # extra pause between the two API calls in this test
    assert "apt29" in original.lower()
    assert original != modified
    #Modified result should mention ransomware and not APT29
    assert "ransomware" in modified.lower()
    assert "apt29" not in modified.lower()

  #test for checking that empty perspectives list does not crash
  def test_empty_perspectives_does_not_crash(self):
    result = generate_pir.fn(
        scope="identify attack patterns against critical infrastructure",
        timeframe="last 6 months",
        target_entities=["Norway"],
        perspectives=[],
        threat_actors=["APT29"],
        priority_focus="attack vectors",
    )

    #Should return a non-empty result
    assert result
    assert isinstance(result, str)
