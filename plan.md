# MCP Threat Intelligence MVP - Project Plan

> **Purpose**: This document provides structured context for AI assistants and developers working on this project. It defines goals, constraints, architecture, and development guidelines.

---

## Project Identity

| Field | Value |
|-------|-------|
| **Project Name** | MCP Threat Intelligence MVP |
| **Full Title** | Integrating Agentic AI via Model Context Protocol (MCP) into the Threat Intelligence Cycle |
| **Type** | Proof of Concept / MVP Study (Hybrid: Project + Research) |
| **Duration** | February 1, 2025 - May 1, 2025 (13 weeks) |
| **Team Size** | 4 developers |
| **Methodology** | Sprints with Kanban, Test-Driven Development (TDD) |
| **Industry Partners** | Telenor ASA, Storebrand Group, Aker ASA |
| **AI Lab Access** | Nvidia L40s (48GB), RTX A6000 (48GB), GV100 (32GB), 2080Ti/1080Ti (11GB) — dynamically allocated |

---

## Research Questions

### Primary Research Question (RQ1)
> **Can MCP effectively integrate AI capabilities into the Direction, Collection, Processing, and Analysis phases of the Threat Intelligence cycle?**

| Sub-question | Evaluation Method |
|--------------|-------------------|
| RQ1.1: Which MCP primitives (Tools, Resources, Prompts) are most effective for each phase? | Implementation analysis, usage logging |
| RQ1.2: What are the technical limitations of MCP for TI workflows? | Documentation of blockers and workarounds |
| RQ1.3: Does dual AI review reduce hallucinations compared to single AI output? | Error rate comparison, review logs analysis |

### Secondary Research Question (RQ2)
> **How can human-in-the-loop controls be designed to maintain analyst oversight in AI-assisted TI workflows?**

| Sub-question | Evaluation Method |
|--------------|-------------------|
| RQ2.1: What level of AI autonomy is appropriate for each TI phase? | User testing feedback, observation |
| RQ2.2: How should AI suggestions be presented to maximize analyst trust? | User testing, SUS questionnaire |
| RQ2.3: What approval mechanisms balance control with efficiency? | Task completion time, user feedback |

---

## Research Evaluation Methods

### RQ1: Technical Feasibility Evaluation

#### RQ1.1: MCP Primitives Effectiveness

**How we answer this:**

| Data Source | What we collect | Analysis |
|-------------|-----------------|----------|
| Implementation log | Which primitives used per phase | Count usage frequency |
| Code review | Lines of code per primitive | Measure implementation complexity |
| Developer notes | Challenges and successes | Qualitative assessment |

**Deliverable:** Table showing which primitives (Tools, Resources, Prompts) were used in each phase and why.

```
Example output:
┌─────────────┬───────────┬────────────┬────────────┐
│ Phase       │ Tools     │ Resources  │ Prompts    │
├─────────────┼───────────┼────────────┼────────────┤
│ Direction   │ 2 used    │ 1 used     │ 2 used     │
│ Collection  │ 4 used    │ 3 used     │ 1 used     │
│ Processing  │ 5 used    │ 4 used     │ 3 used     │
└─────────────┴───────────┴────────────┴────────────┘
```

#### RQ1.2: Technical Limitations

**How we answer this:**

| Data Source | What we collect | Analysis |
|-------------|-----------------|----------|
| Development log | Blockers encountered | Categorize by type |
| GitHub issues | Technical problems | Count and classify |
| Workarounds | Solutions implemented | Document alternatives |

**Deliverable:** List of limitations with severity and workarounds.

```
Example output:
| Limitation | Severity | Workaround |
|------------|----------|------------|
| MCP timeout on large datasets | Medium | Chunked processing |
| No native streaming support | Low | WebSocket wrapper |
```

#### RQ1.3: Dual AI Hallucination Reduction

**How we answer this:**

| Metric | How measured | Target |
|--------|--------------|--------|
| Review correction rate | Count AI #2 corrections / total outputs | Track % |
| Error types | Categorize: factual, unsupported, inconsistent | Distribution |
| Retry success rate | Corrections that improved output | Track % |

**Data collection (automatic logging):**

```json
{
  "workflow_id": "wf-001",
  "phase": "Processing",
  "ai_1_output": "...",
  "ai_2_review": {
    "errors_found": 2,
    "error_types": ["unsupported_claim", "factual_error"],
    "retry_triggered": true
  },
  "ai_1_retry_output": "...",
  "ai_2_final_review": {
    "errors_found": 0,
    "approved": true
  }
}
```

**Analysis:**
1. Run 20+ complete workflows with diverse inputs
2. Calculate: `correction_rate = workflows_with_corrections / total_workflows`
3. Compare expert evaluation of raw vs. reviewed outputs
4. Document types of errors caught

**Deliverable:** Statistics showing dual AI effectiveness.

```
Example output:
- Total workflows analyzed: 25
- Workflows with AI #2 corrections: 18 (72%)
- Error types caught:
  - Unsupported claims: 12 (40%)
  - Factual errors: 8 (27%)
  - Inconsistencies: 10 (33%)
- Expert assessment: Reviewed outputs rated higher in 85% of cases
```

---

### RQ2: Human-AI Collaboration Evaluation

#### RQ2.1: Appropriate AI Autonomy

**How we answer this:**

| Method | Description | Data collected |
|--------|-------------|----------------|
| User observation | Watch users interact with system | Where they intervene, where they trust AI |
| Post-task interview | Ask about comfort level | Qualitative feedback |
| Intervention logging | Track approve/reject/modify actions | Quantitative data |

**Questions to ask users:**
- "At which points did you feel you needed more control?"
- "Where did the AI have too little/too much autonomy?"
- "What would you change about the approval process?"

**Deliverable:** Recommendations for autonomy level per phase.

#### RQ2.2: AI Suggestion Presentation

**How we answer this:**

| Method | Description | Data collected |
|--------|-------------|----------------|
| A/B testing (if time) | Compare different UI layouts | Preference data |
| Think-aloud testing | Users verbalize thoughts while using | Confusion points |
| SUS questionnaire | Standard usability scale | Score 0-100 |

**System Usability Scale (SUS):**
10 questions, users rate 1-5. Examples:
- "I found the system unnecessarily complex"
- "I felt confident using the system"
- "I needed to learn a lot before I could use this system"

**Deliverable:** SUS score + specific UI improvement recommendations.

#### RQ2.3: Approval Mechanism Efficiency

**How we answer this:**

| Metric | How measured |
|--------|--------------|
| Task completion time | Time from start to final output |
| Approval clicks | Number of approve/reject actions needed |
| User satisfaction | Post-task rating (1-5) |

**Deliverable:** Time/effort data with user satisfaction correlation.

---

### User Testing Protocol

#### Participants
| Group | Number | Purpose |
|-------|--------|---------|
| Industry partners (Telenor, Storebrand, Aker) | 3-5 | Expert TI analyst feedback |
| Supervisors | 2-3 | Academic evaluation |
| Team members (internal) | 4 | Early testing, iteration |

#### Testing Sessions

**Session structure (45-60 min per participant):**

| Phase | Duration | Activity |
|-------|----------|----------|
| Introduction | 5 min | Explain purpose, get consent |
| Training | 5 min | Brief system overview |
| Task 1 | 15 min | Complete Direction phase |
| Task 2 | 15 min | Complete full workflow |
| Questionnaire | 10 min | SUS + custom questions |
| Interview | 10 min | Open-ended feedback |

**Tasks for users:**

| Task | Description | What we measure |
|------|-------------|-----------------|
| Task 1 | "Investigate recent APT29 activity targeting Nordic countries" | Direction phase usability |
| Task 2 | "Complete full workflow and generate report" | End-to-end experience |
| Task 3 | "Review AI suggestions and make corrections" | Human-in-the-loop effectiveness |

#### Data Collection Forms

**Observation form (researcher fills during session):**
```
Participant: ___
Date: ___
Task: ___

[ ] User hesitated at: ___
[ ] User asked for help at: ___
[ ] User expressed confusion about: ___
[ ] User made error at: ___
[ ] Time to complete: ___ minutes
[ ] Approvals: ___ Rejections: ___ Modifications: ___

Notes:
```

