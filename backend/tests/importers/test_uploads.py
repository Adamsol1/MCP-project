
import io

import pytest

from src.importers.upload import legal_file_upload, save_uploaded_file

class TestFileTypeValidation:
    """Test suite for validating allowed and disallowed file types."""

    @pytest.mark.parametrize("filename", [
        "data.txt",
        "data.pdf",
        "data.json",
        "data.csv",
        "data.TXT",          # Test if filetype check is case insensitive
        "data.PDF",          # Test if filetype check is case insensitive
        "file.name.csv",     # Test if multiple dots are handled
        "data.exe.txt",      # Test that last dots is considered
    ])
    def test_legal_file_types_are_accepted(self, filename):
        ##Test if legal filetypes are accepted.
        ##Legal file types are : .txt, .pdf, .json, .csv

        assert legal_file_upload(filename), f"{filename} failed, but should be legal"

    @pytest.mark.parametrize("filename", [
        "data.exe",
        "data.bat",
        "data.sh",
        "data.zip",
        "malware.dll",
        "script.py",
        "noextension",
    ])
    def test_illegal_file_types_are_rejected(self, filename):
        ##Test if illegal filetypes are rejected.
        assert not legal_file_upload(filename), f"Expected {filename} to be illegal"


class TestFileSaving:
    ##Tests for saving uploaded files

    def test_file_saved_to_correct_directory(self, tmp_path):
        ##File should be saved to correct directory

        # Mock file and data to test
        file_content = b"test data"
        mock_file = io.BytesIO(file_content)
        filename = "test.txt"

        #Attempt to save the mock file
        result_path = save_uploaded_file(mock_file, filename, tmp_path)

        #Check the results
        #Expected path for the saved file
        expected_path = tmp_path / filename
        assert result_path == expected_path, "File path does not match expected path"
        assert result_path.exists(), "File is not saved on disk"
        assert result_path.read_bytes() == file_content, "File content does not match the original file"

    ##Test for checking if attempting to save illegal filetype gives error
    def test_illegal_filetype_raises_error(self, tmp_path):
        ##Trying to save illegal filetype should raise ValueError

        #Mock file and data
        mock_file = io.BytesIO(b"test")
        illegal_filename = "test.exe"

        # Attempt to save file and expect ValueError
        with pytest.raises(ValueError):
            save_uploaded_file(mock_file, illegal_filename, tmp_path)

    ##Test for checking that illegal filetype is not saved to disk
    def test_illegal_filetype_not_saved_to_disk(self, tmp_path):

        #Create mock file and data
        file = io.BytesIO(b"data")
        illegal_filename = "test.exe"

        #Attempt to save file and expect ValueError
        with pytest.raises(ValueError):
            save_uploaded_file(file, illegal_filename, tmp_path)

        #Check that the file was not saved on disk
        assert not (tmp_path / illegal_filename).exists(), "Illegal file should not exist on disk"

    #Test for checking allowed file types are saved
    @pytest.mark.parametrize("filename,content", [
        ("report.pdf", b"Test"),
        ("data.json", b"Test"),
        ("logs.txt", b"Test"),
        ("indicators.csv", b"Test"),
    ])
    ##Test that different allowed filetypes are saved
    def test_different_file_types_saved_correctly(self, tmp_path, filename, content):
        #Create the mock file
        file = io.BytesIO(content)

        #Attempt to save file with filetypes
        result_path = save_uploaded_file(file, filename, tmp_path)

        #Check the results
        assert result_path.exists()
        assert result_path.read_bytes() == content

class TestEdgeCases:
    ##Test edge cases for the file uploads

    ##Test if an empty file can be saved. Expected resuls is yes.
    def test_empty_file_can_be_saved(self, tmp_path):

        #Create mock file that is empty
        empty_file = io.BytesIO(b"")

        #Attempt to save it
        result = save_uploaded_file(empty_file, "empty.txt", tmp_path)

        #Check the results
        assert result.exists()
        assert result.read_bytes() == b""


    ##Check if filename with multiple dots use the last dot as the filetype
    def test_filename_with_multiple_dots(self, tmp_path):
        #Create mock file
        file_obj = io.BytesIO(b"data")

        #Attempt to save the file
        result = save_uploaded_file(file_obj, "my.file.name.txt", tmp_path)

        #Check the results
        assert result.exists()
        assert result.name == "my.file.name.txt"
