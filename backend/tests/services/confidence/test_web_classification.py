"""TDD tests for web source URL classification.

Tests are written before implementing classify_web_source in scoring.py.
Priority order (from plan): state_media → gov_pattern → gov_exact → think_tank → news → other.
"""

from src.services.confidence.scoring import classify_web_source


class TestGovernmentPattern:
    """.gov/.mil pattern-based government detection."""

    def test_dot_gov_url(self):
        assert (
            classify_web_source("https://www.fbi.gov/reports/2024", None) == "web_gov"
        )

    def test_dot_mil_url(self):
        assert classify_web_source("https://www.defense.mil/news", None) == "web_gov"

    def test_dot_gov_cn_url(self):
        assert classify_web_source("https://www.miit.gov.cn/news", None) == "web_gov"

    def test_dot_gob_url(self):
        assert (
            classify_web_source("https://www.interior.gob.es/report", None) == "web_gov"
        )

    def test_dot_govt_url(self):
        assert (
            classify_web_source("https://www.security.govt.nz/report", None)
            == "web_gov"
        )


class TestGovernmentExactDomain:
    """Exact-match government domains that don't follow standard patterns."""

    def test_nato_int(self):
        assert (
            classify_web_source("https://www.nato.int/cps/en/report", None) == "web_gov"
        )

    def test_europa_eu(self):
        assert (
            classify_web_source("https://ec.europa.eu/commission/report", None)
            == "web_gov"
        )

    def test_regjeringen_no(self):
        assert (
            classify_web_source("https://www.regjeringen.no/no/rapport", None)
            == "web_gov"
        )

    def test_forsvaret_no(self):
        assert (
            classify_web_source("https://www.forsvaret.no/aktuelt", None) == "web_gov"
        )

    def test_government_ru(self):
        assert classify_web_source("https://government.ru/news/2024", None) == "web_gov"

    def test_kremlin_ru(self):
        assert classify_web_source("https://kremlin.ru/events/2024", None) == "web_gov"

    def test_bsi_bund_de(self):
        assert classify_web_source("https://www.bsi.bund.de/report", None) == "web_gov"


class TestStateMedia:
    """State media classified as web_gov (official state positions, not independent)."""

    def test_xinhuanet_is_gov(self):
        assert (
            classify_web_source("https://www.xinhuanet.com/english", None) == "web_gov"
        )

    def test_tass_is_gov(self):
        assert classify_web_source("https://tass.com/defense/report", None) == "web_gov"

    def test_rt_is_gov(self):
        assert classify_web_source("https://www.rt.com/russia/news", None) == "web_gov"

    def test_global_times_is_gov(self):
        assert (
            classify_web_source("https://www.globaltimes.cn/page/2024", None)
            == "web_gov"
        )

    def test_sputnik_is_gov(self):
        assert (
            classify_web_source("https://sputniknews.com/20240101", None) == "web_gov"
        )


class TestThinkTank:
    """Known think-tank domains → web_think_tank."""

    def test_csis_org(self):
        assert (
            classify_web_source("https://www.csis.org/analysis/report", None)
            == "web_think_tank"
        )

    def test_rand_org(self):
        assert (
            classify_web_source("https://www.rand.org/pubs/report.html", None)
            == "web_think_tank"
        )

    def test_rusi_org(self):
        assert (
            classify_web_source("https://rusi.org/publication", None)
            == "web_think_tank"
        )

    def test_nupi_no(self):
        assert (
            classify_web_source("https://www.nupi.no/publikasjoner", None)
            == "web_think_tank"
        )

    def test_sipri_org(self):
        assert (
            classify_web_source("https://www.sipri.org/yearbook/2024", None)
            == "web_think_tank"
        )


class TestNewsOutlets:
    """Known news outlets → web_news."""

    def test_reuters(self):
        assert (
            classify_web_source("https://www.reuters.com/world/europe", None)
            == "web_news"
        )

    def test_bbc(self):
        assert (
            classify_web_source("https://www.bbc.com/news/world-europe", None)
            == "web_news"
        )

    def test_nrk_no(self):
        assert (
            classify_web_source("https://www.nrk.no/nyheter/article", None)
            == "web_news"
        )

    def test_ft(self):
        assert (
            classify_web_source("https://www.ft.com/content/report", None) == "web_news"
        )

    def test_bloomberg(self):
        assert classify_web_source("https://www.bloomberg.com/news", None) == "web_news"


class TestUnknownAndEdgeCases:
    """Unknown domains fall back to web_other."""

    def test_unknown_domain(self):
        assert (
            classify_web_source("https://www.someunknownblog.com/post", None)
            == "web_other"
        )

    def test_none_url(self):
        assert classify_web_source(None, None) == "web_other"

    def test_empty_string_url(self):
        assert classify_web_source("", None) == "web_other"

    def test_localhost_is_other(self):
        assert classify_web_source("http://localhost:8000/api", None) == "web_other"
