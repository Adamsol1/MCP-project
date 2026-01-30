from pathlib import Path

from fastapi import UploadFile

allowed_filetypes = [".txt", ".pdf", ".json", ".csv"]

##Function for checking if filetype is legal.
##Returns True if legal, and false if illegal.

def legal_file_upload(filetype : str) -> bool:
        ##Checks if filetype contains a dot.
        if "." not in filetype:
            return False

        ##Finds filetype by splitting the string by . and taking the last element.
        formattetFiletype = filetype.split(".")[-1].lower()
        return formattetFiletype in allowed_filetypes


##Destination is optional because of the mock tests
def save_uploaded_file(file: UploadFile, destination=None):
  ##Checks if a destination is given. if not use the default destination.
  if destination is None:
      destination = Path("data/imports")

  save_destination = destination / file.filename
  filename = file.filename
  ##Check if filetype is legal. If not raise error
  if not legal_file_upload(filename):
    ##If not legal return error and no save
    raise ValueError("Illegal filetype")

  ##If legal save to directory
  with open(save_destination, "wb") as f:
      f.write(file.file.read())


      ##Return success
      return save_destination
