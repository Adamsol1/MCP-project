import { useEffect, useMemo, useState, type FormEvent } from "react";
import { useChat } from "../../hooks/useChat/useChat";
import { useSettings } from "../../contexts/SettingsContext/SettingsContext";
import type {
  CouncilNote,
  CouncilTranscriptEntry,
  ProcessingFinding,
} from "../../types/analysis";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const PERSPECTIVE_ORDER = ["us", "norway", "china", "eu", "russia", "neutral"];
const COUNCIL_SUMMARY_VIEW = "council-summary";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type CouncilSectionItem = {
  type: "paragraph" | "bullet";
  text: string;
};

type CouncilSection = {
  title: string | null;
  items: CouncilSectionItem[];
};

type CouncilVote = {
  option: string;
  confidence: number | null;
  rationale: string;
};

type CouncilParticipantView = {
  participant: string;
  entries: CouncilTranscriptEntry[];
  latestEntry: CouncilTranscriptEntry | null;
  sections: CouncilSection[];
  vote: CouncilVote | null;
};

// ---------------------------------------------------------------------------
// Helpers — text parsing
// ---------------------------------------------------------------------------

function formatPerspectiveLabel(key: string) {
  return key === "us" || key === "eu"
    ? key.toUpperCase()
    : key.charAt(0).toUpperCase() + key.slice(1);
}

function stripMarkdown(value: string) {
  return value.replace(/\*\*(.*?)\*\*/g, "$1").trim();
}

function normalizeSectionTitle(value: string) {
  return stripMarkdown(value).replace(/:\s*$/, "").trim();
}

function splitVoteFromResponse(response: string) {
  const voteIndex = response.lastIndexOf("VOTE:");
  if (voteIndex === -1) {
    return { body: response.trim(), vote: null };
  }

  const body = response.slice(0, voteIndex).trim();
  const voteCandidate = response.slice(voteIndex + "VOTE:".length).trim();

  try {
    const parsed = JSON.parse(voteCandidate) as {
      option?: string;
      confidence?: number;
      rationale?: string;
    };
    return {
      body,
      vote: {
        option: parsed.option?.trim() || "No position provided",
        confidence: typeof parsed.confidence === "number" ? parsed.confidence : null,
        rationale: parsed.rationale?.trim() || "No rationale provided.",
      } satisfies CouncilVote,
    };
  } catch {
    return { body: response.trim(), vote: null };
  }
}

function buildCouncilSections(body: string) {
  const sections: CouncilSection[] = [];
  let currentSection: CouncilSection = { title: null, items: [] };
  let paragraphBuffer: string[] = [];

  function flushParagraph() {
    if (paragraphBuffer.length === 0) return;
    currentSection.items.push({
      type: "paragraph",
      text: stripMarkdown(paragraphBuffer.join(" ")),
    });
    paragraphBuffer = [];
  }

  function flushSection() {
    flushParagraph();
    if (currentSection.title || currentSection.items.length > 0) {
      sections.push(currentSection);
    }
    currentSection = { title: null, items: [] };
  }

  for (const rawLine of body.split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line) {
      flushParagraph();
      continue;
    }

    const numberedHeadingMatch = line.match(/^\d+\.\s+\*\*(.+?)\*\*\s*$/);
    if (numberedHeadingMatch) {
      flushSection();
      currentSection = { title: normalizeSectionTitle(numberedHeadingMatch[1]), items: [] };
      continue;
    }

    const headingMatch = line.match(/^\*\*(.+?)\*\*\s*$/);
    if (headingMatch) {
      flushSection();
      currentSection = { title: normalizeSectionTitle(headingMatch[1]), items: [] };
      continue;
    }

    const bulletMatch = line.match(/^[-*]\s+(.*)$/);
    if (bulletMatch) {
      flushParagraph();
      currentSection.items.push({ type: "bullet", text: bulletMatch[1].trim() });
      continue;
    }

    paragraphBuffer.push(line);
  }

  flushSection();

  if (sections.length === 0 && body.trim()) {
    return [{ title: null, items: [{ type: "paragraph" as const, text: stripMarkdown(body) }] }];
  }

  return sections;
}

