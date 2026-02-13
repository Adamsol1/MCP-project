import json
from pathlib import Path


class ReasoningLogger:
  def __init__(self, log_path=None):
    #Use given log_path
    if log_path:
      self.log_path = Path(log_path)
    #Use default logpath
    else:
      self.log_path = Path("data/outputs/reasoning_log.jsonl") #TODO: Update with correct name when we have disussed this. For example: filename = file_reasoning + sessionid?

    self.log_path.parent.mkdir(parents=True, exist_ok=True)


  def create_log(self, log_entry):
    #Convert Pydantic model to dict, then to json
    if hasattr(log_entry, "model_dump"):
      log_entry = log_entry.model_dump(mode="json")
    converted_log = json.dumps(log_entry)

    log_file = self.log_path
    #Save the file to disk
    with open(log_file, "a") as f:
        f.write(converted_log+ "\n")






