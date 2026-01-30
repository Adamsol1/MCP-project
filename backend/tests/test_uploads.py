import pytest
from src.importers.upload import save_uploaded_file,legal_file_upload, allowed_filetypes
from unittest.mock import Mock


# Test for uploading functionalities. Will test if file that will be uploaded is legal to upload.


##Tests for legal and illegal file uploads.
class TestFileUpload:
    ##Tests value for legal file uploads
    @pytest.mark.parametrize("filename", [
        "data.txt",
        "data.pdf",
        "data.json",
        "data.csv",
        "data.exe.txt"
    ])

    ##Test the legal file upload function.
    def test_legal_file_upload(self, filename):
        assert legal_file_upload(filename)

    ##Test values for illegal file uploads
    @pytest.mark.parametrize("filename", [
        "data.exe",
        "data.bat",
        "data.sh",
        "data.zip",
    ])
    ##Test the illegal file upload function.
    def test_illegal_file_upload(self, filename):
        assert not legal_file_upload(filename)


class TestFileSaving:
     ###Test class for saving files after upload. They should be saved to "data/imports".
    def test_file_saved_to_correct_directory(self, tmp_path):

        mock_file = Mock()
        mock_file.filename = "test.txt"
        ##Create test file in temp directory by using built in pytest feature

        ##Function for saving file
        save_uploaded_file(mock_file, tmp_path)
        ##Checks if file is saved to correct path
        assert (tmp_path /"test.txt").exists()

     ##Test for checking that a file is not saved if filetype is illegal
    def test_illegal_filetype_not_saved(self, tmp_path):
        ##Test for checking that illegal filetype are not saved
        mock_file = Mock()
        mock_file.filename = "test.exe"


        save_uploaded_file(mock_file, tmp_path)
        ##Checks that file does not exist in the path
        assert not (tmp_path / "test.exe").exists()










class TestFileUploadResponse:
     ##Tests for expected responses when uploading files.

     ##List of expected responses inclduing both legal and illegal file uploads.
