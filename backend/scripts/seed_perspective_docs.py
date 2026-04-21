"""Seed perspective_documents table with official government reference documents.

Each perspective (us, norway, eu, china, russia) gets three documents covering
Political, Economic, and Military sections. Content represents key positions and
doctrines that a threat analyst would reference when interpreting state behaviour.

Two sources are combined:
  1. PERSPECTIVE_DOCUMENTS list below — hand-authored baseline entries.
  2. perspective_docs/ directory — one Markdown file per document with YAML
     frontmatter containing metadata (id, perspective, section, title, source,
     date_published). Files in this directory override list entries with the same id.

Usage:
    cd backend
    python scripts/seed_perspective_docs.py
"""

import os
import re
import sqlite3
from datetime import datetime, UTC
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = SCRIPT_DIR.parent
DATA_DIR = BACKEND_ROOT / "data"

PERSPECTIVE_DOCUMENTS: list[dict] = [
    # ── UNITED STATES ────────────────────────────────────────────────────────
    {
        "id": "us_nss_2022",
        "perspective": "us",
        "section": "political",
        "title": "US National Security Strategy 2022",
        "source": "White House, October 2022",
        "date_published": datetime(2022, 10, 12, tzinfo=UTC),
        "markdown_content": """# US National Security Strategy 2022

## Strategic Context
The 2022 NSS frames the coming decade as a "decisive decade" in which the US must out-compete China, constrain Russia, and address transnational threats including climate change and pandemic preparedness.

## Core Pillars

### Invest, Align, Compete
The US strategy is built on three pillars: investing in domestic competitiveness (infrastructure, semiconductors, clean energy), aligning with allies and partners, and competing with strategic rivals. The CHIPS and Science Act and Inflation Reduction Act are identified as national security investments.

### China as "Pacing Challenge"
China is explicitly named as the "most consequential geopolitical challenge" — the only country with both the intent to reshape the international order and the growing capability to do so. US strategy emphasises denial: denying China the ability to dominate the Indo-Pacific, block US access, or seize Taiwan by force.

### Russia as "Immediate Threat"
Russia is characterised as an "immediate and persistent threat" to European security following the 2022 invasion of Ukraine. US strategy commits to support Ukraine for as long as necessary and to strengthen NATO's eastern flank.

### Rules-Based International Order
The NSS emphasises defence of the rules-based international order — including freedom of navigation, peaceful resolution of disputes, and sovereignty — as a core US interest. This frames US actions in the South China Sea, Arctic, and Indo-Pacific.

## Implications for Intelligence Collection
US collection priorities flow from NSS pillars: Chinese military modernisation and Taiwan contingency planning, Russian hybrid warfare and nuclear signalling, supply chain resilience and technology competition, and partner nation vulnerabilities to adversary influence.
""",
    },
    {
        "id": "us_chips_economic_strategy",
        "perspective": "us",
        "section": "economic",
        "title": "US Technology and Economic Security Strategy",
        "source": "White House / Department of Commerce, 2022-2023",
        "date_published": datetime(2023, 2, 7, tzinfo=UTC),
        "markdown_content": """# US Technology and Economic Security Strategy

## CHIPS and Science Act (2022)
The CHIPS Act allocates $52.7 billion for domestic semiconductor manufacturing and R&D. The strategic rationale is reducing dependence on Taiwanese and East Asian chip production. Recipients are prohibited from expanding advanced chip manufacturing in China for 10 years. This is the largest US industrial policy intervention in decades.

## Export Controls: Advanced Semiconductors
The October 2022 and 2023 semiconductor export control rules block China's access to:
- Advanced semiconductors (below 14nm logic chips)
- Semiconductor manufacturing equipment from US and allied suppliers
- US persons working in Chinese advanced chip facilities

These controls are the most significant technology denial measure taken by the US since the Cold War-era CoCom restrictions and represent a deliberate attempt to deny China military-grade computing capability.

## Outbound Investment Screening
Executive Order 14105 (2023) restricts US investment in Chinese companies working on semiconductors, quantum computing, and AI — sectors with direct military applications. This extends US economic security policy from inbound screening (CFIUS) to outbound capital flows.

## Critical Minerals and Supply Chain Resilience
US strategy identifies critical minerals (rare earths, lithium, cobalt) as a strategic vulnerability given Chinese dominance of processing. The Inflation Reduction Act incentivises domestic and allied-nation supply chains for clean energy technology.

## Sanctions Enforcement
The US maintains comprehensive sanctions programmes against Russia (post-2022), Iran, North Korea, and Belarus. Secondary sanctions risk — penalising third-country entities that do business with sanctioned parties — is a key enforcement tool that creates significant compliance pressure on neutral countries.
""",
    },
    {
        "id": "us_nds_2022",
        "perspective": "us",
        "section": "military",
        "title": "US National Defense Strategy 2022",
        "source": "Department of Defense, October 2022",
        "date_published": datetime(2022, 10, 27, tzinfo=UTC),
        "markdown_content": """# US National Defense Strategy 2022

## Strategic Priorities
The 2022 NDS identifies China as the "pacing challenge" for US defence planning and Russia as an "acute threat." The strategy emphasises integrated deterrence — combining conventional military capability with nuclear, cyber, space, and economic tools — and building a resilient defense ecosystem.

## Integrated Deterrence
The NDS frames deterrence as requiring credibility across all domains simultaneously. Key elements:
- **Nuclear**: Modernisation of all three legs of the nuclear triad (ICBM, SSBN, bomber)
- **Conventional**: Maintaining ability to conduct two-front deterrence while prioritising Indo-Pacific
- **Cyber and Space**: Developing offensive and defensive capabilities in contested domains
- **Alliances**: NATO, QUAD, AUKUS, and bilateral treaty alliances as force multipliers

## Indo-Pacific Priority
The Indo-Pacific is the primary theatre for US defence planning. The US is developing Joint All-Domain Command and Control (JADC2) to enable integrated operations. AUKUS provides Australia with nuclear-powered submarines to extend deterrence. QUAD coordinates with India, Australia, and Japan on maritime security.

## NATO and European Security
Despite Indo-Pacific primacy, the NDS reaffirms US commitment to NATO's collective defence. Reinforcement of NATO's eastern flank (additional brigade-level presence in Poland, Baltic states, Romania), pre-positioning of equipment, and expanded allied exercises are identified as key investments.

## Nuclear Posture
The NPR (Nuclear Posture Review) within the NDS maintains a "sole purpose" aspiration but stops short of commitment, preserving US right to first use. The review upgrades concerns about China's nuclear expansion (estimated 1,000+ warheads by 2030) alongside Russia's continued nuclear coercion.
""",
    },

    # ── NORWAY ───────────────────────────────────────────────────────────────
    {
        "id": "norway_foreign_policy_white_paper",
        "perspective": "norway",
        "section": "political",
        "title": "Norwegian Foreign Policy White Paper: A World in Turmoil",
        "source": "Norwegian Ministry of Foreign Affairs, 2023",
        "date_published": datetime(2023, 11, 3, tzinfo=UTC),
        "markdown_content": """# Norwegian Foreign Policy: A World in Turmoil

## Strategic Context
Norway's 2023 foreign policy white paper was produced in the context of Russia's full-scale invasion of Ukraine, Finland and Sweden's NATO accession, and intensifying great-power competition. The paper frames the international order as under unprecedented pressure and positions Norway as a committed defender of the rules-based system.

## Core Foreign Policy Positions

### Russia
Russia is identified as Norway's primary strategic threat. The paper commits to sustained support for Ukraine, including military aid, economic support, and reconstruction contributions. Norway explicitly rejects any negotiated settlement that rewards Russian aggression.

### NATO and the High North
Norway's foreign policy is anchored in NATO. The paper emphasises Norway's role as a host nation for Allied forces, the importance of Article 5 guarantees, and the need for increased Allied presence in the High North (Arctic). Svalbard's status is described as a source of persistent tension with Russia.

### EU Relationship
Despite not being an EU member, Norway maintains close alignment with EU foreign policy through the EEA agreement. Norway has fully aligned with EU sanctions packages against Russia and actively coordinates with EU foreign policy positions on Ukraine.

### Development and Multilateralism
Norway maintains a strong commitment to development aid (consistently above 1% of GNI), multilateral institutions (UN, WTO), and international law. Norwegian foreign policy explicitly frames human rights and democracy as national security interests.

## Intelligence Implications
Norwegian foreign policy alignment with NATO and the EU means Norwegian intelligence services (PST, E-tjenesten) share collection priorities with Alliance partners. Norwegian political figures, businesses, and institutions with Russia or China connections are subject to enhanced scrutiny.
""",
    },
    {
        "id": "norway_petroleum_security",
        "perspective": "norway",
        "section": "economic",
        "title": "Norwegian Petroleum Sector: Security and Strategic Dimensions",
        "source": "Norwegian Ministry of Petroleum and Energy / PST, 2022",
        "date_published": datetime(2022, 3, 1, tzinfo=UTC),
        "markdown_content": """# Norwegian Petroleum Sector: Security and Strategic Dimensions

## Strategic Importance
Norway is Europe's largest natural gas supplier and a major oil exporter. Following the Nord Stream pipeline sabotage (September 2022) and Russian supply cuts, Norwegian gas became critical to European energy security. The Kårstø and Kollsnes processing plants, Sleipner and Troll fields, and Åsgard transport system carry strategic European significance.

## Threat Assessment
Following the Nord Stream sabotage, Norway elevated the threat level against petroleum infrastructure. PST and E-tjenesten assessed a heightened risk of Russian-linked sabotage or espionage against Norwegian energy assets. Specific threats include:
- Subsea pipeline and cable surveillance/sabotage by Russian vessels
- Cyber intrusions targeting SCADA systems at processing plants
- Insider threats through recruitment of employees with access to critical systems
- Physical sabotage by divers, ROVs, or small vessels

## Security Measures
Norway increased Coast Guard and Royal Norwegian Navy patrols around offshore installations after 2022. NATO allies conducted joint patrols. Equinor (state-controlled energy company) implemented enhanced cyber security standards across offshore OT networks.

## Government Petroleum Fund (Sovereign Wealth Fund)
The Government Pension Fund Global (oil fund) holds approximately $1.7 trillion in assets. Its investment policy excludes companies on ethical grounds, including companies involved in nuclear weapons, serious human rights violations, and since 2022, Russian companies. The fund's size relative to Norway's economy (approximately 5× GDP) creates unique strategic exposure.

## Economic Policy Implications
Norway's energy exports give it unusual leverage in European energy security discussions. Norwegian government policy must balance energy revenues, Allied solidarity obligations, and managing Russian intelligence interest in the sector's vulnerabilities.
""",
    },
    {
        "id": "norway_defence_white_paper_2023",
        "perspective": "norway",
        "section": "military",
        "title": "Norwegian Defence White Paper 2023",
        "source": "Norwegian Ministry of Defence, 2023",
        "date_published": datetime(2023, 4, 5, tzinfo=UTC),
        "markdown_content": """# Norwegian Defence White Paper 2023

## Strategic Environment Assessment
The 2023 white paper marks the most significant Norwegian defence policy shift since the Cold War. Russia is assessed as a direct military threat to Norway and NATO. The paper explicitly states that the period of relative stability in Europe has ended.

## Defence Capability Priorities

### Long-Range Strike and Air Defence
Norway has procured NASAMS air defence systems and F-35 fighters (52 aircraft). The 2023 paper commits to developing long-range precision strike capability targeting enemy logistics, C2, and air defence systems. This represents a departure from Norway's historically defence-oriented military posture.

### Naval Capability
Acquisition of four new Type 212CD submarines (joint with Germany) is the centrepiece of naval investment. These submarines will operate in the North Sea, Norwegian Sea, and Arctic — providing persistent undersea ISR and strike capability. Frigates (Nansen class) are being upgraded.

### High North (Arctic) Presence
The Finnmark Land Defence Brigade is being expanded and given enhanced anti-armour, air defence, and long-range artillery. Pre-positioned US Marine Corps equipment in Trøndelag is being expanded. Joint Norwegian-Allied Arctic exercise tempo is increasing.

### Defence Spending
Norway committed to increasing defence spending to 2% of GDP in 2024 (met) and has discussed increasing further to 2.5% by 2030. This represents a near-doubling of defence investment over the decade.

## Host Nation Support
Norway is investing in infrastructure to receive Allied reinforcements: port capacity at Ramsund, road and rail links to the north, and air base hardening at Evenes and Andøya.
""",
    },

    # ── EUROPEAN UNION ───────────────────────────────────────────────────────
    {
        "id": "eu_strategic_compass_2022",
        "perspective": "eu",
        "section": "political",
        "title": "EU Strategic Compass for Security and Defence 2022",
        "source": "European External Action Service / European Council, March 2022",
        "date_published": datetime(2022, 3, 21, tzinfo=UTC),
        "markdown_content": """# EU Strategic Compass for Security and Defence 2022

## Strategic Context
The Strategic Compass was adopted three weeks after Russia's full-scale invasion of Ukraine — the first EU strategic defence document produced in a wartime European context. It represents the most ambitious EU security and defence framework since the Common Foreign and Security Policy was established.

## Core Objectives

### Act
The EU commits to creating a 5,000-strong Rapid Deployment Capacity (EU RDC) for crisis response, increasing exercises and readiness, and developing a cyber rapid response capability.

### Secure
The EU commits to protecting EU citizens, infrastructure, and interests — including against hybrid threats, cyber attacks, and disinformation. The document identifies China and Russia as primary sources of hybrid threats.

### Invest
EU member states are urged to increase defence spending, close capability gaps (particularly in strategic enablers: airlift, space, cyber), and invest in EU defence industry. The European Defence Fund (EDF) provides €8 billion for R&D.

### Partner
The Strategic Compass emphasises partnerships — with NATO (primary framework), the UN, and strategic partners including the US, UK, and Indo-Pacific democracies. EU-NATO complementarity is stressed throughout.

## Russia as Systemic Threat
The document explicitly identifies Russia as the "most direct threat to the European security order." The EU committed to maintaining sanctions pressure and supporting Ukraine.

## China: Systemic Rival
China is named a "partner, competitor, and systemic rival" — the EU's three-category framework that allows economic engagement while acknowledging strategic competition.

## Intelligence Implications
The Strategic Compass creates formal EU structures for intelligence sharing (EU Intelligence and Situation Centre — EU INTCEN) and hybrid threat analysis. Member state intelligence services are expected to contribute assessments on threats to the European security order.
""",
    },
    {
        "id": "eu_critical_raw_materials_strategy",
        "perspective": "eu",
        "section": "economic",
        "title": "EU Critical Raw Materials Act and Economic Security Strategy",
        "source": "European Commission, 2023",
        "date_published": datetime(2023, 3, 16, tzinfo=UTC),
        "markdown_content": """# EU Economic Security Strategy and Critical Raw Materials

## Strategic Context
The EU's economic security strategy (2023) was driven by three shocks: the COVID-19 pandemic exposing supply chain vulnerabilities, Russian energy weaponisation demonstrating the risk of energy dependence, and Chinese export controls on gallium and germanium (2023) demonstrating technology supply chain risk.

## Critical Raw Materials Act
The CRMA sets binding targets:
- 10% of EU annual consumption to be extracted domestically by 2030
- 40% of EU annual consumption to be processed domestically by 2030
- No more than 65% of any critical raw material from a single third country

Critical raw materials identified include: lithium, cobalt, nickel, rare earth elements, silicon metal, and boron — all essential for clean energy and defence technologies.

## REPowerEU: Energy Diversification
Following Russian gas cutoff, the EU accelerated LNG import infrastructure, Norwegian gas pipeline expansion, and renewable energy deployment. Gas imports from Russia fell from ~40% to ~8% of EU consumption between 2022 and 2024. The EU sanctioned Russian LNG (partially) and is working toward full elimination.

## Economic Coercion Instrument
The EU adopted the Anti-Coercion Instrument (2023) enabling trade retaliation against countries using economic pressure to change EU policy — directly addressing Chinese and Russian economic coercion tactics (e.g., Chinese coercion of Lithuania over Taiwan representative offices).

## Technology Security
The EU has implemented export controls on dual-use items aligned with US and UK controls, strengthened foreign investment screening (FDI Regulation), and is developing a framework for outbound investment screening targeting sensitive technologies.
""",
    },
    {
        "id": "eu_military_capability_plan",
        "perspective": "eu",
        "section": "military",
        "title": "EU Military Capability Development and CSDP Operations",
        "source": "European Defence Agency / EEAS, 2023",
        "date_published": datetime(2023, 6, 19, tzinfo=UTC),
        "markdown_content": """# EU Military Capability Development

## Common Security and Defence Policy (CSDP)
The EU conducts military operations and civilian missions under CSDP. Current/recent operations include: EUFOR Althea (Bosnia-Herzegovina), EUNAVFOR Atalanta (anti-piracy Horn of Africa), EUNAVFOR ASPIDES (Red Sea), EUTM Mali/Somalia (training), and EUMAM Ukraine (military assistance to Ukraine).

## Capability Gaps
EU member states collectively have significant military capability but suffer from fragmentation, duplication, and interoperability gaps. Key capability gaps identified by the EDA:
- **Strategic enablers**: Airlift, aerial refuelling, satellite communications, strategic ISR
- **Air defence**: Insufficient coverage and interoperability; addressed partly by European Sky Shield Initiative
- **Precision strike**: Limited European long-range strike capability outside France and UK
- **Cyber**: Fragmented national capabilities; EU Cyber Rapid Response Teams partially address this

## European Defence Fund
The EDF (€8 billion, 2021-2027) funds collaborative R&D and procurement. Priority areas: next-generation fighter (FCAS), main battle tank (MGCS), drone warfare, cyber, and space.

## EU Rapid Deployment Capacity
The 5,000-strong EU RDC achieved initial operating capability in 2025. It can deploy for evacuation, stabilisation, and initial entry operations. Separate from NATO's Response Force but designed for complementary scenarios where NATO as a whole may not act.

## Nuclear Dimension
The EU has no nuclear capability. French strategic deterrence is the only European nuclear force within EU borders; France maintains that extended deterrence to European partners is a possibility for discussion but has not formalised commitments.
""",
    },

    # ── CHINA ────────────────────────────────────────────────────────────────
    {
        "id": "china_community_of_common_destiny",
        "perspective": "china",
        "section": "political",
        "title": "Chinese Political Doctrine: Community of Common Destiny",
        "source": "Chinese Communist Party / State Council, 2017-2023",
        "date_published": datetime(2022, 10, 16, tzinfo=UTC),
        "markdown_content": """# Chinese Political Doctrine: Community of Common Destiny

## Xi Jinping Thought and the "New Era"
Since Xi Jinping assumed consolidated power (2012 General Secretary, 2013 President), Chinese political doctrine has shifted from Deng Xiaoping's "bide your time, hide your strength" to active assertion of Chinese interests and values globally. The 20th Party Congress (2022) enshrined Xi's position with no successor designated, signalling long-term continuity.

## Community of Common Destiny for Mankind (人类命运共同体)
This concept frames China's preferred alternative to the US-led liberal international order:
- Multi-polarity replacing US "hegemony"
- Non-interference in internal affairs (explicitly rejecting democracy promotion and human rights conditionality)
- Mutual benefit through economic cooperation (Belt and Road framework)
- Chinese-defined global governance reform at the UN and other multilateral bodies
- Rejection of "Cold War mentality" — code for US-led alliance structures targeting China

## Taiwan: Red Line
Taiwan is explicitly framed as a core interest and a matter of domestic rather than international law. Xi has repeatedly stated that "reunification" is a "historical inevitability." The 2022 White Paper on Taiwan maintains military force remains an option.

## Wolf Warrior Diplomacy
China's diplomatic posture shifted markedly after 2017 toward assertive, sometimes aggressive public confrontations with critics — named "wolf warrior diplomacy" after a popular nationalist film. This includes threatening economic retaliation against countries that criticise Chinese policies (Lithuania, Australia, South Korea) and personal attacks on foreign officials.

## Intelligence Implications
Chinese political doctrine frames any criticism of CCP governance (Xinjiang, Hong Kong, Tibet, Taiwan) as external interference threatening China's sovereignty. This framing is used to justify counter-intelligence operations against diaspora communities, academic critics, and foreign politicians deemed hostile.
""",
    },
    {
        "id": "china_bri_economic_strategy",
        "perspective": "china",
        "section": "economic",
        "title": "Belt and Road Initiative: Strategic Economic Framework",
        "source": "State Council of the People's Republic of China, 2015-2023",
        "date_published": datetime(2021, 3, 5, tzinfo=UTC),
        "markdown_content": """# Belt and Road Initiative: Strategic Economic Framework

## Overview
The Belt and Road Initiative (BRI), launched in 2013, is China's signature economic diplomacy programme. It involves Chinese state-backed financing for infrastructure projects — ports, railways, power plants, telecoms — across Asia, Africa, the Middle East, and Europe. As of 2023, over 150 countries have signed BRI cooperation agreements. Total committed investment is estimated at $838 billion, though actual disbursement is lower.

## Strategic Logic
The BRI serves multiple Chinese strategic objectives:
- **Overcapacity export**: Deploying excess capacity in Chinese construction, steel, and materials industries
- **Resource access**: Securing supply chains for raw materials (oil, gas, minerals) essential for Chinese industry
- **Market access**: Opening new markets for Chinese goods and services
- **Diplomatic leverage**: Creating economic dependencies that generate political support at the UN and other multilateral forums
- **Military access**: Ports and airstrips financed by China can provide PLA logistics access (Djibouti naval base is the clearest example; Hambantota port in Sri Lanka is often cited though disputed)

## Debt Trap Concerns
Western and regional analysts have raised concerns about "debt trap diplomacy" — structuring loans to create unsustainable debt obligations that allow China to extract strategic assets as collateral. Sri Lanka's Hambantota port is the most cited example. China disputes this characterisation.

## BRI Adaptation (2.0)
Since 2021, China has rebranded BRI with greater emphasis on "Green BRI" (clean energy) and "Digital Silk Road" (telecoms, data centres, surveillance technology export). The digital component is particularly significant: Huawei, ZTE, and Alibaba Cloud are building digital infrastructure across BRI countries, creating persistent access to communications and data.

## Intelligence Implications
BRI infrastructure creates Chinese presence in strategic locations globally. Port access provides PLA logistics options. Telecoms infrastructure provides collection access. Financial dependencies reduce recipient country willingness to take positions adverse to Chinese interests in multilateral forums.
""",
    },
    {
        "id": "china_military_strategy_2015",
        "perspective": "china",
        "section": "military",
        "title": "China's Military Strategy (Defence White Paper 2015 + PLA Modernisation)",
        "source": "State Council Information Office / PLA, 2015-2023",
        "date_published": datetime(2023, 8, 10, tzinfo=UTC),
        "markdown_content": """# China's Military Strategy and PLA Modernisation

## Active Defence Doctrine
China's official military doctrine is "active defence" — a defensive strategic posture with offensive tactics at the operational and campaign level. In practice, this means: China does not initiate conflict, but once it begins, PLA will take the initiative. This doctrine justifies pre-emptive strikes on adversary capabilities (airfields, carrier groups) as defensive if conflict is "imminent."

## Strategic Goals: 2035 and 2049
Xi Jinping has set two military modernisation milestones:
- **2027**: PLA capability to successfully execute a Taiwan forced reunification operation
- **2035**: PLA fully modernised with world-class capabilities in all domains
- **2049**: PLA as one of the world's premier military forces (centenary of PRC founding)

## Nuclear Expansion
China is expanding its nuclear arsenal from an estimated 500 warheads (2023) toward an estimated 1,000-1,500 by 2030 and potentially 1,500-2,000 by 2035. New missile fields in Xinjiang and Gansu house hundreds of new DF-41 ICBM silos. China is developing a full nuclear triad (land, sea, air). This represents the most rapid nuclear build-up since the Cold War.

## A2/AD (Anti-Access/Area Denial)
China has invested heavily in capabilities designed to deny US forces access to the Western Pacific:
- DF-21D and DF-26 anti-ship ballistic missiles targeting carrier groups
- Extensive air defence network (HQ-9 and derivatives)
- Undersea warfare capability (Type 095 attack submarines)
- Counter-space and cyber capabilities targeting GPS, satellite communications

## Taiwan Contingency
PLA exercises increasingly simulate large-scale joint operations across the Taiwan Strait: air superiority, amphibious assault, blockade operations, and missile strikes on Taiwan's command and military infrastructure. The 2022 exercises following Pelosi's Taiwan visit demonstrated PLA ability to simulate full encirclement.

## Intelligence Implications
PLA modernisation is proceeding faster than many Western assessments predicted a decade ago. Chinese military expenditure is significantly underreported in official figures. The nuclear expansion forces a revision of US strategic planning assumptions. Volt Typhoon pre-positioning in US critical infrastructure is integrated into PLA warfighting doctrine as a tool for deterrence and coercion.
""",
    },

    # ── RUSSIA ───────────────────────────────────────────────────────────────
    {
        "id": "russia_foreign_policy_concept_2023",
        "perspective": "russia",
        "section": "political",
        "title": "Russian Foreign Policy Concept 2023",
        "source": "Russian Federation Presidential Decree No. 229, March 2023",
        "date_published": datetime(2023, 3, 31, tzinfo=UTC),
        "markdown_content": """# Russian Foreign Policy Concept 2023

## Strategic Framework
The 2023 Foreign Policy Concept is the most explicit articulation of Russian ideology since the Soviet collapse. It frames Russia as a "civilisational state" leading the "Russian world" (Russkiy Mir) and positions the West — particularly the US and its "satellites" — as existential adversaries pursuing Russia's "weakening, division and destruction."

## Anti-Western Framing
The concept explicitly identifies the US as seeking to "preserve global hegemony" through "divide and rule" tactics. NATO is characterised as a destabilising force that drew closer to Russian borders in violation of alleged (unwritten) commitments. The EU is seen as a tool of American strategy rather than an independent actor.

## Sovereign Democracy
Russia's preferred international order is "multi-polar" — replacing US-led unipolarity with a system in which Russia, China, and "the Global South" constitute co-equal poles. Russia frames its opposition to Western-backed democracy promotion as defence of sovereignty and non-interference.

## "Russian World" and Near Abroad
The concept asserts Russia's right to protect "Russian-speaking populations" abroad — the legal and ideological basis for interventions in Ukraine (2014, 2022), Georgia (2008), and Moldova. This doctrine provides justification for destabilisation operations against any post-Soviet state deemed to be "drifting" toward the West.

## China Partnership
Russia-China relations are described as a "comprehensive strategic partnership" with "no limits" — not a military alliance but a convergence of interests in opposing US dominance. Russia frames this as a cornerstone of the emerging multi-polar order.

## Intelligence Implications
The 2023 concept provides the ideological framework for Russian intelligence operations: undermining NATO solidarity, supporting anti-Western political movements in Europe, destabilising post-Soviet states, and cultivating "Global South" opposition to Western sanctions.
""",
    },
    {
        "id": "russia_economic_warfare_doctrine",
        "perspective": "russia",
        "section": "economic",
        "title": "Russian Economic Coercion and Sanctions Circumvention",
        "source": "Assessment based on Russian Central Bank, Finance Ministry, and open-source analysis, 2022-2024",
        "date_published": datetime(2023, 9, 14, tzinfo=UTC),
        "markdown_content": """# Russian Economic Coercion and Sanctions Circumvention

## Weaponisation of Energy Supply
Prior to the 2022 invasion, Russia supplied ~40% of EU natural gas and ~25% of EU oil. Russia demonstrated willingness to manipulate energy supply as geopolitical leverage through: the 2006 and 2009 Ukraine gas crises, gradual Nord Stream gas reductions in 2021-2022 preceding the invasion, and complete cutoff of supply to most EU members by late 2022. This strategy ultimately failed — EU diversification accelerated and dependency was reduced.

## Sanctions Adaptation and Circumvention
In response to unprecedented Western sanctions (asset freezes, SWIFT exclusions, export controls), Russia has implemented:
- **Parallel import schemes**: Importing sanctioned goods through Kazakhstan, Armenia, Turkey, UAE, and China as intermediaries
- **Yuan/Rupee trade settlement**: Redirecting trade to non-dollar currencies and non-Western payment systems (MIR, CIPS)
- **Shadow fleet expansion**: Operating 600+ vessels outside Western-insured shipping lanes to export oil above the price cap
- **Domestic substitution**: Accelerated import replacement (with mixed results; semiconductor-dependent industries have suffered)

## War Economy Shift
Russia has pivoted to a war economy: defence spending reached 6% of GDP in 2024 (vs. 3.9% pre-war), industrial production capacity is being redirected to military outputs, and labour market controls are preventing mass flight of skilled workers.

## Financial Vulnerability
Frozen Russian state assets (~$300 billion held in Western central banks, primarily Euroclear in Belgium) represent both a Russian vulnerability and a legal challenge for Western governments seeking to use these funds for Ukraine reconstruction.

## Intelligence Implications
Russia's economic adaptation has been more successful than Western planners anticipated. Sanctions have imposed significant costs but have not collapsed the Russian economy. The circumvention network — particularly through Central Asian and Caucasian intermediaries — supplies dual-use components for weapons production.
""",
    },
    {
        "id": "russia_military_doctrine_posture",
        "perspective": "russia",
        "section": "military",
        "title": "Russian Military Doctrine and Operational Posture",
        "source": "Russian Security Council / General Staff, 2014-2023",
        "date_published": datetime(2022, 11, 2, tzinfo=UTC),
        "markdown_content": """# Russian Military Doctrine and Operational Posture

## Doctrine Overview
Russian military doctrine (2014, updated 2022) frames NATO and the US as existential threats and authorises nuclear use in conventional conflict scenarios where "the very existence of the state is under threat." This deliberately ambiguous threshold is a calculated escalation management tool — designed to deter NATO intervention in Russian conflicts with non-NATO states.

## Nuclear Signalling and Escalation Management
Russia's nuclear signalling during the Ukraine war — deploying tactical nuclear weapons to Belarus (2023), periodic references to nuclear use thresholds — is deliberate and serves three purposes:
1. Deterring NATO direct intervention in Ukraine
2. Slowing or stopping Western weapons deliveries to Ukraine
3. Demonstrating resolve to domestic and international audiences

Russia maintains approximately 1,900 deployed strategic warheads and 2,000+ tactical nuclear weapons (non-strategic), the world's largest tactical nuclear arsenal.

## New Generation Warfare
The Gerasimov-attributed "new generation warfare" concept (not actually a formal Gerasimov doctrine, but a Western analytical frame) describes Russian approach: coordinated use of political subversion, cyber operations, information operations, and conventional military forces. The 2022 invasion demonstrated both the ambitions and limits of this approach.

## Lessons from Ukraine
The Ukraine war has exposed significant Russian military weaknesses: C2 failures, logistics bottlenecks, leadership casualties (battalion and brigade commanders killed at unprecedented rates), and insufficient combined-arms integration. Russia has adapted: increased use of FPV drones, electronic warfare, and depth in defensive lines. Force regeneration through conscription and mobilisation has restored numerical strength at reduced quality.

## Northern Fleet and Arctic Posture
The Northern Fleet (elevated to Military District status in 2021) is Russia's premier force projection asset. Ballistic missile submarines (SSBNs) based on the Kola Peninsula carry the majority of Russia's second-strike capability. The Northern Fleet's conventional forces provide Arctic military dominance and coastal defence.

## Intelligence Implications
Russia's demonstrated willingness to use nuclear signalling as a coercive tool — and the West's partial response (constraining some weapons transfers) — has reinforced Russian confidence in escalation management. Russian conventional military performance in Ukraine provides actionable data on capability gaps that NATO planners and adversary intelligence services are exploiting.
""",
    },
]


