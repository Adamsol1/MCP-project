import { useEffect, useState, type FormEvent } from "react";
import { useConversation } from "../../hooks/useConversation";
import { useSettings } from "../../contexts/SettingsContext/SettingsContext";
import {
  getAnalysisDraft,
  runAnalysisCouncil,
} from "../../services/analysis";
import type {
  AnalysisDraftResponse,
  CouncilNote,
  ProcessingFinding,
} from "../../types/analysis";

const PERSPECTIVE_ORDER = [
  "us",
  "norway",
  "china",
  "eu",
  "russia",
  "neutral",
];

function formatPerspectiveLabel(key: string) {
  return key === "us" || key === "eu"
    ? key.toUpperCase()
    : key.charAt(0).toUpperCase() + key.slice(1);
}

function formatSupportingDataLabel(key: string) {
  return key.replace(/_/g, " ");
}

function formatSourceLabel(source: string) {
  return source.replace(/_/g, " ");
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

  if (error instanceof Error) {
    return error.message;
  }

  return "Request failed.";
}

function normalizePerspectives(perspectives: string[] | undefined) {
  const normalized = perspectives
    ?.map((value) => value.toLowerCase())
    .filter((value) => PERSPECTIVE_ORDER.includes(value));

  if (!normalized || normalized.length === 0) {
    return ["neutral"];
  }

  return PERSPECTIVE_ORDER.filter((value) => normalized.includes(value));
}

function getAverageConfidence(findings: ProcessingFinding[]) {
  if (findings.length === 0) {
    return 0;
  }

  const total = findings.reduce((sum, finding) => sum + finding.confidence, 0);
  return Math.round(total / findings.length);
}

function getCouncilRuntimeIssue(councilNote: CouncilNote | null) {
  if (!councilNote || councilNote.full_debate.length === 0) {
    return null;
  }

  const allErrors = councilNote.full_debate.every((entry) =>
    entry.response.startsWith("[ERROR:"),
  );

  if (!allErrors) {
    return null;
  }

  return "Latest saved council note contains only runtime errors. Re-run council after fixing the Gemini CLI in the backend environment.";
}

function getFindingPreview(finding: ProcessingFinding) {
  return `${finding.evidence_summary} ${finding.why_it_matters}`;
}

