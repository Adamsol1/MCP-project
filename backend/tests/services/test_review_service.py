
#Test for checking review of PIR

from src.models.dialogue import DialogueContext
from src.services.review_service import ReviewService


# Mock AI service. Will simulate ai answer
# variabel should_approve bestemmer om ai bør svare ja eller nei
class MockAIReviewService:
  def __init__(self, should_approve):
    self.should_approve = should_approve

  def review(self, pir_report, context):
    return self.should_approve


def test_review_pir_is_approved():
  #Create enviorment for test
  context = DialogueContext()
  context.scope = "identify attack patterns"
  context.timeframe = "last 6 months"
  context.target_entities = ["Norway"]
  fake_pir_report = "Identify attack patterns in Norway over the last 6 months"

  # Mock AI som returnerer True
  mock_ai = MockAIReviewService(should_approve=True)
  review_service = ReviewService(mock_ai)

  #Perform method call
  result = review_service.review_pir(fake_pir_report, context)

  #Check results
  assert result


def test_review_pir_is_rejected():
  #Create enviorment for test
  context = DialogueContext()
  context.scope = "identify attack patterns"
  context.timeframe = "last 6 months"
  context.target_entities = ["Norway"]
  faulty_fake_pir_report = "Identify how USA defends against attacks in the last week"

  # Mock AI som returnerer False
  mock_ai = MockAIReviewService(should_approve=False)
  review_service = ReviewService(mock_ai)

  #Perform method call
  result = review_service.review_pir(faulty_fake_pir_report, context)

  #Check results
  assert not result
