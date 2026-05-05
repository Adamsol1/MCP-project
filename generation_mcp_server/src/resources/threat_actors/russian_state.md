---
DOCUMENT ID: KB-2024-066
CLASSIFICATION: UNCLASSIFIED // TLP:RED — NOT FOR DISTRIBUTION OUTSIDE AUTHORISED RECIPIENTS
TITLE: Russian State-Sponsored Threat Actors
AUTHOR: Dr. Sophie Brennan, Cyber Intelligence Analyst
DATE: 20 August 2024
ORGANIZATION: Knowledge Base
---

# Russian State-Sponsored Threat Actors

## Strategic Overview
Russia operates the most aggressive and diverse state cyber capability of any nation. Three primary intelligence services run distinct cyber programmes: the GRU (military intelligence), FSB (domestic/counterintelligence/internal), and SVR (foreign intelligence). These services operate in parallel and sometimes in competition, resulting in overlapping operations. Russian cyber operations are fully integrated into a broader hybrid warfare doctrine combining digital, influence, and kinetic action.

## GRU (Military Intelligence) Units

### APT28 / Fancy Bear / Unit 26165
Primary focus: political and military intelligence collection, election interference, and influence operations. Known campaigns include the DNC and DCCC breach (2016), targeting of WADA anti-doping agency, systematic attacks against EU political parties, NATO and EU institutions, and Ukrainian military command systems. Notable for use of X-Agent malware, credential harvesting via spearphishing, and exploitation of zero-day vulnerabilities in widely-used software.

### Sandworm / Unit 74455
The GRU's most destructive unit and the only actor confirmed to have caused physical blackouts through cyber means. Responsible for: Ukrainian power grid attacks (December 2015 — 225,000 customers; December 2016 — capital city outage using Industroyer malware), NotPetya wiper (2017 — $10+ billion global damage, destroyed Maersk, Merck, and FedEx operations), Olympic Destroyer malware (2018 Pyeongchang Winter Olympics), and Industroyer2 (2022, deployed against Ukrainian grid). Sandworm operations are characterised by supply chain compromise and destructive wiper deployment.

### APT44 / Seashell Blizzard
The GRU unit responsible for pre-positioning in Western and Ukrainian critical infrastructure. Maintains persistent access in Ukrainian governmental, energy, and transport networks used for intelligence and pre-attack positioning. Increasingly active in European infrastructure targeting.

## FSB (Federal Security Service) Units

### Turla / Snake / Venomous Bear
Long-running collection operation active since at least 2004. Focus on government, military, diplomatic, and healthcare targets across Europe, Central Asia, and the Middle East. Known for extraordinary persistence — Snake implants survived years on target systems. Notable TTPs include satellite communication hijacking for C2, watering-hole attacks, and a rootkit (UEFI implant) capable of surviving disk wipes. Associated with attacks on the German Bundestag (2015) and multiple EU foreign ministries.

### Gamaredon / Primitive Bear
Lower-sophistication but prolific FSB unit heavily focused on Ukrainian targets — government, military, police, and NGOs. Conducts mass spearphishing operations with remote access trojans. Volume-based operations providing broad collection across Ukrainian decision-making.

## SVR (Foreign Intelligence Service)

### APT29 / Cozy Bear / Midnight Blizzard
Russia's foreign intelligence service cyber arm, focused on long-term, stealthy collection against government, think-tank, and technology sector targets. Signature operations include: SolarWinds supply chain compromise (2019-2020, affecting 18,000 organisations including US Treasury, State Department, and NSA), sustained access to Microsoft's senior leadership email (2024), and penetration of multiple Western intelligence partner networks. TTPs: living off the land, abuse of legitimate cloud services (SharePoint, OneDrive) for C2, patient multi-year persistence.

## Integrated Operations Pattern
Russian cyber operations are nested within broader operations: cyber collection feeds physical sabotage targeting; influence operations amplify the effect of data breaches; pre-positioned access is held for use in conflict scenarios. Attribution is deliberately complicated by false-flag operations (Olympic Destroyer mimicked North Korean and Chinese TTPs). The escalation to physical sabotage in Europe (2022-2024) represents a qualitative shift in Russian operational willingness.

## Recent Campaigns (2023–2025)
- Sustained destructive attacks on Ukrainian power, water, and telecommunications infrastructure using Shahed-136 drones coordinated with cyber attacks
- Physical sabotage operations in EU member states: arson of logistics facilities, rail disruption, DHL parcel bomb campaigns
- Sandworm pre-positioning in European industrial control systems assessed ahead of potential conflict escalation
