from datetime import datetime
from pathlib import Path

allowed_filetypes = [".txt", ".pdf", ".json", ".csv"]

##Function for checking if filetype is legal.
##Returns True if legal, and false if illegal.
def legal_file_upload(filetype : str) -> bool:
        ##Checks if filetype contains a dot.
        if "." not in filetype:
            return False

        ##Finds filetype by splitting the string by . and taking the last element.
        formattetFiletype = "." + filetype.split(".")[-1].lower()
        return formattetFiletype in allowed_filetypes


##Function for saving and uploading files
def save_uploaded_file(file, filename: str, save_directory) -> Path:
  if not legal_file_upload(filename):
      raise ValueError("Illegal filetype")

  path = save_directory / filename

  #Add timestamp to filename only if file already exists. This is for preventing overwriting files.
  while path.exists():
      name_parts = filename.rsplit(".", 1)
      base_name = name_parts[0]
      extension = "." + name_parts[1]
      date_time = datetime.now().strftime("%d-%m-%y_%H-%M-%S-%f")
      unique_filename = f"{base_name}_{date_time}{extension}"
      print("Unique : " + unique_filename)
      path = save_directory / unique_filename

  #Save the file to disk
  with open(path, "wb") as f:
      f.write(file.read())
  print(f"File saved to {path.as_posix()}")

  return path
