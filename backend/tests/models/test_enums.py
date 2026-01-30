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