function buildCouncilParticipantViews(councilNote: CouncilNote) {
  return councilNote.participants.map((participant) => {
    const entries = councilNote.full_debate.filter(
      (entry) => entry.participant === participant,
    );
    const latestEntry = entries.at(-1) ?? null;
    const { body, vote } = splitVoteFromResponse(latestEntry?.response ?? "");
    return {
      participant,
      entries,
      latestEntry,
      sections: buildCouncilSections(body),
      vote,
    } satisfies CouncilParticipantView;
  });
}

function splitLabeledText(text: string) {
  const cleaned = text.trim();
  const match = cleaned.match(/^\*\*(.+?)\*\*:?\s*(.*)$/);
  if (!match) return null;
  return {
    label: normalizeSectionTitle(match[1]),
    body: stripMarkdown(match[2]),
  };
}

function renderCouncilSectionItem(item: CouncilSectionItem, index: number) {
  if (item.type === "paragraph") {
    return (
      <p key={index} className="text-sm leading-7 text-text-primary">
        {item.text}
      </p>
    );
  }

  const labeled = splitLabeledText(item.text);
  if (labeled) {
    return (
      <div key={index} className="flex gap-3 text-sm leading-7 text-text-primary">
        <span className="mt-[0.7em] h-1.5 w-1.5 rounded-full bg-border" />
        <p className="flex-1">
          <span className="font-medium text-text-primary">{labeled.label}</span>
          {labeled.body ? `: ${labeled.body}` : ""}
        </p>
      </div>
    );
  }

  return (
    <div key={index} className="flex gap-3 text-sm leading-7 text-text-primary">
      <span className="mt-[0.7em] h-1.5 w-1.5 rounded-full bg-border" />
      <p className="flex-1">{stripMarkdown(item.text)}</p>
    </div>
  );
}

function getCouncilRuntimeIssue(councilNote: CouncilNote | null) {
  if (!councilNote || councilNote.full_debate.length === 0) return null;
  const allErrors = councilNote.full_debate.every((entry) =>
    entry.response.startsWith("[ERROR:"),
  );
  if (!allErrors) return null;
  return "Latest saved council note contains only runtime errors. Re-run council after fixing Gemini access in the backend environment.";
}

