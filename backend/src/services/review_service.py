
class ReviewService():
  #Review service for PIR reports
  def __init__(self, ai_service):
    self.ai_service = ai_service

  def review_pir(self, pir_report, context):
    #Call AI service to review PIR against context
    result = self.ai_service.review(pir_report, context)
    return result
