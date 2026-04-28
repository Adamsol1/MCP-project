---
DOCUMENT ID: KB-2025-022
CLASSIFICATION: UNCLASSIFIED // TLP:RED — NOT FOR DISTRIBUTION OUTSIDE AUTHORISED RECIPIENTS
TITLE: Chinese State-Sponsored Threat Actors
AUTHOR: Dr. Mei Lin Chen, Asia-Pacific Cyber Analyst
DATE: 12 April 2025
ORGANIZATION: Knowledge Base
---

# Chinese State-Sponsored Threat Actors

## Strategic Overview
China operates the world's largest state intelligence programme, combining cyber espionage, human intelligence, and commercial access to achieve persistent, deep collection against political, economic, military, and technological targets globally. Chinese cyber operations are conducted primarily by the Ministry of State Security (MSS) and the People's Liberation Army (PLA) through the Strategic Support Force. Chinese operations are characterised by long operational timelines, patient persistence, and focus on IP theft and pre-positioning rather than destruction.

## Ministry of State Security (MSS) Units

### APT40 / TEMP.Periscope / Bronze Mohawk
Maritime and naval focus. Extensively targeted naval engineering, maritime research institutions, and undersea technology companies in the US, EU, Australia, and Southeast Asia. Known for rapid exploitation of newly disclosed vulnerabilities and targeting of COVID-19 vaccine research during the pandemic. Active in Microsoft Exchange exploitation campaigns.

### APT41 / Double Dragon / Winnti
A unique dual-mission actor conducting both MSS-directed espionage and financially motivated intrusions. Responsible for supply chain compromises (ASUS LiveUpdate, CCleaner), pharmaceutical IP theft, gaming company compromises, and exploitation of public-facing applications within hours of CVE disclosure. Demonstrated ability to compromise hardware and software supply chains. Active against healthcare, technology, and telecommunications sectors globally.

### APT10 / Stone Panda / MenuPass
Long-running operation against managed service providers (MSP), enabling collection against MSP clients across multiple countries simultaneously. Responsible for Operation Cloud Hopper (2016-2018), compromising MSPs across 14 countries to access client networks. Targets: defence, satellite, maritime, advanced manufacturing, pharmaceutical, and government sectors.

## PLA Strategic Support Force

### Volt Typhoon (BRONZE SILHOUETTE)
The highest-profile and most strategically concerning Chinese actor. Volt Typhoon does not conduct traditional espionage — it pre-positions access in US and Western critical infrastructure (power utilities, water systems, ports, communications providers) for use in disruptive or destructive attacks in a conflict scenario, assessed as preparation for a Taiwan contingency. Uses exclusively "living off the land" techniques (built-in system tools: PowerShell, WMI, scheduled tasks) to avoid detection. CISA and Five Eyes confirmed its presence in US critical infrastructure in 2024.

### Salt Typhoon
Targeted US and allied telecommunications providers including AT&T, Verizon, and Lumen. Compromised lawful intercept systems, enabling collection of call records and interception of senior US government officials' communications. A long-running, deep-access collection operation representing one of the most significant intelligence breaches against US communications infrastructure.

### APT1 / Comment Crew / PLA Unit 61398
The unit that catalysed Western awareness of Chinese cyber espionage (Mandiant 2013 report). Conducted industrial-scale IP theft from US companies in aerospace, energy, defence, and industrial sectors. Operated at factory scale — structured shifts of analysts against assigned sectors. Activity restructured under other unit designations after public exposure and 2015 Obama-Xi cybercrime agreement.

## Key Operational Characteristics
- **Volume and patience**: Chinese operations maintain simultaneous access to thousands of targets, accepting low discovery rates in exchange for breadth
- **Living off the land**: Increasingly avoids custom malware in favour of legitimate system tools, making detection and attribution far harder
- **Supply chain focus**: Hardware (Huawei), software (SolarWinds-style), and firmware-level targeting
- **Data aggregation**: Combining breaches of healthcare (OPM, Anthem), travel (Marriott), financial, and government databases to build comprehensive profiles on individuals of intelligence value

## Known Major Operations
- OPM breach — 21.5 million US government security clearance records exfiltrated (MSS, 2014–2015)
- Operation Cloud Hopper — MSP supply chain compromise across 14 countries (APT10, 2016-2018)
- Volt Typhoon pre-positioning in US critical infrastructure including Guam (confirmed 2023-2024)
- Salt Typhoon compromise of US carrier lawful intercept infrastructure (confirmed 2024)
- Microsoft Exchange Server mass exploitation (Hafnium/MSS, 2021) — hundreds of thousands of organisations globally

## Intelligence Implications
Chinese operations reflect a strategic culture of patience and comprehensive collection. Primary objectives: acquiring technology to close military and economic gaps, mapping adversary infrastructure for contingency use, and identifying intelligence assets and policy positions. The Volt Typhoon pre-positioning shifts Chinese cyber strategy from collection to coercive deterrence — threatening civilian disruption in any Taiwan conflict scenario.
