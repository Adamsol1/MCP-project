from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)

class TestFileUploads:

  @pytest.mark.parametrize("file_name, content", [
    ("test.txt", "test data"),
    ("test.pdf", "test data"),
    ("test.json", "test data"),
    ("test.csv", "test data")
  ])
  ##Test for uploading json file
  def test_upload_legal_filetype(self, file_name, content, mock_upload_path):  # noqa: ARG002 //Disable mock_upload_path warning because pytest uses it for test setup


    ##Attempt to upload file
    http_response = client.post(
      "/api/import/upload",
      files={"file": (file_name, content, "application/json")}
    )

    ##Check the results
    assert http_response.status_code == 200

  ##Files used for testing
  @pytest.mark.parametrize("file_name, content", [
    ("test.exe", "test data"),
    ("test.bat", "test data"),
    ("test.sh", "test data"),
    ("test.docx", "test data")
  ])
  ##Test for checking http response with illegal filetypes
  def test_upload_illegal_filetype(self, file_name, content):
    #Perform a request towards api with different files and save the http respone
    http_response = client.post(
      "/api/import/upload",
      files={"file":(file_name, content, "application/json")}
    )
    ##Test if the http reponse is correct
    assert http_response.status_code == 400


  def test_if_uploaded_file_is_saved_to_file(self, mock_upload_path):  # noqa: ARG002
    file_content = b"test data"
    filename = "test.txt"

    #Attempt to upload file
    http_respone = client.post(
      "/api/import/upload",
      files={"file":(filename, file_content, "application/json")}
    )

    #Check result
    respone_data = http_respone.json()
    saved_path = respone_data.get("path")

    assert saved_path is not None


  def test_if_uploaded_file_is_saved_to_correct_place(self, mock_upload_path):
    #Create mock data for test
    file_content = b"test data"
    filename = "test.txt"

    #Attempt to upload file
    client.post(
      "/api/import/upload",
      files={"file":(filename, file_content, "application/json")}
    )
    #Check if file was saved in correct place with correct content
    saved_file = mock_upload_path / filename
    assert saved_file.exists()
    assert saved_file.read_bytes() == file_content





  def test_if_uploaded_response_contains_filename(self, mock_upload_path):  # noqa: ARG002
    #Create mock data for test
    file_content = b"test data"
    filename = "test.txt"

    #Attempt to upload file
    http_reponse = client.post(
      "/api/import/upload",
      files={"file":(filename, file_content, "application/json")}
    )
    #Check if response contains filename
    respone_data = http_reponse.json()
    assert "filename" in respone_data

  def test_upload_empty_file(self, mock_upload_path):
    #Create mock data for test
    file_content = b""
    filename = "empty.txt"

    #Attempt to upload file
    http_response = client.post(
      "/api/import/upload",
      files={"file":(filename, file_content, "application/json")}
    )

    #Check if upload was successful
    assert http_response.status_code == 200
    saved_file = mock_upload_path / filename
    assert saved_file.exists()
    assert saved_file.read_bytes() == b""

  def test_upload_does_not_overwrite_existing_files(self, mock_upload_path):
    #Create mock data for test with same filename but different content
    filename_first_file = "test.txt"
    filename_second_file = "test.txt"
    first_content = b"first version"
    second_content = b"second version"

    #Upload first file
    response1 = client.post(
      "/api/import/upload",
      files={"file":(filename_first_file, first_content, "application/json")}
    )
    path1 = response1.json().get("path")

    #Upload second file with same name
    response2 = client.post(
      "/api/import/upload",
      files={"file":(filename_second_file, second_content, "application/json")}
    )
    path2 = response2.json().get("path")

    #Check that paths are different
    assert path1 != path2

    #Check that both files exist with correct content
    saved_first_file = mock_upload_path / Path(path1).name
    saved_second_file = mock_upload_path / Path(path2).name

    assert saved_first_file.read_bytes() == first_content
    assert saved_second_file.read_bytes() == second_content

  def test_upload_without_file_returns_error(self):
    http_response = client.post("/api/import/upload")

    assert http_response.status_code == 422