DOCS_DIR = SCRIPT_DIR / "perspective_docs"


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """Split YAML frontmatter from markdown body. Returns (meta, body)."""
    if not text.startswith("---"):
        return {}, text
    end = text.index("---", 3)
    fm_block = text[3:end].strip()
    body = text[end + 3:].strip()
    meta: dict = {}
    for line in fm_block.splitlines():
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        meta[key.strip()] = val.strip().strip('"')
    return meta, body


def _load_markdown_docs() -> list[dict]:
    """Load all .md files from perspective_docs/ as seed entries."""
    docs = []
    for path in sorted(DOCS_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        meta, body = _parse_frontmatter(text)
        if not meta.get("id"):
            continue
        raw_date = meta.get("date_published", "2000-01-01")
        parts = [int(p) for p in raw_date.split("-")]
        date_published = datetime(*parts, tzinfo=UTC)
        docs.append({
            "id": meta["id"],
            "perspective": meta["perspective"],
            "section": meta["section"],
            "title": meta["title"],
            "source": meta.get("source", ""),
            "date_published": date_published,
            "markdown_content": body,
        })
    return docs


def seed() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    db_path = Path(os.getenv("KNOWLEDGE_DB_PATH", str(DATA_DIR / "knowledge.db")))
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS perspective_documents (
            id               TEXT PRIMARY KEY,
            perspective      TEXT NOT NULL,
            section          TEXT NOT NULL,
            title            TEXT NOT NULL,
            source           TEXT,
            date_published   DATETIME NOT NULL,
            markdown_content TEXT NOT NULL DEFAULT '',
            is_active        INTEGER NOT NULL DEFAULT 1
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_persp_docs_perspective ON perspective_documents(perspective)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_persp_docs_section ON perspective_documents(section)")

    # Merge: file-based docs override list entries with the same id
    file_docs = _load_markdown_docs()
    file_ids = {d["id"] for d in file_docs}
    all_docs = [d for d in PERSPECTIVE_DOCUMENTS if d["id"] not in file_ids] + file_docs

    inserted = 0
    for doc in all_docs:
        conn.execute(
            """INSERT INTO perspective_documents
                   (id, perspective, section, title, source, date_published, markdown_content, is_active)
               VALUES (?, ?, ?, ?, ?, ?, ?, 1)
               ON CONFLICT(id) DO UPDATE SET
                   perspective=excluded.perspective,
                   section=excluded.section,
                   title=excluded.title,
                   source=excluded.source,
                   date_published=excluded.date_published,
                   markdown_content=excluded.markdown_content
            """,
            (
                doc["id"],
                doc["perspective"],
                doc["section"],
                doc["title"],
                doc.get("source"),
                doc["date_published"].isoformat(),
                doc["markdown_content"],
            ),
        )
        inserted += 1

    conn.commit()
    conn.close()
    print(f"Seeded {inserted} perspective documents into {db_path}")
    print(f"  {len(file_docs)} from perspective_docs/ markdown files")
    print(f"  {inserted - len(file_docs)} from inline PERSPECTIVE_DOCUMENTS list")


if __name__ == "__main__":
    seed()
