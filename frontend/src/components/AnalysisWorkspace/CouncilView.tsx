import { useEffect, useMemo, useState, type FormEvent } from "react";
import { pdf } from "@react-pdf/renderer";
import { useChat } from "../../hooks/useChat/useChat";
import { useSettings } from "../../contexts/SettingsContext/SettingsContext";
import type {
  CouncilNote,
  CouncilTranscriptEntry,
  ProcessingFinding,
} from "../../types/analysis";
import CouncilReportPDF from "./CouncilReportPDF";

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

    const inlineHeadingMatch = line.match(/^\*\*(.+?)\*\*:?\s+(.+)$/);
    if (inlineHeadingMatch) {
      flushSection();
      currentSection = { title: normalizeSectionTitle(inlineHeadingMatch[1]), items: [] };
      paragraphBuffer.push(inlineHeadingMatch[2].trim());
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

function extractSummary(body: string): string {
  const cleaned = stripMarkdown(body).replace(/\n+/g, " ").trim();
  const sentenceEnd = /[.!?]\s+/g;
  let count = 0;
  let lastIndex = 0;
  let match: RegExpExecArray | null;
  while ((match = sentenceEnd.exec(cleaned)) !== null) {
    count++;
    lastIndex = match.index + match[0].length;
    if (count >= 2) break;
  }
  const excerpt = count > 0 ? cleaned.slice(0, lastIndex).trim() : cleaned;
  if (excerpt.length <= 220) return excerpt;
  return excerpt.slice(0, 217) + "…";
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
  const hasDisagreements =
    councilNote.key_disagreements.length > 0 &&
    !(councilNote.key_disagreements.length === 1 &&
      councilNote.key_disagreements[0].toLowerCase() === "none");

  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm font-semibold text-text-primary">Summary</p>
        <p className="mt-2 text-sm leading-7 text-text-primary">{councilNote.summary}</p>
      </div>

      <div>
        <p className="text-sm font-semibold text-text-primary">Key Agreements</p>
        <ul className="mt-2 space-y-2">
          {councilNote.key_agreements.map((item) => (
            <li key={item} className="flex gap-3 text-sm leading-6 text-text-primary">
              <span className="mt-[0.55em] h-1.5 w-1.5 shrink-0 rounded-full bg-success" />
              <span>{item}</span>
            </li>
          ))}
        </ul>
      </div>

      <div>
        <p className="text-sm font-semibold text-text-primary">Key Disagreements</p>
        {hasDisagreements ? (
          <ul className="mt-2 space-y-2">
            {councilNote.key_disagreements.map((item) => (
              <li key={item} className="flex gap-3 text-sm leading-6 text-text-primary">
                <span className="mt-[0.55em] h-1.5 w-1.5 shrink-0 rounded-full bg-warning" />
                <span>{item}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-2 text-sm italic text-text-muted">No disagreements recorded.</p>
        )}
      </div>

      <div>
        <p className="text-sm font-semibold text-text-primary">Final Recommendation</p>
        <p className="mt-2 text-sm leading-7 text-text-primary">{councilNote.final_recommendation}</p>
      </div>
    </div>
  );
}

function CouncilParticipantPanel({
  participantView,
}: {
  participantView: CouncilParticipantView;
}) {
  return (
    <div className="space-y-6">
      {participantView.sections.map((section, si) => (
        <div key={si}>
          {section.title ? (
            <p className="mb-2 text-sm font-semibold text-text-primary">{section.title}</p>
          ) : null}
          <div className="space-y-3">
            {section.items.map(renderCouncilSectionItem)}
          </div>
        </div>
      ))}

      {participantView.vote ? (
        <div>
          <p className="mb-2 text-sm font-semibold text-text-primary">Vote</p>
          <div className="flex flex-wrap items-start gap-3">
            <div className="flex-1 space-y-1">
              <p className="text-sm font-medium text-text-primary">{participantView.vote.option}</p>
              <p className="text-sm leading-6 text-text-secondary">{participantView.vote.rationale}</p>
            </div>
            {participantView.vote.confidence !== null ? (
              <span className="rounded-full border border-border bg-surface px-3 py-1 text-sm font-medium text-text-primary">
                {Math.round(participantView.vote.confidence * 100)}% confidence
              </span>
            ) : null}
          </div>
        </div>
      ) : null}
    </div>
  );
}

function CollapsibleRound({ roundNumber, entries }: { roundNumber: number; entries: CouncilTranscriptEntry[] }) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="rounded-[14px] border border-border-muted overflow-hidden">
      {/* Round header — always visible, shows participant summaries */}
      <button
        type="button"
        onClick={() => setIsOpen((v) => !v)}
        className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left hover:bg-surface-muted/50 transition-colors"
      >
        <span className="text-sm font-semibold text-text-primary">Round {roundNumber}</span>
        <svg
          width="12"
          height="12"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          className={`shrink-0 text-text-muted transition-transform duration-150 ${isOpen ? "rotate-180" : ""}`}
        >
          <path d="M6 9l6 6 6-6" />
        </svg>
      </button>

      {/* Participant summaries — shown in the collapsed header area */}
      <div className="border-t border-border-muted divide-y divide-border-muted/60">
        {entries.map((entry, i) => {
          const { body, vote } = splitVoteFromResponse(entry.response);
          const summary = entry.summary ?? extractSummary(body);
          const shortName = entry.participant
            .replace(/\b(Strategic|Policy|Senior|Junior|Chief|Lead)\b\s*/gi, "")
            .trim();
          return (
            <div key={i} className="px-4 py-3 space-y-1">
              <p className="text-xs font-semibold text-text-primary">{shortName}</p>
              <p className="text-sm leading-6 text-text-secondary">{summary}</p>
              {vote ? (
                <div className="flex flex-wrap items-center gap-2 pt-0.5">
                  <span className="text-xs font-medium text-text-primary">{vote.option}</span>
                  {vote.confidence !== null ? (
                    <span className="rounded-full border border-border bg-surface px-2.5 py-0.5 text-xs font-medium text-text-primary">
                      {Math.round(vote.confidence * 100)}%
                    </span>
                  ) : null}
                </div>
              ) : null}
            </div>
          );
        })}
      </div>

      {/* Full responses — shown only when expanded */}
      {isOpen ? (
        <div className="border-t border-border-muted bg-surface-muted/20 px-4 py-4 space-y-6">
          {entries.map((entry, index) => {
            const { body, vote } = splitVoteFromResponse(entry.response);
            const sections = buildCouncilSections(body);
            return (
              <div key={`${entry.round}-${entry.participant}-${index}`}>
                <div className="mb-4 flex items-baseline justify-between gap-3 border-b border-border-muted pb-2">
                  <p className="text-sm font-semibold text-text-primary">
                    {entry.participant}
                  </p>
                  <span className="text-xs text-text-muted">{entry.timestamp}</span>
                </div>
                <div className="space-y-5">
                  {sections.map((section, si) => (
                    <div key={si}>
                      {section.title ? (
                        <p className="mb-2 text-sm font-semibold text-text-primary">{section.title}</p>
                      ) : null}
                      <div className="space-y-3">
                        {section.items.map(renderCouncilSectionItem)}
                      </div>
                    </div>
                  ))}
                  {vote ? (
                    <div>
                      <p className="mb-2 text-sm font-semibold text-text-primary">Vote</p>
                      <div className="flex flex-wrap items-start gap-3">
                        <div className="flex-1 space-y-1">
                          <p className="text-sm font-medium text-text-primary">{vote.option}</p>
                          <p className="text-sm leading-6 text-text-secondary">{vote.rationale}</p>
                        </div>
                        {vote.confidence !== null ? (
                          <span className="rounded-full border border-border bg-surface px-2.5 py-0.5 text-xs font-medium text-text-primary">
                            {Math.round(vote.confidence * 100)}% confidence
                          </span>
                        ) : null}
                      </div>
                    </div>
                  ) : null}
                </div>
              </div>
            );
          })}
        </div>
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

  async function handleDownloadPDF() {
    if (!councilNote) return;
    const blob = await pdf(<CouncilReportPDF councilNote={councilNote} />).toBlob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `council_${councilNote.question.slice(0, 50).replace(/[^a-z0-9 ]/gi, "").trim().replace(/\s+/g, "_")}.pdf`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <>
      {councilNote && (
        <div className="flex justify-end pb-2">
          <button
            onClick={handleDownloadPDF}
            className="rounded-md bg-primary px-3 py-1.5 text-xs font-semibold text-text-inverse transition-opacity hover:opacity-80"
          >
            Download PDF
          </button>
        </div>
      )}
      <div className="mx-auto max-w-4xl space-y-10 pb-12 pt-2 px-5">
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

      <section className="grid gap-6 xl:grid-cols-[0.95fr,1.05fr]">
        {/* Council form */}
        <article className="space-y-1">
          <p className="text-xs font-medium uppercase tracking-[0.12em] text-text-muted">
            Run council on a point
          </p>
          <p className="text-sm leading-6 text-text-secondary">
            The Council simulates structured deliberation between analytical perspectives, surfacing agreements, disagreements, and a final recommendation.
          </p>
          <form className="pt-2 space-y-4" onSubmit={handleCouncilSubmit}>
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
                          ? "border-primary bg-primary-subtle text-primary"
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
              <div className="flex items-center justify-between">
                <p className="text-sm font-medium text-text-primary">Findings in scope</p>
                <button
                  type="button"
                  onClick={() =>
                    selectedFindingIds.length === processingFindings.length
                      ? setSelectedFindingIds([])
                      : setSelectedFindingIds(processingFindings.map((f) => f.id))
                  }
                  className="text-xs text-text-muted hover:text-text-primary transition-colors"
                >
                  {selectedFindingIds.length === processingFindings.length ? "Deselect all" : "Select all"}
                </button>
              </div>
              <div className="overflow-hidden rounded-[18px] border border-border/50 divide-y divide-border/50">
                {processingFindings.map((finding) => {
                  const isSelected = selectedFindingIds.includes(finding.id);
                  return (
                    <button
                      key={finding.id}
                      type="button"
                      onClick={() => toggleFinding(finding.id)}
                      aria-pressed={isSelected}
                      aria-label={`${finding.id} ${finding.title}`}
                      className={`flex w-full items-center gap-3 px-4 py-3 text-left transition-colors ${
                        isSelected ? "bg-primary-subtle/40" : "hover:bg-surface-muted/50"
                      }`}
                    >
                      <span className={`flex h-4 w-4 shrink-0 items-center justify-center rounded border transition-colors ${
                        isSelected ? "border-primary bg-primary" : "border-border"
                      }`}>
                        {isSelected && (
                          <svg width="9" height="9" viewBox="0 0 12 12" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                            <path d="M2 6l3 3 5-5" />
                          </svg>
                        )}
                      </span>
                      <span className="text-sm text-text-primary">
                        <span className="font-medium">{finding.id}</span>{" "}
                        {finding.title}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>

            {validationMessage ? (
              <p className="rounded-2xl bg-error-subtle px-3 py-2 text-sm text-error-text">
                {validationMessage}
              </p>
            ) : null}
            {councilErrorMessage ? (
              <p className="rounded-2xl bg-error-subtle px-3 py-2 text-sm text-error-text">
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
        <article className="space-y-4 xl:border-t-0 border-t border-border-muted pt-6 xl:pt-0">
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
            <p className="text-sm leading-6 text-text-secondary">
              Run a council deliberation to generate a separate advisory note for this assessment.
            </p>
          ) : (
            <div className="space-y-4">
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

              <div className="inline-flex max-w-full overflow-hidden items-center gap-1.5 rounded-[14px] border border-border bg-surface-muted/50 p-1.5">
                <button
                  type="button"
                  onClick={() => setActiveCouncilView(COUNCIL_SUMMARY_VIEW)}
                  aria-pressed={activeCouncilView === COUNCIL_SUMMARY_VIEW}
                  className={
                    activeCouncilView === COUNCIL_SUMMARY_VIEW
                      ? "rounded-[10px] border border-primary bg-primary-subtle px-3 py-1.5 text-xs font-medium text-primary"
                      : "rounded-[10px] border border-transparent px-3 py-1.5 text-xs text-text-secondary hover:text-text-primary"
                  }
                >
                  Summary
                </button>
                <span className="h-4 w-px bg-border mx-1" />
                {councilParticipantViews.map((participantView) => (
                  <button
                    key={participantView.participant}
                    type="button"
                    onClick={() => setActiveCouncilView(participantView.participant)}
                    aria-pressed={activeCouncilView === participantView.participant}
                    className={
                      activeCouncilView === participantView.participant
                        ? "rounded-[10px] border border-primary bg-primary-subtle px-3 py-1.5 text-xs font-medium text-primary"
                        : "rounded-[10px] border border-transparent px-3 py-1.5 text-xs text-text-secondary hover:text-text-primary"
                    }
                  >
                    {participantView.participant.replace(/\b(Strategic|Policy|Senior|Junior|Chief|Lead)\b\s*/gi, "").trim()}
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
                  className="inline-flex items-center gap-2 rounded-xl border border-border px-4 py-2 text-sm font-medium text-text-primary transition-colors hover:bg-surface-muted"
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
                  {Object.entries(
                    councilNote.full_debate.reduce<Record<number, CouncilTranscriptEntry[]>>(
                      (acc, entry) => {
                        (acc[entry.round] ??= []).push(entry);
                        return acc;
                      },
                      {},
                    ),
                  )
                    .sort(([a], [b]) => Number(a) - Number(b))
                    .map(([round, entries]) => (
                      <CollapsibleRound key={round} roundNumber={Number(round)} entries={entries} />
                    ))}
                </div>
              ) : null}
            </div>
          )}
        </article>
      </section>
    </div>
    </>
  );
}