**Post-task questionnaire:**
1. SUS (10 standard questions)
2. "The AI suggestions were helpful" (1-5)
3. "I felt in control of the process" (1-5)
4. "The reasoning explanations were clear" (1-5)
5. "I would use this system in my work" (1-5)
6. Open: "What would you improve?"

---

## UI Design Process

### Design Phases

```
┌─────────────────────────────────────────────────────────────┐
│  LOW-FIDELITY (Sprint 1-2)                                  │
│  ─────────────────────────────────────────────────────────  │
│  Deliverables:                                              │
│  - Paper sketches of main screens                           │
│  - Whiteboard workflow diagrams                             │
│  - Basic wireframes (Figma or draw.io)                      │
│                                                             │
│  Focus: Layout, information architecture, user flow         │
│  Test with: Team members, supervisor                        │
│  Feedback method: Informal review, discussion               │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  MEDIUM-FIDELITY (Sprint 2-3)                               │
│  ─────────────────────────────────────────────────────────  │
│  Deliverables:                                              │
│  - Clickable Figma prototype                                │
│  - All main screens designed                                │
│  - Basic styling and real text                              │
│                                                             │
│  Focus: Navigation, interactions, component design          │
│  Test with: Supervisor, 1-2 industry partners               │
│  Feedback method: Walkthrough session, notes                │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  HIGH-FIDELITY (Sprint 4-5)                                 │
│  ─────────────────────────────────────────────────────────  │
│  Deliverables:                                              │
│  - Implemented React components                             │
│  - Full TailwindCSS styling                                 │
│  - Working interactions                                     │
│                                                             │
│  Focus: Visual polish, responsiveness, accessibility        │
│  Test with: All industry partners                           │
│  Feedback method: Formal user testing sessions              │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  USER TESTING & ITERATION (Sprint 5-6)                      │
│  ─────────────────────────────────────────────────────────  │
│  Deliverables:                                              │
│  - User testing reports                                     │
│  - SUS scores                                               │
│  - Iteration based on feedback                              │
│                                                             │
│  Focus: Validation, final improvements                      │
│  Test with: Industry partners, final demo                   │
│  Feedback method: Formal sessions, questionnaires           │
└─────────────────────────────────────────────────────────────┘
```

### Screens to Design

| Screen | Priority | Sprint |
|--------|----------|--------|
| Direction: Chat dialogue | Must Have | 2 |
| Direction: PIR review | Must Have | 2 |
| Direction: Perspective selection | Must Have | 2 |
| Direction: Source selection | Must Have | 2 |
| Collection: Data review | Must Have | 3 |
| Collection: Approve/reject UI | Must Have | 3 |
| Processing: Correlation view | Must Have | 4 |
| Processing: MITRE mapping | Must Have | 4 |
| Processing: Tactical perspective summaries | Must Have | 4 |
| Analysis: Strategic assessment view | Must Have | 5 |
| Analysis: Key findings + confidence levels | Must Have | 5 |
| Analysis: Recommendations per perspective | Must Have | 5 |
| Output: Report view | Must Have | 5 |
| Output: Reasoning toggle | Must Have | 5 |
| Output: Download/history | Must Have | 5 |
| Data import: File upload | Must Have | 1 |
| Progress bar | Must Have | 3 |
| Language toggle | Should Have | 6 |

---

## Project Goals

### Primary Objective
Demonstrate that AI can be integrated into the first four phases of the Threat Intelligence (TI) cycle — Direction, Collection, Processing, and Analysis — using the Model Context Protocol (MCP), while maintaining human oversight at all decision points.

### Success Criteria
1. **Continuous Workflow**: System flows through Direction → Collection → Processing → Analysis without interruption
2. **Human-in-the-Loop**: Humans have approval/rejection control at every phase transition and critical decision
3. **Dual AI Validation**: Second AI instance reviews outputs to reduce hallucinations
4. **Functional MCP Implementation**: Working Tools, Resources, and Prompts primitives
5. **Working Web Application**: Usable interface for analyst interaction
6. **Dual Mode Support**: System works both online (cloud API) and offline (local models)
7. **Geographic Perspectives with Strategic Intelligence**: Analysts can view both tactical and strategic summaries through different national lenses
8. **Validated Usability**: User testing with SUS score ≥ 68 (above average)

### Non-Goals (Out of Scope for MVP)
- Dissemination phase (phase 5 of TI cycle)
- MCP Sampling primitive
- User authentication/authorization
- Production deployment
- Multi-tenant support
- Mobile responsive design

---

## Functional Requirements

### Core Workflow Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| F01 | Human must be involved in all phases (Direction, Collection, Processing, Analysis) | Must Have |
| F02 | Human can review/approve/reject with feedback after each AI output | Must Have |
| F03 | Direction phase uses dialogue to understand user goals (AI asks clarifying questions) | Must Have |
| F04 | System retrieves data from file upload, AlienVault OTX, and MISP | Must Have |
| F05 | System formats data into human-readable format | Must Have |
| F06 | System summarizes data and provides output | Must Have |
| F07 | System shows AI reasoning (summarized and complete versions) | Must Have |
| F08 | Second AI instance reviews each phase output for errors/hallucinations | Must Have |
| F09 | AI auto-retries on review errors; retry process logged in reasoning file | Must Have |
| F10 | User can select geographic perspectives (US, Norway, China, EU) or none (Neutral) | Must Have |
| F11 | Each perspective generates both a tactical summary and a strategic intelligence assessment | Must Have |
| F12 | System works online (Gemini API) and offline (local small model) | Must Have |
| F13 | Output saved as JSON and PDF files locally | Must Have |
| F14 | User can download report as PDF | Must Have |
| F15 | User can download previous reports (max 3 stored) | Must Have |
| F16 | Each output cites the sources used | Must Have |
| F17 | User can start AI dialogue with 1 click and text input | Must Have |
| F18 | UI supports Norwegian and English language switching | Should Have |
| F19 | AI output generated in user's selected language | Should Have |
| F20 | Multiple AI agents debate from different perspectives | Deferred |
| F21 | System logs AI review corrections for research analysis | Must Have |
| F22 | Analysis phase synthesizes Processing output into analytical judgments and recommendations | Must Have |
| F23 | Analysis phase produces finished intelligence: key findings, confidence levels, recommendations | Must Have |

### Web Interface Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| W01 | File upload button for data import (JSON, CSV, PDF, TXT) | Must Have |
| W02 | Start/stop controls for AI generation | Must Have |
| W03 | Options for report generation settings | Must Have |
| W04 | Toggle between output view and reasoning view | Must Have |
| W05 | Download button for output (JSON, PDF) | Must Have |
| W06 | Progress bar showing workflow status | Must Have |
| W07 | Data source selection (Upload, OTX, MISP) | Must Have |
| W08 | Geographic perspective selection (checkboxes/buttons) | Must Have |
| W09 | Language toggle (Norwegian/English) | Should Have |
| W10 | Chat-like interface for Direction phase dialogue | Must Have |

### Data Import Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| D01 | User can upload TI data before workflow starts | Must Have |
| D02 | System validates imported data format | Must Have |
| D03 | Support for OTX exports (JSON) | Must Have |
| D04 | Support for MISP events (JSON) | Must Have |
| D05 | Support for custom IOC lists (CSV) | Should Have |
| D06 | Support for attachments (PDF, TXT) | Should Have |

---

## Non-Functional Requirements

### Usability

| ID | Requirement | Target |
|----|-------------|--------|
| NF01 | User can complete workflow without training | Yes |
| NF02 | Start AI dialogue with 1 click + text input | Yes |
| NF03 | Correct and helpful error messages on failures | Yes |
| NF04 | Progress bar shows current phase and status | Yes |
| NF05 | SUS usability score | ≥ 68 (above average) |

### Performance

