class DialogueContext:
  def __init__(self):
    self.initial_query = "" #The initial query given by the user. This will withhold inteded goal
    self.scope = "" #Scope of the current investigation
    self.timeframe = "" #Set the timefra for current investigation
    self.target_entities = [] #List of target entities for current investigation. E.g [Norway, Russsia]

class DialogueResponse:
  def __init__(self):
    self.action ="" #The action returned to the frontend. Informs about what the frontend shall do
    self.content="" #The reponse content. Can be question/information connected to the action
