import pytest

from src.api import main


#For mocking the upload path in tests to prevent test data from being saved
@pytest.fixture
def mock_upload_path(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "UPLOAD_PATH", tmp_path)
    return tmp_path