| ID | Requirement | Target |
|----|-------------|--------|
| NF06 | Workflow initialization time | â‰¤ 5 seconds |
| NF07 | Page load time | â‰¤ 3 seconds |
| NF08 | AI response time | No hard limit; progress bar shows status |

### Design

| ID | Requirement | Target |
|----|-------------|--------|
| NF09 | Designed for desktop/web use (PC) | Yes |
| NF10 | Minimum supported screen width | 1024px |
| NF11 | WCAG 2.1 Level AA accessibility | Yes |

### Storage

| ID | Requirement | Target |
|----|-------------|--------|
| NF12 | Maximum reports stored on server | 3 |
| NF13 | Report formats | JSON + PDF |
| NF14 | Reasoning file includes AI review notes | Yes |
| NF15 | Review notes only visible in reasoning file (not main output) | Yes |

### Localization

| ID | Requirement | Target | Priority |
|----|-------------|--------|----------|
| NF16 | UI language support | Norwegian + English | Should Have |
| NF17 | AI output language | Matches UI language | Should Have |

### Testing

| ID | Requirement | Target | Minimum |
|----|-------------|--------|---------|
| NF18 | Unit test coverage (TDD) | 80% | 70% |
| NF19 | Integration test coverage (TDD) | 80% | 70% |
| NF20 | E2E critical path coverage | 100% | 100% |

### Research Data Collection

| ID | Requirement | Target |
|----|-------------|--------|
| NF21 | Log all AI review corrections | Yes |
| NF22 | Log user approve/reject/modify actions | Yes |
| NF23 | Log task completion times | Yes |

---

## Architecture Overview

### Dual AI System

The system uses two AI instances to reduce hallucinations:

```
┌─────────────────────────────────────────────────────────────┐
│  DUAL AI REVIEW FLOW                                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  AI Instance #1        AI Instance #2         Final Output  │
│  (Generate)      →     (Review)         →     to Human      │
│       │                     │                    │          │
│       ▼                     ▼                    ▼          │
│  Creates output       Checks for:          Reworked output  │
│                       - Hallucinations     (clean version)  │
│                       - Errors                   +          │
│                       - Inconsistencies    Review notes     │
│                             │              stored in        │
│                             ▼              reasoning file   │
│                       If errors found:                      │
│                       → Feedback to AI #1                   │
│                       → Auto-retry                          │
│                       → Log for RQ1.3                       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

| Mode | AI Instance #1 (Generate) | AI Instance #2 (Review) |
|------|--------------------------|------------------------|
| Online | Gemini 2.5 Flash | Gemini 2.5 Flash (separate instance) |
| Offline (Tier 1) | DeepSeek-R1 32B / DeepSeek-V3 (quantized) | Llama 3.3 70B (quantized) |
| Offline (Tier 2) | DeepSeek-R1 14B | Llama 3.2 11B |
| Offline (Tier 3 / Fallback) | Phi-3 Mini (3.8B) | Same model (separate instance) |

**Key Points:**
- Same model, two separate instances
- Review runs sequentially (not parallel) to fit in 8-12GB VRAM
- User only sees final reworked output
- Review notes stored in reasoning file for transparency
- All corrections logged for RQ1.3 analysis

### System Modes

```
┌─────────────────────────────────────────────────────────────┐
│  ONLINE MODE                                                │
│  ─────────────────────────────────────────────────────────  │
│  - Gemini 2.5 Flash API (both instances)                    │
│  - Live OSINT queries (OTX, MISP APIs)                      │
│  - Real-time threat intelligence                            │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  OFFLINE MODE                                               │
│  ─────────────────────────────────────────────────────────  │
│  - Local model via Ollama or vLLM (both instances)          │
│  - Pre-loaded TI data (JSON, CSV uploads)                   │
│  - Air-gapped environment support                           │
│  - Hardware: AI lab GPUs (L40s, A6000, GV100, 2080Ti)       │
│  - Model size scales to available VRAM (see LLM Layer)      │
│  - Preferred: DeepSeek (generate) + Llama (review)          │
└─────────────────────────────────────────────────────────────┘
```

### Component Architecture

> **Architectural note:** Direction phase calls the LLM directly from the backend (no MCP involved). This is a deliberate design decision — Direction is purely conversational and requires no external tool integration. MCP is used from Collection phase onwards, where the AI agent calls real external data sources. This distinction is itself a research finding for RQ1.1.

```
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND                                 │
│              React 18 + TypeScript                          │
│              Vite + TailwindCSS                             │
│                                                             │
│  Components:                                                │
│  - Data Import UI (file upload, source selection)           │
│  - Direction Phase UI (chat dialogue, perspective select)   │
│  - Collection Phase UI (data review, approve/reject)        │
│  - Processing Phase UI (correlations, validation)           │
│  - Output View (toggle: summary / full reasoning)           │
│  - Progress Bar (workflow status)                           │
│  - Language Toggle (NO/EN)                                  │
└─────────────────────┬───────────────────────────────────────┘
                      │ REST API + WebSocket
┌─────────────────────▼───────────────────────────────────────┐
│                 BACKEND API                                 │
│              FastAPI (Python 3.11+)                         │
│                                                             │
│  Responsibilities:                                          │
│  - Session management across all phases                     │
│  - Phase transition orchestration                           │
│  - Human approval checkpoint control                        │
│  - Dual AI instance orchestration (AIOrchestrator)          │
│  - Direct LLM calls for Direction phase (LLMService)        │
│  - GeminiAgent orchestration for Collection+ phases         │
│  - MCP client connection management (Collection+)           │
│  - Data import validation                                   │
│  - Report generation (JSON, PDF)                            │
│  - Research data logging (corrections, actions, times)      │
│                                                             │
│  Services:                                                  │
│  - LLMService        — direct Gemini calls (Direction)      │
│  - GeminiAgent       — Gemini with MCP tools (Collection+)  │
│  - DialogueService   — Direction dialogue (uses LLMService) │
│  - ReviewService     — AI #2 review (uses LLMService)       │
│  - AIOrchestrator    — generate → review → retry loop       │
│  - CollectionService — Collection logic (uses GeminiAgent)  │
│  - ProcessingService — Processing logic (uses GeminiAgent)  │
│                                                             │
│  State Machines (human approval checkpoints only):          │
│  - DirectionFlow   — SUMMARY_CONFIRMING, PIR_CONFIRMING     │
│  - CollectionFlow  — PLAN_CONFIRMING, SOURCE_SELECTING,     │
│                      REVIEWING                              │
│  - ProcessingFlow  — CORRELATION_CONFIRMING,                │
│                      PERSPECTIVE_CONFIRMING                 │
└──────────┬──────────────────────────────┬───────────────────┘
           │ Direct API call              │ MCP Protocol
           │ (Direction only)             │ (Collection+)
┌──────────▼──────────┐       ┌───────────▼───────────────────┐
│     LLM LAYER       │       │         MCP SERVER            │
│  Gemini 2.5 Flash   │       │      Python (FastMCP)         │
│  (via LLMService)   │       │                               │
│                     │       │  Tools:                       │
│  Instance #1:       │       │  - query_otx()                │
│  Generate           │       │  - search_misp()              │
│                     │       │  - search_local_data()        │
│  Instance #2:       │       │  - normalize_data()           │
│  Review             │       │  - map_to_mitre()             │
│                     │       │  - enrich_ioc()               │
└─────────────────────┘       │  - read_knowledge_base()      │
                              │                               │
                              │  Resources (Knowledge Bank):  │
                              │  - geopolitical/ context      │
                              │  - perspectives/ (NSM, CISA,  │
                              │    ENISA, national security)  │
                              │  - threat_actors/ (APT29, ..) │
                              │                               │
                              │  Prompts:                     │
                              │  - collection.md              │
                              │  - processing.md              │
                              └───────────────────────────────┘