export default function AnalysisPrototypeView() {
  const { activeConversation } = useConversation();
  const { settings } = useSettings();
  const [data, setData] = useState<AnalysisDraftResponse | null>(null);
  const [councilNote, setCouncilNote] = useState<CouncilNote | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [selectedPerspectives, setSelectedPerspectives] = useState<string[]>([
    "neutral",
  ]);
  const [debatePoint, setDebatePoint] = useState("");
  const [selectedFindingIds, setSelectedFindingIds] = useState<string[]>([]);
  const [isCouncilLoading, setIsCouncilLoading] = useState(false);
  const [councilErrorMessage, setCouncilErrorMessage] = useState<string | null>(
    null,
  );
  const [validationMessage, setValidationMessage] = useState<string | null>(null);
  const [isTranscriptExpanded, setIsTranscriptExpanded] = useState(false);

  useEffect(() => {
    setSelectedPerspectives(
      normalizePerspectives(activeConversation?.perspectives),
    );
    setDebatePoint("");
    setSelectedFindingIds([]);
    setCouncilNote(null);
    setCouncilErrorMessage(null);
    setValidationMessage(null);
    setIsTranscriptExpanded(false);
  }, [
    activeConversation?.sessionId,
    activeConversation?.perspectives?.join(","),
  ]);

  useEffect(() => {
    let isCancelled = false;

    async function loadDraft(sessionId: string) {
      setIsLoading(true);
      setErrorMessage(null);

      try {
        const response = await getAnalysisDraft(sessionId);
        if (!isCancelled) {
          setData(response);
          setCouncilNote(response.latest_council_note);
        }
      } catch (error) {
        if (!isCancelled) {
          setData(null);
          setCouncilNote(null);
          setErrorMessage(getErrorMessage(error));
        }
      } finally {
        if (!isCancelled) {
          setIsLoading(false);
        }
      }
    }

    if (!activeConversation?.sessionId) {
      setData(null);
      setIsLoading(false);
      setErrorMessage(null);
      return () => {
        isCancelled = true;
      };
    }

    void loadDraft(activeConversation.sessionId);

    return () => {
      isCancelled = true;
    };
  }, [activeConversation?.sessionId]);

  async function handleCouncilSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!activeConversation?.sessionId || !data) {
      return;
    }

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
    setIsCouncilLoading(true);

    try {
      const response = await runAnalysisCouncil({
        session_id: activeConversation.sessionId,
        debate_point: debatePoint.trim(),
        finding_ids: selectedFindingIds,
        selected_perspectives: selectedPerspectives,
        council_settings: {
          mode: settings.councilSettings.mode,
          rounds: settings.councilSettings.rounds,
          timeout_seconds: settings.councilSettings.timeoutSeconds,
          vote_retry_enabled: settings.councilSettings.voteRetryEnabled,
          vote_retry_attempts: settings.councilSettings.voteRetryAttempts,
        },
      });
      setCouncilNote(response);
      setIsTranscriptExpanded(false);
    } catch (error) {
      setCouncilErrorMessage(getErrorMessage(error));
    } finally {
      setIsCouncilLoading(false);
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

  if (!activeConversation?.sessionId) {
    return (
      <p className="text-sm text-text-secondary">
        Create or select a conversation to load the analysis prototype.
      </p>
    );
  }

  if (isLoading) {
    return (
      <div className="space-y-3" aria-live="polite">
        <p className="text-xs font-medium uppercase tracking-[0.12em] text-text-muted">
          Draft Analysis
        </p>
        <div className="rounded-[24px] border border-border bg-surface px-5 py-6">
          <p className="text-sm text-text-secondary">Loading analysis draft...</p>
        </div>
      </div>
    );
  }

  if (errorMessage) {
    return (
      <div className="rounded-[24px] border border-error bg-error-subtle p-5">
        <p className="text-xs font-medium uppercase tracking-[0.12em] text-error-text">
          Analysis Error
        </p>
        <p className="mt-2 text-sm text-error-text">
          Failed to load analysis draft.
        </p>
        <p className="mt-1 text-xs text-error-text/80">{errorMessage}</p>
      </div>
    );
  }

  if (!data) {
    return (
      <p className="text-sm text-text-secondary">
        Analysis draft is not available for this session.
      </p>
    );
  }

  const { processing_result: processingResult, analysis_draft: analysisDraft } = data;
  const averageConfidence = getAverageConfidence(processingResult.findings);
  const orderedPerspectiveEntries = PERSPECTIVE_ORDER.filter(
    (key) => key in analysisDraft.per_perspective_implications,
  ).map((key) => [key, analysisDraft.per_perspective_implications[key]] as const);
  const councilRuntimeIssue = getCouncilRuntimeIssue(councilNote);

  return (
    <div className="mx-auto max-w-6xl space-y-8 pb-8">
      <section className="overflow-hidden rounded-[28px] border border-border bg-[linear-gradient(135deg,#f4efe6_0%,#edf3f4_48%,#f5f7fb_100%)] shadow-sm">
        <div className="grid gap-6 px-6 py-6 lg:grid-cols-[1.5fr,0.9fr]">
          <div className="space-y-4">
            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded-full border border-border bg-white/75 px-3 py-1 text-[11px] font-medium uppercase tracking-[0.18em] text-text-muted">
                Draft Analysis
              </span>
              <span className="rounded-full border border-border bg-white/55 px-3 py-1 text-[11px] text-text-secondary">
                Demo-backed assessment
              </span>
            </div>
            <div>
              <h1 className="font-serif text-3xl leading-tight text-text-primary">
                Northern Europe telecom access-development assessment
              </h1>
              <p className="mt-3 max-w-3xl text-sm leading-6 text-text-secondary">
                {analysisDraft.summary}
              </p>
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-3 lg:grid-cols-2">
            <div className="rounded-[20px] border border-border bg-white/70 px-4 py-4">
              <p className="text-[11px] uppercase tracking-[0.16em] text-text-muted">
                Findings
              </p>
              <p className="mt-2 text-3xl font-semibold text-text-primary">
                {processingResult.findings.length}
              </p>
            </div>
            <div className="rounded-[20px] border border-border bg-white/70 px-4 py-4">
              <p className="text-[11px] uppercase tracking-[0.16em] text-text-muted">
                Avg confidence
              </p>
              <p className="mt-2 text-3xl font-semibold text-text-primary">
                {averageConfidence}
              </p>
            </div>
            <div className="rounded-[20px] border border-border bg-white/70 px-4 py-4">
              <p className="text-[11px] uppercase tracking-[0.16em] text-text-muted">
                Open gaps
              </p>
              <p className="mt-2 text-3xl font-semibold text-text-primary">
                {analysisDraft.information_gaps.length}
              </p>
            </div>
            <div className="rounded-[20px] border border-border bg-white/70 px-4 py-4">
              <p className="text-[11px] uppercase tracking-[0.16em] text-text-muted">
                Perspectives
              </p>
              <p className="mt-2 text-3xl font-semibold text-text-primary">
                {orderedPerspectiveEntries.length}
              </p>
            </div>
          </div>
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-[1.2fr,0.8fr]">
        <article className="rounded-[24px] border border-border bg-surface px-5 py-5 shadow-sm">
          <p className="text-xs font-medium uppercase tracking-[0.12em] text-text-muted">
            Key Judgments
          </p>
          <ul className="mt-4 grid gap-3">
            {analysisDraft.key_judgments.map((judgment, index) => (
              <li
                key={judgment}
                className="rounded-[18px] border border-border bg-surface-muted/60 px-4 py-4 text-sm leading-6 text-text-primary"
              >
                <span className="mb-2 inline-flex h-7 w-7 items-center justify-center rounded-full border border-border bg-surface text-xs font-semibold text-text-secondary">
                  {index + 1}
                </span>
                <p>{judgment}</p>
              </li>
            ))}
          </ul>
        </article>

        <div className="grid gap-4">
          <article className="rounded-[24px] border border-border bg-surface px-5 py-5 shadow-sm">
            <p className="text-xs font-medium uppercase tracking-[0.12em] text-text-muted">
              Recommended Actions
            </p>
            <ul className="mt-4 space-y-3">
              {analysisDraft.recommended_actions.map((action) => (
                <li key={action} className="text-sm leading-6 text-text-primary">
                  {action}
                </li>
              ))}
            </ul>
          </article>

          <article className="rounded-[24px] border border-border bg-surface px-5 py-5 shadow-sm">
            <p className="text-xs font-medium uppercase tracking-[0.12em] text-text-muted">
              Information Gaps
            </p>
            <ul className="mt-4 space-y-3">
              {analysisDraft.information_gaps.map((gap) => (
                <li key={gap} className="text-sm leading-6 text-text-secondary">
                  {gap}
                </li>
              ))}
            </ul>
          </article>
        </div>
      </section>

      <section className="space-y-4">
        <div className="flex items-end justify-between gap-4">
          <div>
            <p className="text-xs font-medium uppercase tracking-[0.12em] text-text-muted">
              Processing Findings
            </p>
            <h2 className="mt-1 text-2xl font-semibold text-text-primary">
              Evidence docket
            </h2>
          </div>
          <span className="rounded-full border border-border bg-surface-muted px-3 py-1 text-xs text-text-secondary">
            {processingResult.findings.length} findings
          </span>
        </div>

        <div className="space-y-4">
          {processingResult.findings.map((finding, index) => (
            <details
              key={finding.id}
              open={index === 0}
              className="group rounded-[24px] border border-border bg-surface shadow-sm"
            >
              <summary
                className="list-none cursor-pointer px-5 py-5"
                aria-label={`Finding ${finding.id}`}
              >
                <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                  <div className="space-y-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="rounded-full border border-border bg-surface-muted px-2.5 py-1 text-[11px] font-medium uppercase tracking-[0.16em] text-text-muted">
                        {finding.id}
                      </span>
                      <span className="rounded-full border border-border bg-white px-2.5 py-1 text-[11px] uppercase tracking-wide text-text-secondary">
                        {formatSourceLabel(finding.source)}
                      </span>
                      {finding.relevant_to.map((pirId) => (
                        <span
                          key={pirId}
                          className="rounded-full bg-surface-muted px-2.5 py-1 text-[11px] uppercase tracking-wide text-text-secondary"
                        >
                          {pirId}
                        </span>
                      ))}
                    </div>
                    <div>
                      <h3 className="text-lg font-semibold text-text-primary">
                        {finding.title}
                      </h3>
                      <p className="mt-2 max-w-3xl text-sm leading-6 text-text-secondary">
                        {getFindingPreview(finding)}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-3 lg:flex-col lg:items-end">
                    <span className="rounded-full border border-border bg-surface-muted px-3 py-1 text-sm font-medium text-text-primary">
                      {finding.confidence}% confidence
                    </span>
                    <span className="text-xs uppercase tracking-[0.14em] text-text-muted">
                      {index === 0 ? "Open" : "Expand"}
                    </span>
                  </div>
                </div>
              </summary>

              <div className="grid gap-5 border-t border-border px-5 py-5 lg:grid-cols-[1.4fr,0.9fr]">
                <div className="space-y-5">
                  <section>
                    <p className="text-xs font-medium uppercase tracking-[0.12em] text-text-muted">
                      Finding
                    </p>
                    <p className="mt-2 text-sm leading-7 text-text-primary">
                      {finding.finding}
                    </p>
                  </section>

                  <section>
                    <p className="text-xs font-medium uppercase tracking-[0.12em] text-text-muted">
                      Why it matters
                    </p>
                    <p className="mt-2 text-sm leading-7 text-text-primary">
                      {finding.why_it_matters}
                    </p>
                  </section>

                  <section>
                    <p className="text-xs font-medium uppercase tracking-[0.12em] text-text-muted">
                      Supporting data
                    </p>
                    <div className="mt-3 grid gap-3 md:grid-cols-2">
                      {Object.entries(finding.supporting_data)
                        .filter(([, values]) => values.length > 0)
                        .map(([key, values]) => (
                          <div
                            key={key}
                            className="rounded-[18px] border border-border bg-surface-muted/60 px-4 py-3"
                          >
                            <p className="text-[11px] font-medium uppercase tracking-[0.12em] text-text-muted">
                              {formatSupportingDataLabel(key)}
                            </p>
                            <div className="mt-2 flex flex-wrap gap-1.5">
                              {values.map((value) => (
                                <span
                                  key={`${key}-${value}`}
                                  className="rounded-md border border-border bg-surface px-2 py-1 text-xs text-text-secondary"
                                >
                                  {value}
                                </span>
                              ))}
                            </div>
                          </div>
                        ))}
                    </div>
                  </section>
                </div>

                <div className="space-y-5">
                  <section className="rounded-[20px] border border-border bg-surface-muted/60 px-4 py-4">
                    <p className="text-xs font-medium uppercase tracking-[0.12em] text-text-muted">
                      Evidence summary
                    </p>
                    <p className="mt-2 text-sm leading-6 text-text-primary">
                      {finding.evidence_summary}
                    </p>
                  </section>

                  <section className="rounded-[20px] border border-border bg-surface-muted/60 px-4 py-4">
                    <p className="text-xs font-medium uppercase tracking-[0.12em] text-text-muted">
                      Uncertainties
                    </p>
                    <ul className="mt-3 space-y-2">
                      {finding.uncertainties.map((uncertainty) => (
                        <li
                          key={uncertainty}
                          className="text-sm leading-6 text-text-secondary"
                        >
                          {uncertainty}
                        </li>
                      ))}
                    </ul>
                  </section>
                </div>
              </div>
            </details>
          ))}
        </div>
      </section>

      <section className="space-y-4">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.12em] text-text-muted">
            Perspective Implications
          </p>
          <h2 className="mt-1 text-2xl font-semibold text-text-primary">
            Framing by perspective
          </h2>
        </div>

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {orderedPerspectiveEntries.map(([key, implications]) => (
            <article
              key={key}
              className="rounded-[22px] border border-border bg-surface px-4 py-4 shadow-sm"
            >
              <h3 className="text-sm font-semibold text-text-primary">
                {formatPerspectiveLabel(key)}
              </h3>
              <ul className="mt-3 space-y-2">
                {implications.map((implication) => (
                  <li
                    key={implication}
                    className="text-sm leading-6 text-text-secondary"
                  >
                    {implication}
                  </li>
                ))}
              </ul>
            </article>
          ))}
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-[0.95fr,1.05fr]">
        <article className="rounded-[24px] border border-border bg-surface px-5 py-5 shadow-sm">
          <p className="text-xs font-medium uppercase tracking-[0.12em] text-text-muted">
            Run council on a point
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
                      className={
                        isSelected
                          ? "rounded-full border border-border bg-surface-muted px-3 py-1.5 text-xs font-medium text-text-primary"
                          : "rounded-full border border-border-muted px-3 py-1.5 text-xs text-text-secondary"
                      }
                    >
                      {formatPerspectiveLabel(perspective)}
                    </button>
                  );
                })}
              </div>
              <p className="text-xs text-text-secondary">
                Runtime: {settings.councilSettings.mode}, {settings.councilSettings.rounds}{" "}
                round{settings.councilSettings.rounds === 1 ? "" : "s"}, timeout{" "}
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
              <p className="text-sm font-medium text-text-primary">
                Findings in scope
              </p>
              <div className="space-y-2">
                {processingResult.findings.map((finding) => (
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

        <article className="rounded-[24px] border border-border bg-surface px-5 py-5 shadow-sm">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-xs font-medium uppercase tracking-[0.12em] text-text-muted">
                Council Note
              </p>
              <h2 className="mt-1 text-2xl font-semibold text-text-primary">
                Advisory note
              </h2>
            </div>
            {councilNote ? (
              <span className="rounded-full border border-border bg-surface-muted px-3 py-1 text-xs text-text-secondary">
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

              <div>
                <p className="text-sm font-medium text-text-primary">
                  {councilNote.question}
                </p>
              </div>

              <div className="flex flex-wrap gap-2">
                {councilNote.participants.map((participant) => (
                  <span
                    key={participant}
                    className="rounded-full border border-border-muted bg-surface-muted px-2.5 py-1 text-[11px] text-text-secondary"
                  >
                    {participant}
                  </span>
                ))}
              </div>

              <section className="rounded-[20px] border border-border bg-surface-muted/60 px-4 py-4">
                <p className="text-xs font-medium uppercase tracking-[0.12em] text-text-muted">
                  Summary
                </p>
                <p className="mt-2 text-sm leading-6 text-text-primary">
                  {councilNote.summary}
                </p>
              </section>

              <div className="grid gap-4 md:grid-cols-2">
                <section className="rounded-[20px] border border-border bg-surface-muted/60 px-4 py-4">
                  <p className="text-xs font-medium uppercase tracking-[0.12em] text-text-muted">
                    Key agreements
                  </p>
                  <ul className="mt-3 space-y-2">
                    {councilNote.key_agreements.map((item) => (
                      <li key={item} className="text-sm leading-6 text-text-primary">
                        {item}
                      </li>
                    ))}
                  </ul>
                </section>

                <section className="rounded-[20px] border border-border bg-surface-muted/60 px-4 py-4">
                  <p className="text-xs font-medium uppercase tracking-[0.12em] text-text-muted">
                    Key disagreements
                  </p>
                  <ul className="mt-3 space-y-2">
                    {councilNote.key_disagreements.map((item) => (
                      <li
                        key={item}
                        className="text-sm leading-6 text-text-secondary"
                      >
                        {item}
                      </li>
                    ))}
                  </ul>
                </section>
              </div>

              <section className="rounded-[20px] border border-border bg-surface-muted/60 px-4 py-4">
                <p className="text-xs font-medium uppercase tracking-[0.12em] text-text-muted">
                  Final recommendation
                </p>
                <p className="mt-2 text-sm leading-6 text-text-primary">
                  {councilNote.final_recommendation}
                </p>
              </section>

              <div className="space-y-2">
                <button
                  type="button"
                  onClick={() => setIsTranscriptExpanded((current) => !current)}
                  className="rounded-[16px] border border-border-muted px-3 py-2 text-sm text-text-primary"
                >
                  {isTranscriptExpanded ? "Hide full debate" : "Show full debate"}
                </button>
                {councilNote.transcript_path ? (
                  <p className="text-xs text-text-secondary">
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
                        <span className="text-xs text-text-secondary">
                          {entry.timestamp}
                        </span>
                      </div>
                      <p className="mt-2 text-sm leading-6 text-text-primary">
                        {entry.response}
                      </p>
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
