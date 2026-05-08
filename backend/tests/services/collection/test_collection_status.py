import pytest
from unittest.mock import MagicMock, patch

from src.services.collection.collection_status import CollectionStatusTracker


@pytest.fixture
def mock_repo():
    with patch("src.services.collection.collection_status._repo") as mock:
        mock.upsert = MagicMock()
        mock.get = MagicMock(return_value=None)
        yield mock


@pytest.fixture
def tracker(mock_repo):
    return CollectionStatusTracker(
        session_id="test-session",
        selected_sources=["Knowledge Bank", "AlienVault OTX"],
    )


class TestInit:
    def test_initial_status_is_collecting(self, mock_repo):
        # arrange / act
        tracker = CollectionStatusTracker("sess-1", ["Knowledge Bank"])

        # assert
        assert tracker._data["status"] == "collecting"

    def test_selected_sources_are_initialized(self, mock_repo):
        # arrange / act
        tracker = CollectionStatusTracker("sess-1", ["Knowledge Bank", "AlienVault OTX"])

        # assert
        assert "Knowledge Bank" in tracker._data["sources"]
        assert "AlienVault OTX" in tracker._data["sources"]

    def test_flushes_to_repo_on_init(self, mock_repo):
        # arrange / act
        CollectionStatusTracker("sess-1", ["Knowledge Bank"])

        # assert
        mock_repo.upsert.assert_called_once()


class TestRecordToolCall:
    def test_fetch_page_increments_current_source_count(self, tracker, mock_repo):
        # arrange
        tracker._data["current_source"] = "Knowledge Bank"

        # act
        tracker.record_tool_call("fetch_page")

        # assert
        assert tracker._data["sources"]["Knowledge Bank"]["call_count"] == 1

    def test_fetch_page_sets_reading_activity(self, tracker, mock_repo):
        # arrange
        tracker._data["current_source"] = "Knowledge Bank"

        # act
        tracker.record_tool_call("fetch_page")

        # assert
        assert tracker._data["current_activity"] == "Reading page"

    def test_known_source_tool_sets_current_source(self, tracker, mock_repo):
        # arrange — no prior current_source

        # act
        tracker.record_tool_call("read_knowledge_base")

        # assert
        assert tracker._data["current_source"] == "Knowledge Bank"

    def test_no_count_tool_does_not_increment_call_count(self, tracker, mock_repo):
        # arrange
        initial_count = tracker._data["sources"]["AlienVault OTX"]["call_count"]

        # act
        tracker.record_tool_call("google_search")

        # assert
        assert tracker._data["sources"]["AlienVault OTX"]["call_count"] == initial_count

    def test_unknown_tool_is_ignored_no_flush(self, tracker, mock_repo):
        # arrange
        call_count_before = mock_repo.upsert.call_count

        # act
        tracker.record_tool_call("some_unknown_tool_xyz")

        # assert
        assert mock_repo.upsert.call_count == call_count_before

    def test_read_upload_counts_each_unique_file_once(self, mock_repo):
        # arrange
        tracker = CollectionStatusTracker("sess-1", ["Uploaded Documents"])

        # act
        tracker.record_tool_call("read_upload", {"file_upload_id": "file-1"})
        tracker.record_tool_call("read_upload", {"file_upload_id": "file-1"})  # duplicate
        tracker.record_tool_call("read_upload", {"file_upload_id": "file-2"})

        # assert
        assert tracker._data["sources"]["Uploaded Documents"]["call_count"] == 2

    def test_otx_tool_increments_alienvault_count(self, tracker, mock_repo):
        # arrange — no prior state needed

        # act
        tracker.record_tool_call("query_otx")

        # assert
        assert tracker._data["sources"]["AlienVault OTX"]["call_count"] == 1


class TestSetSourceCount:
    def test_overwrites_existing_count(self, tracker, mock_repo):
        # arrange
        tracker._data["sources"]["Knowledge Bank"]["call_count"] = 5

        # act
        tracker.set_source_count("Knowledge Bank", 42)

        # assert
        assert tracker._data["sources"]["Knowledge Bank"]["call_count"] == 42

    def test_ignores_unknown_source_without_crashing(self, tracker, mock_repo):
        # arrange / act / assert — should not raise
        tracker.set_source_count("Non-existent Source", 99)


class TestMarkComplete:
    def test_sets_status_to_complete(self, tracker, mock_repo):
        # arrange — status starts as "collecting"

        # act
        tracker.mark_complete()

        # assert
        assert tracker._data["status"] == "complete"

    def test_clears_current_source(self, tracker, mock_repo):
        # arrange
        tracker._data["current_source"] = "Knowledge Bank"

        # act
        tracker.mark_complete()

        # assert
        assert tracker._data["current_source"] is None

    def test_clears_current_activity(self, tracker, mock_repo):
        # arrange
        tracker._data["current_activity"] = "Searching"

        # act
        tracker.mark_complete()

        # assert
        assert tracker._data["current_activity"] is None


class TestRead:
    def test_returns_none_when_session_not_found(self, mock_repo):
        # arrange
        mock_repo.get.return_value = None

        # act
        result = CollectionStatusTracker.read("missing-session")

        # assert
        assert result is None

    def test_returns_status_dict_when_found(self, mock_repo):
        # arrange
        mock_repo.get.return_value = {"status": "complete", "sources": {}}

        # act
        result = CollectionStatusTracker.read("found-session")

        # assert
        assert result == {"status": "complete", "sources": {}}

    def test_returns_none_on_repo_exception(self, mock_repo):
        # arrange
        mock_repo.get.side_effect = Exception("DB connection failed")

        # act
        result = CollectionStatusTracker.read("error-session")

        # assert
        assert result is None