```

---

## Workflow Detail

### Direction Phase (Dialogue-Based)

> **MCP usage:** None — deliberate design decision. Direction is purely conversational. All AI calls are made directly from the backend via LLMService (Gemini API). The state machine manages human approval checkpoints only. See Architectural Design Decisions for rationale.

The Direction phase uses a conversational approach to understand user goals and produce approved PIRs:

```
┌─────────────────────────────────────────────────────────────┐
│                    DIRECTION PHASE                          │
│                    (Dialogue-Based)                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ User clicks "Start" + enters initial query          │   │
│  │ Example: "I want to investigate APT29"              │   │
│  └─────────────────────────────────────────────────────┘   │
│                          ↓                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ AI asks clarifying questions:                       │   │
│  │ "What is your scope? Recent activity, TTPs,         │   │
│  │  specific targets, or general overview?"            │   │
│  └─────────────────────────────────────────────────────┘   │
│                          ↓                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ User responds:                                      │   │
│  │ "Focus on recent campaigns against Nordic countries"│   │
│  └─────────────────────────────────────────────────────┘   │
│                          ↓                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ AI asks more questions:                             │   │
│  │ "What time period? Which sources should I           │   │
│  │  prioritize? Any specific IOC types?"               │   │
│  └─────────────────────────────────────────────────────┘   │
│                          ↓                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Dialogue continues until AI has full context...     │   │
│  └─────────────────────────────────────────────────────┘   │
│                          ↓                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ AI Instance #1 generates suggested PIRs             │   │
│  │ AI Instance #2 reviews for errors/hallucinations    │   │
│  │ → If errors: auto-retry, log in reasoning           │   │
│  └─────────────────────────────────────────────────────┘   │
│                          ↓                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ User selects geographic perspectives (optional):    │   │
│  │ [ ] 🇺🇸 US    [ ] 🇳🇴 Norway                         │   │
│  │ [ ] 🇨🇳 China  [ ] 🇪🇺 EU                            │   │
│  │ (None selected = Neutral perspective)               │   │
│  └─────────────────────────────────────────────────────┘   │
│                          ↓                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ User selects data sources:                          │   │
│  │ [ ] File Upload  [ ] AlienVault OTX  [ ] MISP       │   │
│  └─────────────────────────────────────────────────────┘   │
│                          ↓                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ User approves/modifies PIRs                         │   │
│  │ [Approve] [Modify] [Reject with Feedback]           │   │
│  │ (Action logged for RQ2 analysis)                    │   │
│  └─────────────────────────────────────────────────────┘   │
│                          ↓                                  │
│              Proceed to Collection Phase                    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Collection Phase

> **MCP usage:** Full MCP integration. GeminiAgent is the AI driver — it decides which tools to call and when. MCP Tools provide access to external OSINT sources. MCP Resources (knowledge bank) provide geopolitical and threat actor context. The state machine manages human approval checkpoints only.

```
┌─────────────────────────────────────────────────────────────┐
│                    COLLECTION PHASE                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Backend generates collection plan via GeminiAgent       │
│     → GeminiAgent reads knowledge bank for context         │
│     → Produces structured collection plan                  │
│                                                             │
│  [Human checkpoint] User approves/rejects plan              │
│  → Reject: GeminiAgent regenerates with feedback            │
│                                                             │
│  2. System suggests relevant sources based on plan + PIRs   │
│                                                             │
│  [Human checkpoint] User selects approved sources           │
│  → Sources: OTX, MISP, local uploaded files                 │
│                                                             │
│  3. GeminiAgent executes collection:                        │
│     → Reads relevant knowledge bank entries                 │
│     → Calls query_otx() when threat actor data needed       │
│     → Calls search_misp() to cross-reference indicators     │
│     → Calls search_local_data() for uploaded files          │
│     → Synthesises findings, links each to a PIR             │
│     → Assigns confidence level and source per finding       │
│                                                             │
│  4. AI Instance #2 reviews collection output                │
│     → If severity=major: GeminiAgent retries                │
│     → All attempts logged in reasoning file                 │
│                                                             │
│  [Human checkpoint] User reviews collected data             │
│  → Approve: proceed to Processing                           │
│  → Reject with feedback: GeminiAgent revises summary        │
│  → Collect more: return to source selection                 │
│     (Action logged for RQ2 analysis)                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Processing Phase

> **MCP usage:** Full MCP integration, same pattern as Collection. GeminiAgent drives the analysis — it calls normalize_data(), map_to_mitre(), enrich_ioc() and read_knowledge_base() as needed. State machine manages human approval checkpoints only.

```
┌─────────────────────────────────────────────────────────────┐
│                    PROCESSING PHASE                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. GeminiAgent processes collected data:                   │
│     → Calls normalize_data() to standardise IOC formats     │
│     → Calls enrich_ioc() for additional context             │
│     → Calls map_to_mitre() to map TTPs to ATT&CK            │
│     → Reads perspective knowledge bank entries              │
│     → Correlates indicators across sources                  │
│     → Produces structured correlation report                │
│                                                             │
│  2. AI Instance #2 reviews correlation output               │
│     → If severity=major: GeminiAgent retries                │
│     → All attempts logged in reasoning file                 │
│                                                             │
│  [Human checkpoint] User validates correlations             │
│  → Reject with feedback: GeminiAgent revises                │
│                                                             │
│  3. GeminiAgent generates perspective-specific analysis:    │
│     → Reads national security documents from knowledge bank │
│     → Each selected perspective: tactical + strategic layer │
│     → Tactical: IOCs, TTPs, affected systems                │
│     → Strategic: geopolitical framing, policy implications  │
│                                                             │
│  4. AI Instance #2 reviews perspective analysis             │
│     → If severity=major: GeminiAgent retries                │
│                                                             │
│  [Human checkpoint] User approves perspective analysis      │
│  → Reject with feedback: GeminiAgent revises                │
│     (Action logged for RQ2 analysis)                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Analysis Phase

```
┌─────────────────────────────────────────────────────────────┐
│                    ANALYSIS PHASE                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. AI Instance #1 synthesizes Processing output into       │
│     finished analytical intelligence:                       │
│     - Key findings (what happened / is happening)           │
│     - Threat actor attribution (with confidence levels)     │
│     - Impact assessment per selected perspective            │
│     - Strategic implications (per national lens)            │
│     - Recommended courses of action                         │
│                                                             │
│  2. For each selected perspective, AI generates:            │
│     - Tactical layer: IOCs, TTPs, affected systems          │
│     - Strategic layer: Geopolitical framing, national       │
│       security implications, policy-relevant insights       │
│       (derived from national security documents)            │
│                                                             │
│  3. AI Instance #2 reviews analytical judgments             │
│     → Checks: unsupported claims, attribution errors,       │
│       inconsistencies with collected data                   │
│     → If errors: auto-retry, log in reasoning               │
│                                                             │
│  4. User reviews finished intelligence product              │
│  5. User approves final output                              │
│     (Action logged for RQ2 analysis)                        │
│                                                             │
│  [Approve] [Reject with Feedback]                           │
│                          ↓                                  │
│                   Generate Output                           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Output

```
┌─────────────────────────────────────────────────────────────┐
│                    OUTPUT                                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Files generated:                                           │
│  ├── report_[timestamp].json    (machine-readable)          │
│  ├── report_[timestamp].pdf     (human-readable)            │
│  ├── reasoning_[timestamp].json (AI reasoning + review)     │
│  └── research_log_[timestamp].json (for RQ analysis)        │
│                                                             │
│  Report contains:                                           │
│  - Executive summary                                        │
│  - Direction (PIRs, scope, selected perspectives)           │
│  - Collection (sources used, data collected)                │
│  - Processing (correlations, enrichments, MITRE mappings)   │
│  - Analysis: key findings, attribution, confidence levels   │
│  - Per-perspective outputs (tactical + strategic layers)    │
│  - Recommended courses of action                            │
│  - All sources cited with timestamps                        │
│                                                             │
│  Reasoning file contains:                                   │
│  - AI decision-making process (summarized + full)           │
│  - AI Review notes from Instance #2                         │
│  - Retry attempts and corrections                           │
│                                                             │
│  Research log contains:                                     │
│  - All AI #2 corrections (for RQ1.3)                        │
│  - User actions: approve/reject/modify (for RQ2)            │
│  - Task completion times (for RQ2.3)                        │
│                                                             │
│  User can:                                                  │
│  - Toggle between output view and reasoning view            │
│  - Download JSON                                            │
│  - Download PDF                                             │
│  - Access previous reports (max 3 stored)                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Geographic Perspectives

