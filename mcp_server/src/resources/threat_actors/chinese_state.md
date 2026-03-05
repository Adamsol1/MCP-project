# Chinese State-Sponsored Threat Actors

## Strategic Overview
China operates the world's largest state-sponsored cyber espionage programme. Operations are primarily conducted by the Ministry of State Security (MSS) and People's Liberation Army (PLA), with significant contractor involvement. Chinese cyber operations emphasise volume, patience, and IP theft over destructive capability — though pre-positioning for disruption is an emerging priority.

## Primary Threat Groups

### MSS — APT41 / Double Dragon / Winnti
Unique in combining state-sponsored espionage with financially motivated cybercrime. Active against healthcare, telecommunications, technology, and gaming sectors globally. Known for supply chain attacks (ASUS LiveUpdate, CCleaner) and exploitation of public-facing applications within hours of CVE disclosure. TTPs: fast exploitation of new vulnerabilities, supply chain compromise, data exfiltration at scale.

### PLA Unit 61398 — Comment Crew / APT1
Extensively documented by Mandiant in 2013. Focus on systematic IP theft across 20 industry sectors including aerospace, defence, energy, and telecommunications. Operated on a factory scale — hundreds of analysts working structured shifts against assigned targets. TTPs: spearphishing for initial access, sustained long-dwell collection, structured data exfiltration.

### MSS — Volt Typhoon
Identified by CISA and Five Eyes partners in 2023. Focus is not espionage but strategic pre-positioning in US and allied critical infrastructure — utilities, water systems, communications, and transportation. Assessed to be preparation for disruptive attacks in a Taiwan contingency. TTPs: living off the land (no custom malware), compromised SOHO routers as relay nodes, extremely low signature.

### MSS — Salt Typhoon
Targeted telecommunications providers in the US and allied countries. Compromised carrier infrastructure used for lawful intercept, enabling collection of call records and interception of senior government officials' communications. Assessed as a long-running collection operation, not disruption-focused. Discovered 2024.

## Known Major Operations
- OPM breach — 21.5 million US government security clearance records exfiltrated (MSS, 2014–2015)
- Volt Typhoon pre-positioning in Guam and US critical infrastructure (confirmed 2023)
- Salt Typhoon compromise of AT&T, Verizon, and other US carriers (confirmed 2024)
- Microsoft Exchange Server exploitation targeting defence contractors and research institutions (APT41, 2021)

## Intelligence Implications
Chinese cyber operations reflect a strategic culture of patience and comprehensive collection. The primary objectives are: acquiring technology to close military and economic gaps with the West, mapping adversary critical infrastructure for contingency use, and identifying intelligence assets and policy positions. The shift toward pre-positioning (Volt Typhoon) indicates preparation for potential high-intensity conflict scenarios.