function getErrorMessage(error: unknown) {
  if (
    typeof error === "object" &&
    error !== null &&
    "response" in error &&
    typeof error.response === "object" &&
    error.response !== null &&
    "data" in error.response &&
    typeof error.response.data === "object" &&
    error.response.data !== null &&
    "detail" in error.response.data &&
    typeof error.response.data.detail === "string"
  ) {
    return error.response.data.detail;
  }
  if (error instanceof Error) return error.message;
  return "Request failed.";
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function CouncilSummaryPanel({ councilNote }: { councilNote: CouncilNote }) {
  return (
    <div className="space-y-5">
      <section className="rounded-[20px] border border-border bg-surface-muted/60 px-5 py-5">
        <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-primary">Summary</p>
        <p className="mt-3 text-sm leading-7 text-text-primary">{councilNote.summary}</p>
      </section>

      <div className="grid gap-4 lg:grid-cols-[1.2fr,0.8fr]">
        <section className="rounded-[20px] border border-border bg-surface-muted/60 px-5 py-5">
          <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-text-muted">Key agreements</p>
          <ul className="mt-4 space-y-3">
            {councilNote.key_agreements.map((item) => (
              <li key={item} className="flex gap-3 text-sm leading-6 text-text-primary">
                <span className="mt-[0.55em] h-1.5 w-1.5 shrink-0 rounded-full bg-success" />
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </section>

        <section className="rounded-[20px] border border-border bg-surface-muted/60 px-5 py-5">
          <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-text-muted">Key disagreements</p>
          {councilNote.key_disagreements.length === 0 ||
          (councilNote.key_disagreements.length === 1 &&
            councilNote.key_disagreements[0].toLowerCase() === "none") ? (
            <p className="mt-4 text-sm italic text-text-muted">No disagreements recorded.</p>
          ) : (
            <ul className="mt-4 space-y-3">
              {councilNote.key_disagreements.map((item) => (
                <li key={item} className="flex gap-3 text-sm leading-6 text-text-secondary">
                  <span className="mt-[0.55em] h-1.5 w-1.5 shrink-0 rounded-full bg-warning" />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

      <section className="rounded-[20px] border-l-[3px] border-l-primary border border-border bg-primary-subtle/40 px-5 py-5">
        <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-primary">Final recommendation</p>
        <p className="mt-3 text-sm leading-7 text-text-primary">{councilNote.final_recommendation}</p>
      </section>
    </div>
  );
}

function CouncilParticipantPanel({
  participantView,
}: {
  participantView: CouncilParticipantView;
}) {
  const leadSection = participantView.sections.find((section) => section.title === null);
  const namedSections = participantView.sections.filter((section) => section.title !== null);

  return (
    <div className="space-y-4">
      <section className="rounded-[20px] border border-border bg-surface-muted px-4 py-4">
        <div className="flex flex-wrap items-center gap-2">
          <span className="rounded-full border border-border bg-surface/80 px-2.5 py-1 text-[11px] font-medium uppercase tracking-[0.12em] text-text-muted">
            Active view
          </span>
          {participantView.latestEntry ? (
            <span className="rounded-full border border-border bg-surface/80 px-2.5 py-1 text-[11px] text-text-secondary">
              Round {participantView.latestEntry.round}
            </span>
          ) : null}
        </div>
        <h3 className="mt-3 text-xl font-semibold text-text-primary">
          {participantView.participant}
        </h3>
        {participantView.latestEntry ? (
          <p className="mt-2 text-xs text-text-secondary">
            Latest response: {participantView.latestEntry.timestamp}
          </p>
        ) : null}
      </section>

      {leadSection ? (
        <section className="rounded-[20px] border border-border bg-surface-muted/60 px-4 py-4">
          <p className="text-xs font-medium uppercase tracking-[0.12em] text-text-muted">Perspective overview</p>
          <div className="mt-3 space-y-3">
            {leadSection.items.map(renderCouncilSectionItem)}
          </div>
        </section>
      ) : null}

      <div className="grid gap-4">
        {namedSections.map((section) => (
          <section
            key={section.title}
            className="rounded-[20px] border border-border bg-surface-muted/60 px-4 py-4"
          >
            <p className="text-xs font-medium uppercase tracking-[0.12em] text-text-muted">
              {section.title}
            </p>
            <div className="mt-3 space-y-3">
              {section.items.map(renderCouncilSectionItem)}
            </div>
          </section>
        ))}
      </div>

      {participantView.vote ? (
        <section className="rounded-[20px] border border-border bg-surface-muted/60 px-4 py-4">
          <p className="text-xs font-medium uppercase tracking-[0.12em] text-text-muted">Latest vote</p>
          <div className="mt-3 grid gap-3 md:grid-cols-[1fr,auto] md:items-start">
            <div className="space-y-2">
              <p className="text-sm font-medium text-text-primary">{participantView.vote.option}</p>
              <p className="text-sm leading-6 text-text-secondary">{participantView.vote.rationale}</p>
            </div>
            {participantView.vote.confidence !== null ? (
              <span className="rounded-full border border-border bg-surface px-3 py-1 text-sm font-medium text-text-primary">
                {Math.round(participantView.vote.confidence * 100)}% confidence
              </span>
            ) : null}
          </div>
        </section>
      ) : null}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface CouncilViewProps {
  processingFindings: ProcessingFinding[];
  councilNote: CouncilNote | null;
  defaultPerspectives: string[];
  onBack: () => void;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function CouncilView({
  processingFindings,
  councilNote,
  defaultPerspectives,
  onBack,
}: CouncilViewProps) {
  const { sendCouncilRequest, isLoading: isCouncilLoading } = useChat();
  const { settings } = useSettings();

  const [activeCouncilView, setActiveCouncilView] = useState(COUNCIL_SUMMARY_VIEW);
  const [selectedPerspectives, setSelectedPerspectives] = useState<string[]>(defaultPerspectives);
  const [debatePoint, setDebatePoint] = useState("");
  const [selectedFindingIds, setSelectedFindingIds] = useState<string[]>([]);
  const [councilErrorMessage, setCouncilErrorMessage] = useState<string | null>(null);
  const [validationMessage, setValidationMessage] = useState<string | null>(null);
  const [isTranscriptExpanded, setIsTranscriptExpanded] = useState(false);

  // Reset form when switching between conversations (defaultPerspectives identity changes)
  useEffect(() => {
    setSelectedPerspectives(defaultPerspectives);
    setDebatePoint("");
    setSelectedFindingIds([]);
    setActiveCouncilView(COUNCIL_SUMMARY_VIEW);
    setCouncilErrorMessage(null);
    setValidationMessage(null);
    setIsTranscriptExpanded(false);
  }, [defaultPerspectives]);

  // Reset active tab when new council note arrives
  useEffect(() => {
    setActiveCouncilView(COUNCIL_SUMMARY_VIEW);
  }, [councilNote]);

  async function handleCouncilSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (selectedPerspectives.length < 2) {
      setValidationMessage("Select at least 2 perspectives before running council.");
      return;
    }

    if (debatePoint.trim() === "" && selectedFindingIds.length === 0) {
      setValidationMessage(
        "Enter a debate point or select at least one finding before running council.",
      );
      return;
    }

    setValidationMessage(null);
    setCouncilErrorMessage(null);

    try {
      await sendCouncilRequest({
        debatePoint: debatePoint.trim(),
        findingIds: selectedFindingIds,
        perspectives: selectedPerspectives,
        councilSettings: {
          mode: settings.councilSettings.mode,
          rounds: settings.councilSettings.rounds,
          timeout_seconds: settings.councilSettings.timeoutSeconds,
          vote_retry_enabled: settings.councilSettings.voteRetryEnabled,
          vote_retry_attempts: settings.councilSettings.voteRetryAttempts,
        },
      });
      setIsTranscriptExpanded(false);
    } catch (error) {
      setCouncilErrorMessage(getErrorMessage(error));
    }
  }

  function togglePerspective(perspective: string) {
    setSelectedPerspectives((current) =>
      current.includes(perspective)
        ? current.filter((value) => value !== perspective)
        : [...current, perspective],
    );
    setValidationMessage(null);
  }

  function toggleFinding(findingId: string) {
    setSelectedFindingIds((current) =>
      current.includes(findingId)
        ? current.filter((value) => value !== findingId)
        : [...current, findingId],
    );
    setValidationMessage(null);
  }

  const councilParticipantViews = useMemo(
    () => (councilNote ? buildCouncilParticipantViews(councilNote) : []),
    [councilNote],
  );

  const councilRuntimeIssue = getCouncilRuntimeIssue(councilNote);
  const activeParticipantView =
    activeCouncilView === COUNCIL_SUMMARY_VIEW
      ? null
      : (councilParticipantViews.find((view) => view.participant === activeCouncilView) ?? null);

  return (
    <div className="mx-auto max-w-6xl space-y-8 pb-8">
      {/* Back button */}
      <div>
        <button
          type="button"
          onClick={onBack}
          className="inline-flex items-center gap-2 rounded-[14px] border border-border bg-surface px-4 py-2 text-sm font-medium text-text-secondary hover:text-text-primary hover:bg-surface-muted transition-colors"
        >
          ← Back to analysis
        </button>
      </div>

      <section className="grid gap-4 xl:grid-cols-[0.95fr,1.05fr]">
        {/* Council form */}
        <article className="rounded-[24px] border border-border bg-surface px-5 py-5 shadow-sm">
          <p className="text-xs font-medium uppercase tracking-[0.12em] text-text-muted">
            Run council on a point
          </p>
          <p className="mt-2 text-sm leading-6 text-text-secondary">
            The Council simulates structured deliberation between analytical perspectives, surfacing agreements, disagreements, and a final recommendation.
          </p>
          <form className="mt-4 space-y-4" onSubmit={handleCouncilSubmit}>
            <div className="space-y-2">
              <p className="text-sm font-medium text-text-primary">Perspectives</p>
              <div className="flex flex-wrap gap-2">
                {PERSPECTIVE_ORDER.map((perspective) => {
                  const isSelected = selectedPerspectives.includes(perspective);
                  return (
                    <button
                      key={perspective}
                      type="button"
                      onClick={() => togglePerspective(perspective)}
                      aria-pressed={isSelected}
                      className={`rounded-full border px-3 py-1.5 text-xs font-medium transition-colors ${
                        isSelected
                          ? "border-primary/40 bg-primary-subtle/40 text-text-primary"
                          : "border-border-muted text-text-secondary hover:border-border hover:text-text-primary"
                      }`}
                    >
                      {formatPerspectiveLabel(perspective)}
                    </button>
                  );
                })}
              </div>
              <p className="text-xs text-text-secondary">
                Runtime: {settings.councilSettings.mode},{" "}
                {settings.councilSettings.rounds} round
                {settings.councilSettings.rounds === 1 ? "" : "s"}, timeout{" "}
                {settings.councilSettings.timeoutSeconds}s, vote retry{" "}
                {settings.councilSettings.voteRetryEnabled
                  ? `${settings.councilSettings.voteRetryAttempts}x`
                  : "off"}
              </p>
            </div>

            <div className="space-y-2">
              <label
                htmlFor="analysis-debate-point"
                className="text-sm font-medium text-text-primary"
              >
                Debate point
              </label>
              <textarea
                id="analysis-debate-point"
                value={debatePoint}
                onChange={(event) => {
                  setDebatePoint(event.target.value);
                  setValidationMessage(null);
                }}
                rows={4}
                className="w-full rounded-[18px] border border-border bg-background px-3 py-3 text-sm text-text-primary"
                placeholder="State the analytical point the council should debate."
              />
            </div>

            <div className="space-y-2">
              <p className="text-sm font-medium text-text-primary">Findings in scope</p>
              <div className="space-y-2">
                {processingFindings.map((finding) => (
                  <label
                    key={finding.id}
                    className="flex items-start gap-3 rounded-[18px] border border-border-muted px-3 py-3"
                  >
                    <input
                      type="checkbox"
                      checked={selectedFindingIds.includes(finding.id)}
                      onChange={() => toggleFinding(finding.id)}
                      className="mt-1"
                    />
                    <span className="text-sm text-text-primary">
                      <span className="font-medium">{finding.id}</span>{" "}
                      {finding.title}
                    </span>
                  </label>
                ))}
              </div>
            </div>

            {validationMessage ? (
              <p className="rounded-[16px] bg-error-subtle px-3 py-2 text-sm text-error-text">
                {validationMessage}
              </p>
            ) : null}
            {councilErrorMessage ? (
              <p className="rounded-[16px] bg-error-subtle px-3 py-2 text-sm text-error-text">
                {councilErrorMessage}
              </p>
            ) : null}

            <button
              type="submit"
              disabled={isCouncilLoading}
              className="rounded-[18px] border border-border bg-surface-muted px-4 py-2.5 text-sm font-medium text-text-primary disabled:opacity-60"
            >
              {isCouncilLoading ? "Running council..." : "Run council"}
            </button>
          </form>
        </article>

        {/* Advisory note */}
        <article className="rounded-[24px] border border-border bg-surface px-5 py-5 shadow-sm">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-primary">
                Council Note
              </p>
              <h2 className="mt-1 text-2xl font-semibold text-text-primary">Advisory note</h2>
            </div>
            {councilNote ? (
              <span className="rounded-full border border-primary/30 bg-primary-subtle px-3 py-1 text-xs font-medium text-primary">
                {councilNote.rounds_completed} rounds
              </span>
            ) : null}
          </div>

          {!councilNote ? (
            <p className="mt-4 text-sm leading-6 text-text-secondary">
              Run a council deliberation to generate a separate advisory note for this assessment.
            </p>
          ) : (
            <div className="mt-4 space-y-4">
              {councilRuntimeIssue ? (
                <div className="rounded-[18px] border border-error bg-error-subtle px-4 py-3">
                  <p className="text-sm text-error-text">{councilRuntimeIssue}</p>
                </div>
              ) : null}

              <div className="rounded-[14px] border border-border-muted bg-surface-muted/40 px-4 py-3">
                <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-text-muted">
                  Debate point
                </p>
                <p className="mt-1.5 text-sm leading-6 text-text-primary">{councilNote.question}</p>
              </div>

              <div className="flex flex-wrap gap-1.5 rounded-[14px] border border-border-muted bg-surface-muted/50 p-1.5">
                <button
                  type="button"
                  onClick={() => setActiveCouncilView(COUNCIL_SUMMARY_VIEW)}
                  aria-pressed={activeCouncilView === COUNCIL_SUMMARY_VIEW}
                  className={
                    activeCouncilView === COUNCIL_SUMMARY_VIEW
                      ? "rounded-[10px] bg-surface px-3 py-1.5 text-xs font-medium text-text-primary shadow-sm"
                      : "rounded-[10px] px-3 py-1.5 text-xs text-text-secondary hover:text-text-primary"
                  }
                >
                  Council Summary
                </button>
                {councilParticipantViews.map((participantView) => (
                  <button
                    key={participantView.participant}
                    type="button"
                    onClick={() => setActiveCouncilView(participantView.participant)}
                    aria-pressed={activeCouncilView === participantView.participant}
                    className={
                      activeCouncilView === participantView.participant
                        ? "rounded-[10px] bg-surface px-3 py-1.5 text-xs font-medium text-text-primary shadow-sm"
                        : "rounded-[10px] px-3 py-1.5 text-xs text-text-secondary hover:text-text-primary"
                    }
                  >
                    {participantView.participant}
                  </button>
                ))}
              </div>

              {activeParticipantView ? (
                <CouncilParticipantPanel participantView={activeParticipantView} />
              ) : (
                <CouncilSummaryPanel councilNote={councilNote} />
              )}

              <div className="space-y-2 border-t border-border-muted pt-4">
                <button
                  type="button"
                  onClick={() => setIsTranscriptExpanded((current) => !current)}
                  className="inline-flex items-center gap-2 rounded-[12px] border border-border px-4 py-2 text-sm font-medium text-text-primary transition-colors hover:bg-surface-muted"
                >
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className={`text-text-muted transition-transform duration-150 ${isTranscriptExpanded ? "rotate-180" : ""}`}>
                    <path d="M6 9l6 6 6-6" />
                  </svg>
                  {isTranscriptExpanded ? "Hide full debate" : "Show full debate"}
                </button>
                {councilNote.transcript_path ? (
                  <p className="text-[11px] text-text-muted">
                    Transcript path: {councilNote.transcript_path}
                  </p>
                ) : null}
              </div>

              {isTranscriptExpanded ? (
                <div className="space-y-3">
                  {councilNote.full_debate.map((entry, index) => (
                    <article
                      key={`${entry.round}-${entry.participant}-${index}`}
                      className="rounded-[18px] border border-border bg-surface-muted/60 px-4 py-4"
                    >
                      <div className="flex items-center justify-between gap-3">
                        <p className="text-sm font-medium text-text-primary">
                          Round {entry.round}: {entry.participant}
                        </p>
                        <span className="text-xs text-text-secondary">{entry.timestamp}</span>
                      </div>
                      <p className="mt-2 text-sm leading-6 text-text-primary">{entry.response}</p>
                    </article>
                  ))}
                </div>
              ) : null}
            </div>
          )}
        </article>
      </section>
    </div>
  );
}