| Perspective | Code | Description |
|-------------|------|-------------|
| 🇺🇸 United States | US | American/FBI/CISA perspective on threats |
| 🇳🇴 Norway | NO | Norwegian/NSM/PST perspective on threats |
| 🇨🇳 China | CN | Chinese perspective on threats |
| 🇪🇺 European Union | EU | European/Europol/ENISA perspective on threats |
| 🌐 Neutral | NEUTRAL | Objective, non-aligned perspective (default) |

**Rules:**
- Selection happens in Direction phase
- User can select 0, 1, or multiple perspectives
- If none selected → Neutral (default)
- Each perspective produces **two layers** of output:
  - **Tactical layer**: IOC context, TTP framing, affected systems — delivered in Processing
  - **Strategic layer**: National security implications, geopolitical framing, policy-relevant insights — delivered in Analysis
- Each perspective generates a separate section in the final report
- Can be extended with additional perspectives post-MVP

**Strategic Perspective Source Documents (per nation):**
| Perspective | Key Source Documents |
|-------------|----------------------|
| 🇳🇴 Norway | NSM Risikobilde, PST Nasjonal trusselvurdering (NTA), NIS Focus |
| 🇺🇸 United States | CISA advisories, ODNI Annual Threat Assessment, NSA Cybersecurity Reports |
| 🇪🇺 EU | ENISA Threat Landscape, Europol IOCTA, NIS2 Directive |
| 🇨🇳 China | MIIT/MPS security frameworks, CNCERT annual reports |
| 🌐 Neutral | No framing document — raw technical intelligence only |

---

## Technology Stack

### Backend (Python 3.11+)

#### Language
| Technology | Justification |
|------------|---------------|
| Python 3.11+ | Required for FastMCP; OSINT libraries (PyMISP, OTXv2) are Python-native. |

#### Framework
| Technology | Purpose | Justification |
|------------|---------|---------------|
| FastAPI | REST API framework | Native async support; auto-generates API documentation. |

#### Libraries
| Library | Purpose | Justification |
|---------|---------|---------------|
| FastMCP | MCP server framework | Decorator-based API; reduces boilerplate. |
| Pydantic | Data validation | Validates OSINT data; integrated with FastAPI. |
| httpx | Async HTTP client | Parallel OSINT queries without blocking. |
| PyMISP | MISP API client | Official MISP library. |
| OTXv2 | AlienVault OTX client | Official OTX library. |
| ReportLab | PDF generation | Creates PDF reports. |

#### Testing Libraries
| Library | Purpose | Justification |
|---------|---------|---------------|
| pytest | Test framework | Python standard; CI integration. |
| pytest-asyncio | Async test support | Required for async code testing. |
| pytest-cov | Coverage reporting | Enforces coverage thresholds. |
| respx | HTTP mocking | Mocks API calls in tests. |

#### Dev Tools
| Tool | Purpose | Justification |
|------|---------|---------------|
| Ruff | Linter | Fast; replaces multiple tools. |
| mypy | Type checker | Catches type errors. |
| Poetry | Dependency manager | Modern dependency management. |

### Frontend (TypeScript)

#### Language
| Technology | Justification |
|------------|---------------|
| TypeScript | Type safety; prevents integration errors. |

#### Framework
| Technology | Purpose | Justification |
|------------|---------|---------------|
| React 18 | UI framework | Reusable components; large ecosystem. |

#### Libraries
| Library | Purpose | Justification |
|---------|---------|---------------|
| TailwindCSS | Styling | Rapid UI development. |
| React Router | Client-side routing | Navigation between phases. |
| Axios | HTTP client | Clean API; interceptors for errors. |

#### Testing Libraries
| Library | Purpose | Justification |
|---------|---------|---------------|
| Vitest | Unit tests | Native Vite integration. |
| React Testing Library | Component tests | Tests user behavior. |
| MSW | API mocking | Mocks backend at network level. |
| Playwright | E2E tests | Browser automation. |

#### Dev Tools
| Tool | Purpose | Justification |
|------|---------|---------------|
| Vite | Build tool | Fast hot module replacement. |
| ESLint | Linter | Consistent code style. |

### Design Tools
| Tool | Purpose | Phase |
|------|---------|-------|
| Figma | Wireframes, prototypes | Low-fi, Med-fi |
| draw.io | Flow diagrams | Low-fi |

### LLM Layer

#### Online Mode
| Model | Role | Justification |
|-------|------|---------------|
| Gemini 2.5 Flash | Primary: Generate + Review | Available via Google AI Studio API key; large context window. Best fit for MVP. |

#### Online Backup / Free Tier APIs
| Provider | Models Available | Notes |
|----------|------------------|-------|
| Google AI Studio | Gemini 2.5 Flash, Gemini 2.0 Flash | **Primary.** Use API key from Google AI Studio. |
| Groq | Llama 3.3 70B, DeepSeek, Mistral | Ultra-fast inference; generous free tier. |
| GitHub Models | GPT-4o, GPT-4o mini, Llama, Mistral | Available via GitHub account. |
| Together AI | Llama 4 Scout, DeepSeek-R1 | $25 free credits on signup. |
| OpenRouter | 50+ models (DeepSeek, Qwen, etc.) | $5 credits; free models available. |
| Mistral AI | Mistral Small, Ministral 3B | Free tier; EU data compliance. |
| Hugging Face | 300+ open-source models | Rate-limited; good for experimentation. |

#### Offline / Local Mode (AI Lab)
The project has access to an AI lab with dynamically allocated GPU resources. Model choice scales with available VRAM:

| Tier | Available GPU | Primary AI (Generate) | Review AI (Validate) |
|------|---------------|-----------------------|----------------------|
| Tier 1 (Ideal) | L40s / A6000 (48GB each) | DeepSeek-R1 32B or DeepSeek-V3 quantized | Llama 3.3 70B (quantized) |
| Tier 2 (Realistic) | GV100 (32GB) | DeepSeek-R1 14B | Llama 3.2 11B |
| Tier 3 (Minimum) | 2080Ti / 1080Ti (11GB) | DeepSeek-R1 7B (quantized) | Llama 3.2 3B |
| Fallback | Any (8GB+) | Phi-3 Mini (3.8B) | Same model, sequential |

**AI Lab Hardware Available (dynamically allocated):**
- Nvidia L40s — 48GB VRAM (best option)
- RTX A6000 — 48GB VRAM
- GV100 — 32GB VRAM
- 2080Ti / 1080Ti — 11GB VRAM each

**Key Constraints:**
- Compute is dynamically allocated; model size must flex based on what is available at runtime
- Two instances run sequentially (not parallel) when VRAM is shared
- Offline model runner: Ollama (for simplicity) or vLLM (for performance)
- DeepSeek models preferred for primary generation (strong analytical reasoning, structured output)
- Llama models preferred for review/validation (different architecture reduces correlated errors)

---

## Perspective Architecture

### Core Design Principle

Geographic perspectives use **official government and national security documents as interpretation lenses**, not as neutral knowledge sources. The same technical threat data is interpreted through different geopolitical frames.

### Two-Layer Architecture

```
Layer 1: Shared Neutral Technical Foundation
─────────────────────────────────────────────
  - MITRE ATT&CK framework (TTPs, techniques)
  - CVE / NVD vulnerability database
  - Threat actor profiles (neutral, factual)
  - Raw OSINT data (OTX, MISP)

             ↓  fed into  ↓

Layer 2A: Tactical Perspective (Processing Phase)
─────────────────────────────────────────────────
  IOC context, TTP framing, affected systems
  viewed through national security priorities

             ↓  synthesized into  ↓

Layer 2B: Strategic Perspective (Analysis Phase)
─────────────────────────────────────────────────
  Derived from national security documents:
  - Norway: NSM Risiko, PST NTA, NIS Focus
  - US: CISA advisories, NSA/ODNI publications
  - EU: ENISA Threat Landscape reports
  - China: MIIT/MPS security frameworks
  - Neutral: No framing; raw technical summary only

  Outputs: geopolitical framing, strategic implications,
  attribution stance, recommended policy actions
```

