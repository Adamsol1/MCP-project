"""
Tests for threat intelligence enums.
"""


class TestIOCType:
    """Test IOCType enum."""

    def test_ioc_type_has_all_exptected_values(self):
        from src.models.enums import IOCType

        expected_values = {
            "ipv4",
            "ipv6",
            "domain",
            "url",
            "md5",
            "sha1",
            "sha256",
            "email",
            "cve",
        }
        actual_values = {item.value for item in IOCType}

        assert actual_values == expected_values


class TestThreatLevel:
    """Test ThreatLevel for secerity classification."""

    def test_threat_level_has_all_expected_values(self):
        from src.models.enums import ThreatLevel

        except_values = {"critical", "high", "medium", "low", "unknown"}
        actual_values = {items.value for items in ThreatLevel}

        assert actual_values == except_values


class TestTLPLevel:
    """Test TLP levels for information sharing"""

    def test_tlp_level_has_all_expected_values(self):
        from src.models.enums import TLPLevel

        excepted_values = {"white", "green", "amber", "red"}
        actual_values = {items.value for items in TLPLevel}

        assert actual_values == excepted_values


class TestIndicatorRole:
    """Test IndicatorRole enum for IOC categorization."""

    def test_indicator_role_has_all_expected_values(self):
        from src.models.enums import IndicatorRole

        expected = {"c2", "malware", "phishing", "scanner", "exfiltration", "unknown"}
        actual = {member.value for member in IndicatorRole}

        assert actual == expected


class TestDataSource:
    """Test DataSource enum for tracking data origin."""

    def test_data_source_has_all_expected_values(self):
        from src.models.enums import DataSource

        expected = {
            "otx",
            "misp",
            "csv_upload",
            "pdf_upload",
            "txt_upload",
            "json_upload",
            "manual",
        }
        actual = {member.value for member in DataSource}

        assert actual == expected


class TestExtractionMethod:
    """Test ExtractionMethod enum."""

    def test_extraction_method_has_all_expected_values(self):
        from src.models.enums import ExtractionMethod

        expected = {"direct_parse", "regex", "ai_extraction", "manual"}
        actual = {member.value for member in ExtractionMethod}

        assert actual == expected


class TestProcessingStatus:
    """Test ProcessingStatus enum for file processing state."""

    def test_processing_status_has_all_expected_values(self):
        from src.models.enums import ProcessingStatus

        expected = {"pending", "processing", "completed", "failed"}
        actual = {member.value for member in ProcessingStatus}

        assert actual == expected
