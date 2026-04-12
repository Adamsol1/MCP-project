"""Configurable domain lists for web source authority classification.

All lists are constants — extend these during testing without touching logic code.
State media is classified as web_gov (not web_news) because it reflects official
state positions rather than independent reporting. See thesis design note.
"""

# ---------------------------------------------------------------------------
# Source authority weights
# ---------------------------------------------------------------------------

SOURCE_AUTHORITY_WEIGHTS: dict[str, float] = {
    # Internal curated sources
    "knowledge_bank": 1.00,
    "knowledge_base": 1.00,
    # Perspective documents (national security docs used as framing)
    "perspective": 0.85,
    # Threat intelligence feeds
    "otx": 0.70,
    "otx_high_rep": 0.70,
    "otx_low_rep": 0.45,
    "osint": 0.70,
    # User uploads (untagged — could be anything)
    "uploaded": 0.50,
    "manual": 0.50,
    "network_telemetry": 0.50,
    "malware_analysis": 0.50,
    # Web sources — differentiated by publisher type
    "web_gov": 0.50,
    "web_think_tank": 0.40,
    "web_news": 0.35,
    "web_other": 0.25,
    "web_search": 0.35,  # fallback when publisher isn't classified
    # AI pretrained knowledge (no source attribution)
    "pretrained": 0.10,
    "uncited": 0.10,
}

# ---------------------------------------------------------------------------
# Corroboration scale (independent source clusters → score)
# ---------------------------------------------------------------------------

CORROBORATION_SCALE: dict[int, float] = {
    1: 0.25,
    2: 0.55,
    3: 0.75,
}
CORROBORATION_CAP = 0.90  # 4+ clusters — JDP 2-00 p. 32 irreducible uncertainty

# ---------------------------------------------------------------------------
# Government: pattern-based detection
# ---------------------------------------------------------------------------

GOV_PATTERNS: list[str] = [".gov.", ".mil.", ".gob.", ".govt."]

# Suffixes/exact patterns — covers most .gov.XX TLDs
GOV_SUFFIX_PATTERNS: list[str] = [".gov", ".mil", ".gob", ".govt"]

# Exact-match domains that don't follow the .gov/.mil pattern
GOV_EXACT_DOMAINS: set[str] = {
    # International / multilateral
    "nato.int",
    "europa.eu",
    "ec.europa.eu",
    "enisa.europa.eu",
    "eeas.europa.eu",
    # Norway
    "regjeringen.no",
    "forsvaret.no",
    "nsm.no",
    "pst.no",
    "nis.no",
    "ffi.no",
    "dsa.no",
    # US (most covered by .gov/.mil patterns)
    "cisa.gov",
    "nsa.gov",
    # EU member states — common exceptions
    "bmi.bund.de",
    "bka.de",
    "bsi.bund.de",
    "gouvernement.fr",
    "sgdsn.gouv.fr",
    "government.nl",
    "aivd.nl",
    # China — government and state agencies
    "miit.gov.cn",
    "mps.gov.cn",
    "mod.gov.cn",
    "cert.org.cn",
    # Russia — government domains
    "government.ru",
    "kremlin.ru",
    "mid.ru",
    "fsb.ru",
}

# ---------------------------------------------------------------------------
# State media — classified as web_gov (not web_news)
# These outlets reflect official state positions and are not editorially
# independent. Design decision documented for thesis.
# ---------------------------------------------------------------------------

STATE_MEDIA_DOMAINS: set[str] = {
    # China
    "xinhuanet.com",
    "xinhua.net",
    "globaltimes.cn",
    "chinadaily.com.cn",
    "eng.mod.gov.cn",
    # Russia
    "tass.com",
    "ria.ru",
    "rt.com",
    "sputniknews.com",
}

# ---------------------------------------------------------------------------
# Think tanks & research institutions
# ---------------------------------------------------------------------------

THINK_TANK_DOMAINS: set[str] = {
    # US / International
    "csis.org",
    "rand.org",
    "cfr.org",
    "brookings.edu",
    "carnegieendowment.org",
    "heritage.org",
    "cato.org",
    "americanprogress.org",
    # UK / Europe
    "rusi.org",
    "chathamhouse.org",
    "iiss.org",
    "ecfr.eu",
    "cer.eu",
    "swp-berlin.org",
    # Nordic
    "nupi.no",
    "fiia.fi",
    "foi.se",
    "diis.dk",
    # Asia-focused
    "aspi.org.au",
    "iseas.edu.sg",
    # Security / conflict specific
    "sipri.org",
    "crisisgroup.org",
    "recordedfuture.com",
    "mandiant.com",
    "isw",
}

# ---------------------------------------------------------------------------
# News outlets (editorially independent)
# ---------------------------------------------------------------------------

NEWS_DOMAINS: set[str] = {
    # Wire services
    "reuters.com",
    "apnews.com",
    "afp.com",
    # English-language international
    "bbc.com",
    "bbc.co.uk",
    "ft.com",
    "economist.com",
    "nytimes.com",
    "washingtonpost.com",
    "theguardian.com",
    "wsj.com",
    "bloomberg.com",
    # Nordic
    "nrk.no",
    "vg.no",
    "aftenposten.no",
    "dn.no",
    "svt.se",
    "yle.fi",
    # European
    "lemonde.fr",
    "spiegel.de",
    "elpais.com",
    "politico.eu",
    # Asia-Pacific
    "scmp.com",
    "japantimes.co.jp",
}