### How Documents Are Used

Official documents **define the lens**, not the facts. They provide:
- Strategic priority rankings (which sectors/actors matter most)
- Attribution bias and style (how to frame threat actor identification)
- Terminology preferences (country-specific language patterns)
- Recommended mitigations and frameworks (NIST vs GDPR vs GB/T standards)

### Implementation

Perspectives are stored as **MCP Prompt templates** (not RAG/vector DB):
```
mcp_server/src/prompts/
  ├── neutral.md
  ├── perspective_norway.md    ← Uses NSM/PST priorities as framing
  ├── perspective_us.md        ← Uses CISA/NIST as framing
  ├── perspective_eu.md        ← Uses ENISA/NIS2 as framing
  └── perspective_china.md     ← Uses MIIT/MPS as framing
```

Each template (~200-400 words) contains:
1. Geopolitical context and strategic priorities (from source documents)
2. Critical sectors ranked by national priority
3. Threat actor ranking (Critical/High/Medium/Low for this nation)
4. Attribution style guidelines
5. Preferred mitigation frameworks and terminology

### Future Extension: Council Mode

F20 (Deferred) — Multiple AI agents each adopt a perspective and debate findings. Reveals strategic trade-offs and disagreements across national viewpoints. Not part of MVP scope; preserved for future work.

---

## Architectural Design Decisions

### MCP Usage Per Phase — Rationale

A core finding of this project is that MCP adds value proportional to the need for external tool integration. Not all phases of the TI cycle benefit equally from MCP.

| Phase | MCP Used | Rationale |
|-------|----------|-----------|
| Direction | No | Pure conversational dialogue. No external data sources required. Gemini's training knowledge is sufficient. Using MCP here would add protocol overhead with no value. |
| Collection | Yes | Requires external OSINT APIs (OTX, MISP) and local file search. Gemini cannot access these without tools. This is MCP's core use case. |
| Processing | Yes | Requires MITRE ATT&CK lookups, data normalisation, IOC enrichment, and national security knowledge bank. All require external integration. |

This distinction directly answers **RQ1.1** — MCP primitives are most effective when they provide access to external systems the AI cannot reach independently.

### AI Agent Architecture

From Collection phase onwards, Gemini acts as a true AI agent:
- Gemini decides which tools to call and when
- Gemini decides how many OTX queries to make
- Gemini decides which knowledge bank entries are relevant
- Backend only manages human approval checkpoints

Direction phase uses a backend-orchestrated approach:
- Backend state machine controls the conversation flow
- Backend calls LLMService directly for each AI generation step
- State machine manages human approval checkpoints

This hybrid is a deliberate choice, not a compromise. Direction's value lies in structured dialogue management and human oversight — not in autonomous AI decision-making.

### State Machines — Human Checkpoints Only

State machines in this project manage **human decisions**, not AI decisions. Each state corresponds to a point where the analyst must approve, reject, or modify AI output before proceeding.

| State | Human decision |
|-------|---------------|
| `SUMMARY_CONFIRMING` | Is the gathered context correctly understood? |
| `PIR_CONFIRMING` | Are the generated PIRs acceptable? |
| `PLAN_CONFIRMING` | Is the collection plan appropriate? |
| `SOURCE_SELECTING` | Which data sources should be queried? |
| `REVIEWING` | Is the collected data sufficient and accurate? |
| `CORRELATION_CONFIRMING` | Are the correlations and MITRE mappings correct? |
| `PERSPECTIVE_CONFIRMING` | Is the perspective analysis accurate? |

AI orchestration (deciding when to call which tool) belongs to GeminiAgent, not the state machine.

### Dual AI Review

AI Instance #1 (generate) and AI Instance #2 (review) are both Gemini 2.5 Flash in online mode. The backend orchestrates two separate API calls — they are not the same request. The review prompt (`DIRECTION_REVIEW_PROMPT`, `COLLECTION_REVIEW_PROMPT`, `PROCESSING_REVIEW_PROMPT`) instructs AI #2 to evaluate quality and return a structured severity verdict (`none` / `minor` / `major`). On `major`, the AIOrchestrator retries generation (max 3 attempts). All attempts are logged for RQ1.3 analysis.

---

## MCP Implementation

> **Note on MCP usage per phase:** Direction phase does not use MCP — all AI calls are made directly from the backend via LLMService. This is a deliberate architectural decision: Direction is purely conversational and requires no external tool integration. Collection and Processing phases use MCP correctly, with GeminiAgent calling real external integrations. See Architectural Design Decisions for full rationale.

### Tools (Called by GeminiAgent — Collection and Processing only)

| Tool | Purpose | Phase |
|------|---------|-------|
| `query_otx(threat_actor, ioc_type)` | Query AlienVault OTX API for threat data | Collection |
| `search_misp(query, limit)` | Search MISP instance for events and indicators | Collection |
| `search_local_data(query)` | Search uploaded local TI files | Collection |
| `normalize_data(raw_data)` | Standardize and deduplicate IOC formats | Processing |
| `enrich_ioc(ioc, ioc_type)` | Enrich IOC with external context | Processing |
| `map_to_mitre(technique_description)` | Map findings to MITRE ATT&CK framework | Processing |
| `read_knowledge_base(resource_id)` | Read from knowledge bank (geopolitical, perspectives, threat actors) | Collection + Processing |

> **Removed from Tools:** `dialogue_question`, `generate_pirs`, `generate_summary`, `review_output`, `generate_perspective_summary`, `generate_strategic_assessment`, `generate_key_findings`, `generate_recommendations`. These are AI reasoning tasks — Gemini performs them directly without tool wrappers. AI generation is handled by LLMService (Direction) or GeminiAgent's own reasoning (Collection+).

### Resources (Knowledge Bank — exposed via read_knowledge_base tool)

| Resource ID | Content | Used In |
|-------------|---------|---------|
| `geopolitical/norway-russia` | Norway-Russia relations, tensions, historical context | Collection + Processing |
| `geopolitical/norway-usa` | NATO cooperation, dependencies, interest differences | Collection + Processing |
| `geopolitical/norway-china` | Chinese presence in Norway, investment risk | Collection + Processing |
| `geopolitical/russia-nato` | Russian threat posture toward NATO | Collection + Processing |
| `geopolitical/china-eu` | China-EU strategic relationship | Collection + Processing |
| `perspective/norway` | NSM/PST priorities, Norwegian national security law | Processing |
| `perspective/us` | CISA, NIST, Five Eyes perspective | Processing |
| `perspective/eu` | ENISA, NIS2, GDPR implications | Processing |
| `perspective/china` | Chinese state perspective, domestic APT groups | Processing |
| `threat-actor/apt29` | Cozy Bear — TTPs, history, known Nordic targets | Collection + Processing |
| `threat-actor/apt28` | Fancy Bear — TTPs, history | Collection + Processing |
| `threat-actor/lazarus-group` | North Korea — TTPs, financial targeting | Collection + Processing |
| `threat-actor/killnet` | Russian hacktivist group | Collection + Processing |

### Prompts (Workflow templates — used in backend, not MCP Prompts primitive)

> **Implementation note:** Prompt templates for Direction phase remain in `mcp_server/src/prompts/__init__.py` and are imported directly by backend services. System prompts for Collection and Processing agents are stored as markdown files in `backend/src/prompts/`.

