import os
import pytest
from pathlib import Path
from unittest.mock import patch

from src.db.engine import _db_path, get_sessions_db_path, get_knowledge_db_path


class TestDbPath:
    def test_uses_env_var_when_set(self):
        # arrange
        custom_path = "/custom/path/mydb.sqlite"

        # act
        with patch.dict(os.environ, {"TEST_DB_PATH": custom_path}):
            result = _db_path("TEST_DB_PATH", "default.db")

        # assert
        assert result == Path(custom_path)

    def test_uses_default_filename_when_env_var_not_set(self, tmp_path):
        # arrange
        env_var = "NONEXISTENT_DB_PATH_XYZ"

        # act
        with patch("src.db.engine._DEFAULT_DATA_DIR", tmp_path):
            with patch.dict(os.environ, {}, clear=True):
                result = _db_path(env_var, "sessions.db")

        # assert
        assert result.name == "sessions.db"

    def test_default_path_is_under_data_dir(self, tmp_path):
        # arrange
        env_var = "NONEXISTENT_DB_PATH_XYZ"

        # act
        with patch("src.db.engine._DEFAULT_DATA_DIR", tmp_path):
            with patch.dict(os.environ, {}, clear=True):
                result = _db_path(env_var, "sessions.db")

        # assert
        assert str(tmp_path) in str(result)


class TestDbPathHelpers:
    def test_get_sessions_db_path_returns_a_path_object(self):
        # arrange — no setup needed

        # act
        result = get_sessions_db_path()

        # assert
        assert isinstance(result, Path)

    def test_get_sessions_db_path_ends_with_sessions_db(self):
        # arrange
        with patch.dict(os.environ, {}, clear=True):
            with patch("src.db.engine._DEFAULT_DATA_DIR", Path("/tmp/test_data")):

                # act
                result = get_sessions_db_path()

        # assert
        assert result.name == "sessions.db"

    def test_get_knowledge_db_path_returns_a_path_object(self):
        # arrange — no setup needed

        # act
        result = get_knowledge_db_path()

        # assert
        assert isinstance(result, Path)

    def test_get_knowledge_db_path_ends_with_knowledge_db(self):
        # arrange
        with patch.dict(os.environ, {}, clear=True):
            with patch("src.db.engine._DEFAULT_DATA_DIR", Path("/tmp/test_data")):

                # act
                result = get_knowledge_db_path()

        # assert
        assert result.name == "knowledge.db"

    def test_sessions_db_path_respects_env_var_override(self):
        # arrange
        custom = "/override/path/sessions.db"

        # act
        with patch.dict(os.environ, {"SESSIONS_DB_PATH": custom}):
            result = get_sessions_db_path()

        # assert
        assert result == Path(custom)
