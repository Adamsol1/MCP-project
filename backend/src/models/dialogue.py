class DialogueContext:
  def __init__(self):
    self.initial_query = "" #The initial query given by the user. This will withhold inteded goal
    self.scope = "" #Scope of the current investigation
    self.timeframe = "" #Set the timefra for current investigation
    self.target_entities = [] #List of target entities for current investigation. E.g [Norway, Russsia]