| Prompt | Purpose | Phase | Location |
|--------|---------|-------|----------|
| `build_direction_dialogue_prompt()` | Guide conversation to gather intelligence requirements | Direction | `mcp_server/src/prompts/__init__.py` |
| `build_pir_generation_prompt()` | Generate PIRs from gathered context | Direction | `mcp_server/src/prompts/__init__.py` |
| `build_summary_prompt()` | Summarise gathered context for analyst review | Direction | `mcp_server/src/prompts/__init__.py` |
| `DIRECTION_REVIEW_PROMPT()` | AI #2 quality review of PIRs | Direction | `mcp_server/src/prompts/__init__.py` |
| `COLLECTION_REVIEW_PROMPT()` | AI #2 review of collected data | Collection | `mcp_server/src/prompts/__init__.py` |
| `PROCESSING_REVIEW_PROMPT()` | AI #2 review of processed analysis | Processing | `mcp_server/src/prompts/__init__.py` |
| `collection.md` | System prompt for GeminiAgent in Collection phase | Collection | `backend/src/prompts/collection.md` |
| `processing.md` | System prompt for GeminiAgent in Processing phase | Processing | `backend/src/prompts/processing.md` |

---

## OSINT Data Sources

### Online Mode
| Source | Type | Integration |
|--------|------|-------------|
| AlienVault OTX | Threat Intelligence | OTXv2 library |
| MISP | Threat Sharing | PyMISP library |

### Offline Mode (Pre-loaded Data)
| Format | Description |
|--------|-------------|
| OTX Export (JSON) | Downloaded pulse data |
| MISP Export (JSON) | Exported events |
| Custom IOCs (CSV) | User-provided indicators |
| Attachments (PDF, TXT) | Supporting documents |

---

## Test Coverage Requirements

| Test Type | Target | Minimum | Description |
|-----------|--------|---------|-------------|
| Unit Tests | 80% | 70% | Individual functions, classes, components |
| Integration Tests | 80% | 70% | Module interactions, API endpoints |
| E2E Tests | 100% | 100% | Full user journeys (critical paths) |

### Critical E2E Paths

#### Path 1: Direction Phase (Dialogue)
| Step | Action | Expected Result |
|------|--------|-----------------|
| 1.1 | User clicks start + enters query | Dialogue UI opens |
| 1.2 | AI asks clarifying questions | Questions displayed |
| 1.3 | User responds to questions | AI receives context |
| 1.4 | Dialogue continues until complete | Full context gathered |
| 1.5 | AI generates PIRs | PIRs displayed |
| 1.6 | AI Review validates PIRs | Errors auto-corrected |
| 1.7 | User selects perspectives | Selection saved |
| 1.8 | User selects data sources | Sources saved |
| 1.9 | User approves PIRs | Proceed to Collection |

#### Path 2: Collection Phase
| Step | Action | Expected Result |
|------|--------|-----------------|
| 2.1 | System shows PIRs | PIRs displayed |
| 2.2 | System queries sources | Data collected |
| 2.3 | AI aggregates data | Aggregated view shown |
| 2.4 | AI Review validates | Errors auto-corrected |
| 2.5 | User reviews data | Data with sources shown |
| 2.6 | User approves | Proceed to Processing |

#### Path 3: Processing Phase
| Step | Action | Expected Result |
|------|--------|-----------------|
| 3.1 | AI normalizes data | Normalized view shown |
| 3.2 | AI correlates | Correlations displayed |
| 3.3 | AI enriches IOCs | Enrichment shown |
| 3.4 | AI maps to MITRE | Mappings displayed |
| 3.5 | AI Review validates all | Errors auto-corrected |
| 3.6 | AI generates perspective summaries | Summaries shown |
| 3.7 | AI Review validates summaries | Errors auto-corrected |
| 3.8 | User validates output | Final approval |

#### Path 4: Output Generation
| Step | Action | Expected Result |
|------|--------|-----------------|
| 4.1 | System generates JSON | Valid JSON created |
| 4.2 | System generates PDF | Formatted PDF created |
| 4.3 | System saves reasoning | Reasoning file created |
| 4.4 | User toggles views | View switches correctly |
| 4.5 | User downloads files | Files download correctly |

#### Path 5: Human-in-the-Loop
| Step | Action | Expected Result |
|------|--------|-----------------|
| 5.1 | User rejects suggestion | Workflow continues |
| 5.2 | User provides feedback | Feedback recorded |
| 5.3 | User modifies suggestion | Modified version saved |
| 5.4 | User cannot skip approval | Transition blocked |

#### Path 6: Error Handling
| Step | Action | Expected Result |
|------|--------|-----------------|
| 6.1 | API fails | Error message shown |
| 6.2 | Invalid file uploaded | Validation error shown |
| 6.3 | AI Review finds error | Auto-retry logged |

#### Path 7: Report Management
| Step | Action | Expected Result |
|------|--------|-----------------|
| 7.1 | User accesses old reports | List displayed |
| 7.2 | User downloads old report | Correct file downloads |
| 7.3 | 4th report created | Oldest deleted |

---

## Risk Analysis

| Risk | Severity | Likelihood | Mitigation |
|------|----------|------------|------------|
| AI goes rogue (unauthorized actions) | Critical | Low | Human approval at every step; no autonomous actions |
| AI hallucination | Medium | Medium | Dual AI review system; auto-retry on errors |
| External data poisoning | Critical | Low | Validate data sources; human review |
| Bad analysis quality | Medium | Medium | Human validation; reasoning transparency |
| Results not testable | Medium | Low | Structured output; reproducible workflows |
| Program stops mid-analysis | High | Medium | Session recovery; auto-save; error handling |
| Not fully using tools | Medium | Medium | Documentation; well-designed prompts |
| Bad prompt usage | Low | Medium | Documentation; prompt templates |
| AI cannot justify answers | Medium | Low | Mandatory reasoning output; source citation |
| Offline model quality | Medium | Medium | Test with multiple models; set expectations |
| User testing recruitment | Medium | Medium | Early coordination with industry partners |

---

## Sprint Schedule

| Sprint | Dates | Focus | UI Phase |
|--------|-------|-------|----------|
| 1 | Feb 1-14 | Foundation: Environment, basic MCP, test infrastructure, data import | Low-fi sketches |
| 2 | Feb 15-28 | Direction Phase: Dialogue system, PIR generation, perspective selection | Low-fi → Med-fi wireframes |
| 3 | Mar 1-14 | Collection Phase: Multi-source queries, AI review integration | Med-fi clickable prototype |
| 4 | Mar 15-28 | Processing Phase: Normalization, correlation, tactical perspective summaries | High-fi implementation |
| 5 | Mar 29 - Apr 11 | Analysis Phase + Integration: Strategic assessments, end-to-end workflow, output generation | High-fi + User testing |
| 6 | Apr 12-30 | Polish: Bug fixes, PDF reports, language support, documentation | Iteration + Final testing |

### Key Milestones

| Date | Milestone | Success Criteria |
|------|-----------|------------------|
| Feb 14 | M1: Infrastructure | Dev environment, CI, data import working |
| Feb 28 | M2: Direction | Dialogue-based PIR workflow with AI review |
| Mar 14 | M3: Collection | Multi-source collection with AI review |
| Mar 28 | M4: Processing | Full processing pipeline with tactical perspective summaries |
| Apr 11 | M5: Analysis + Integration | Strategic assessments, complete 4-phase workflow, JSON output, user testing done |
| May 1 | M6: Final | PDF reports, documentation, demo ready, research data analyzed |

### User Testing Schedule

| When | What | Participants |
|------|------|--------------|
| Week 3 (Feb 15-21) | Low-fi wireframe review | Team + Supervisor |
| Week 5 (Mar 1-7) | Med-fi prototype walkthrough | Supervisor + 1-2 partners |
| Week 9 (Mar 29 - Apr 4) | High-fi user testing sessions | 3-5 industry partners |
| Week 11 (Apr 12-18) | Final validation | Partners + Supervisor |

---

## Definition of Done

### Code Quality
- [ ] TDD followed (tests before implementation)
- [ ] Passes linting (ESLint, Ruff)
- [ ] Passes type checks (TypeScript, mypy)
- [ ] Code reviewed by ≥1 team member
- [ ] Merged to main branch

### Testing
- [ ] Unit tests: ≥80% coverage
- [ ] Integration tests: ≥80% coverage
- [ ] E2E tests updated if affecting critical paths
- [ ] All existing tests pass

### Functionality
- [ ] Works in integrated environment
- [ ] Human-in-the-loop controls verified
- [ ] AI review functioning (auto-retry working)
- [ ] Works online and offline (if applicable)
- [ ] Error handling with clear messages

### Accessibility
- [ ] Keyboard navigable
- [ ] Screen reader labels
- [ ] Color contrast meets WCAG AA

### Research Data
- [ ] AI corrections logged
- [ ] User actions logged
- [ ] Timing data collected

---

## File Structure

```
project-root/
├── PLAN.md                     # This file
├── README.md                   # Setup and usage
├── pyproject.toml              # Python dependencies
├── package.json                # Frontend dependencies
├── .gitignore                  # Git ignore rules
├── check.sh                    # Manual lint check script
│
├── .vscode/
│   ├── settings.json           # VS Code workspace settings
│   └── extensions.json         # Recommended extensions
│
├── design/
│   ├── wireframes/             # Low-fi and med-fi designs
│   ├── prototypes/             # Figma links/exports
│   └── user-testing/           # Test protocols, results
│
├── data/
│   ├── imports/                # User uploads
│   └── outputs/                # Generated reports (max 3)
│       ├── report_001.json
│       ├── report_001.pdf
│       ├── reasoning_001.json
│       └── research_log_001.json
│
├── backend/
│   ├── src/
│   │   ├── api/                     # FastAPI routes
│   │   │   ├── dialogue.py          # Main phase endpoint + session mgmt
│   │   │   └── main.py
│   │   ├── mcp_client/              # MCP client (used by Collection+)
│   │   │   └── client.py
│   │   ├── services/                # Business logic
│   │   │   ├── llm_service.py       # Direct Gemini calls (Direction)
│   │   │   ├── gemini_agent.py      # Gemini + MCP tool-loop (Collection+)
│   │   │   ├── ai_orchestrator.py   # Dual AI generate→review→retry
│   │   │   ├── dialogue_service.py  # Direction dialogue (uses LLMService)
│   │   │   ├── review_service.py    # AI #2 review (uses LLMService)
│   │   │   ├── collection_service.py # Collection logic (uses GeminiAgent)
│   │   │   ├── processing_service.py # Processing logic (uses GeminiAgent)
│   │   │   ├── reasearch_logger.py  # RQ data collection
│   │   │   └── state_machines/
│   │   │       ├── base_phase_flow.py
│   │   │       ├── direction_flow.py   # Human checkpoints only
│   │   │       ├── collection_flow.py  # Human checkpoints only
│   │   │       └── processing_flow.py  # Human checkpoints only
│   │   ├── prompts/                 # Agent system prompts
│   │   │   ├── collection.md        # GeminiAgent system prompt
│   │   │   └── processing.md        # GeminiAgent system prompt
│   │   ├── importers/               # Data import handlers
│   │   └── models/                  # Pydantic models
│   └── tests/
│
├── mcp_server/
│   ├── src/
│   │   ├── tools/                   # MCP tools (external integrations only)
│   │   │   ├── osint.py             # query_otx, search_misp, search_local_data
│   │   │   └── processing.py        # normalize_data, map_to_mitre, enrich_ioc
│   │   ├── resources/               # Knowledge bank
│   │   │   ├── geopolitical/        # Country relationship markdown files
│   │   │   ├── perspectives/        # National security framework files
│   │   │   └── threat_actors/       # Threat actor context files
│   │   ├── prompts/                 # Direction phase prompt builders
│   │   │   └── __init__.py          # build_direction_dialogue_prompt, etc.
│   │   └── server.py                # FastMCP server + tool/resource registration
│   └── tests/
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── DialogueChat/   # Direction dialogue UI
│   │   │   ├── PerspectiveSelect/
│   │   │   ├── ProgressBar/
│   │   │   └── ReasoningToggle/
│   │   ├── pages/
│   │   ├── hooks/
│   │   ├── services/
│   │   ├── i18n/               # Translations (NO/EN)
│   │   └── types/
│   └── tests/
│
├── research/
│   ├── data/                   # Collected research data
│   ├── analysis/               # Analysis scripts/notebooks
│   └── reports/                # Research findings
│
└── tests/
    ├── e2e/                    # Playwright tests
    └── fixtures/               # Test data
```

---

## Documentation Links

### Backend
| Technology | URL |
|------------|-----|
| Python 3.11 | https://docs.python.org/3.11/ |
| FastAPI | https://fastapi.tiangolo.com/ |
| FastMCP | https://github.com/jlowin/fastmcp |
| Pydantic | https://docs.pydantic.dev/ |
| httpx | https://www.python-httpx.org/ |
| PyMISP | https://pymisp.readthedocs.io/ |
| OTXv2 | https://github.com/AlienVault-OTX/OTX-Python-SDK |
| pytest | https://docs.pytest.org/ |
| Ruff | https://docs.astral.sh/ruff/ |
| mypy | https://mypy.readthedocs.io/ |
| Poetry | https://python-poetry.org/docs/ |

### Frontend
| Technology | URL |
|------------|-----|
| TypeScript | https://www.typescriptlang.org/docs/ |
| React 18 | https://react.dev/ |
| TailwindCSS | https://tailwindcss.com/docs |
| React Router | https://reactrouter.com/ |
| Axios | https://axios-http.com/docs/intro |
| Vitest | https://vitest.dev/ |
| React Testing Library | https://testing-library.com/docs/react-testing-library/intro/ |
| MSW | https://mswjs.io/docs/ |
| Vite | https://vitejs.dev/guide/ |
| ESLint | https://eslint.org/docs/latest/ |
| Playwright | https://playwright.dev/docs/intro |

### LLM & Protocols
| Technology | URL |
|------------|-----|
| MCP | https://modelcontextprotocol.io/ |
| Gemini API | https://ai.google.dev/docs |
| Ollama | https://ollama.ai/ |

### OSINT
| Source | URL |
|--------|-----|
| AlienVault OTX | https://otx.alienvault.com/api |
| MISP | https://www.misp-project.org/documentation/ |

### Accessibility
| Standard | URL |
|----------|-----|
| WCAG 2.1 | https://www.w3.org/WAI/WCAG21/quickref/ |

### User Testing
| Resource | URL |
|----------|-----|
| System Usability Scale (SUS) | https://www.usability.gov/how-to-and-tools/methods/system-usability-scale.html |

---

## Acceptance Criteria

The MVP is complete when:
1. All functional requirements (F01-F21) marked "Must Have" are implemented
2. All non-functional requirements (NF01-NF23) marked "Must Have" are met
3. All critical E2E paths pass (Paths 1-7)
4. Test coverage: ≥80% unit, ≥80% integration, 100% critical paths
5. User testing completed with SUS score ≥ 68
6. Research data collected for RQ1 and RQ2 analysis
7. Documentation complete (README, API docs, user guide)
8. Demo successfully presented to supervisors

---

## AI Assistant Guidelines

When working on this project:

1. **Follow TDD**: Write tests before implementation
2. **Respect human-in-the-loop**: Never implement autonomous AI actions
3. **Implement dual AI review**: All AI outputs go through review instance
4. **Use type hints**: Python and TypeScript types are mandatory
5. **Mock external services**: Never call real APIs in tests
6. **Keep MVP scope**: Confirm with team before adding features not in this plan
7. **Support both modes**: Features should work online and offline
8. **Maintain accessibility**: Follow WCAG 2.1 AA guidelines
9. **Log research data**: All AI corrections and user actions must be logged

### Prohibited
- Skipping AI review step
- Implementing authentication
- Using paid APIs without approval
- Removing human approval steps
- Breaking accessibility requirements
- Disabling research logging

### Encouraged
- Improving AI review prompts
- Adding error recovery mechanisms
- Enhancing reasoning transparency
- Improving dialogue quality
- Better perspective prompts
- Improving research data collection

---

*Last Updated: February 2026*
*Version: 6.0 (Added: Analysis phase throughout, strategic perspective layer, Gemini 2.5 Flash, fixed encoding/emojis, updated MCP tools/prompts, sprint/milestone alignment)*
