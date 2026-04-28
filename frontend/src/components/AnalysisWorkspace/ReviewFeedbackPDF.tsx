import { Document, Page, Text, View, StyleSheet } from "@react-pdf/renderer";
import type { PhaseReviewItem } from "../../types/conversation";
import type { AnalysisResponse, CouncilNote } from "../../types/analysis";

const styles = StyleSheet.create({
  page: {
    fontFamily: "Helvetica",
    fontSize: 10,
    paddingTop: 48,
    paddingBottom: 48,
    paddingHorizontal: 56,
    color: "#1a1a1a",
    lineHeight: 1.5,
  },
  reportTitle: {
    fontSize: 22,
    fontFamily: "Helvetica-Bold",
    marginBottom: 6,
    lineHeight: 1.3,
  },
  reportSubtitle: {
    fontSize: 10.5,
    color: "#666666",
    marginBottom: 28,
  },
  majorSectionTitle: {
    fontSize: 14,
    fontFamily: "Helvetica-Bold",
    marginBottom: 6,
    marginTop: 32,
    paddingBottom: 6,
    borderBottomWidth: 1,
    borderBottomColor: "#333333",
  },
  sectionHeading: {
    fontSize: 11,
    fontFamily: "Helvetica-Bold",
    textTransform: "uppercase",
    letterSpacing: 1.2,
    color: "#666666",
    marginBottom: 8,
    marginTop: 24,
    borderBottomWidth: 0.5,
    borderBottomColor: "#cccccc",
    paddingBottom: 4,
  },
  subHeading: {
    fontSize: 10.5,
    fontFamily: "Helvetica-Bold",
    marginBottom: 4,
    marginTop: 14,
  },
  bodyText: {
    lineHeight: 1.7,
    marginBottom: 6,
  },
  listItem: {
    flexDirection: "row",
    marginBottom: 6,
    gap: 6,
  },
  listIndex: {
    minWidth: 16,
    fontFamily: "Helvetica-Bold",
    color: "#555555",
  },
  listBullet: {
    minWidth: 10,
    color: "#555555",
  },
  listText: {
    flex: 1,
    lineHeight: 1.6,
  },
  attemptBlock: {
    marginBottom: 14,
    paddingBottom: 14,
    borderBottomWidth: 0.5,
    borderBottomColor: "#e5e5e5",
  },
  attemptHeader: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    marginBottom: 6,
  },
  attemptLabel: {
    fontSize: 10,
    fontFamily: "Helvetica-Bold",
    color: "#333333",
  },
  statusApproved: {
    fontSize: 9,
    color: "#2d7a4f",
    fontFamily: "Helvetica-Bold",
  },
  statusRejected: {
    fontSize: 9,
    color: "#b84040",
    fontFamily: "Helvetica-Bold",
  },
  suggestionsLabel: {
    fontSize: 9,
    fontFamily: "Helvetica-Bold",
    color: "#555555",
    marginBottom: 3,
  },
  suggestionsText: {
    fontSize: 10,
    lineHeight: 1.6,
    color: "#444444",
  },
  noSuggestions: {
    fontSize: 10,
    color: "#999999",
    fontStyle: "italic",
  },
  sourcesLabel: {
    fontSize: 9,
    fontFamily: "Helvetica-Bold",
    color: "#555555",
    marginTop: 6,
    marginBottom: 2,
  },
  sourcesText: {
    fontSize: 9,
    color: "#666666",
  },
  emptyPhase: {
    fontSize: 10,
    color: "#999999",
    fontStyle: "italic",
  },
  meta: {
    fontSize: 9,
    color: "#888888",
    marginBottom: 8,
  },
  voteBlock: {
    marginTop: 6,
    paddingTop: 6,
    borderTopWidth: 0.5,
    borderTopColor: "#e5e5e5",
  },
  voteLabel: {
    fontSize: 9,
    fontFamily: "Helvetica-Bold",
    color: "#555555",
    marginBottom: 2,
  },
});

function stripMarkdown(value: string): string {
  return value.replace(/\*\*(.*?)\*\*/g, "$1").trim();
}

function splitVoteFromResponse(response: string) {
  const voteIndex = response.lastIndexOf("VOTE:");
  if (voteIndex === -1) return { body: response.trim(), voteOption: null, voteRationale: null, voteConfidence: null };
  const body = response.slice(0, voteIndex).trim();
  const voteCandidate = response.slice(voteIndex + "VOTE:".length).trim();
  try {
    const parsed = JSON.parse(voteCandidate) as { option?: string; confidence?: number; rationale?: string };
    return {
      body,
      voteOption: parsed.option?.trim() || null,
      voteRationale: parsed.rationale?.trim() || null,
      voteConfidence: typeof parsed.confidence === "number" ? parsed.confidence : null,
    };
  } catch {
    return { body: response.trim(), voteOption: null, voteRationale: null, voteConfidence: null };
  }
}

function formatPerspectiveLabel(key: string): string {
  if (key === "neutral") return "Global";
  if (key === "us" || key === "eu") return key.toUpperCase();
  return key.charAt(0).toUpperCase() + key.slice(1);
}

const PHASE_LABELS: Record<PhaseReviewItem["phase"], string> = {
  direction: "Direction",
  collection: "Collection",
  processing: "Processing",
  analysis: "Analysis",
};

const PHASES: PhaseReviewItem["phase"][] = ["direction", "collection", "processing", "analysis"];

interface Props {
  reviewActivity: PhaseReviewItem[];
  reportTitle: string;
  analysisData: AnalysisResponse;
  councilNote?: CouncilNote | null;
}

export default function ReviewFeedbackPDF({ reviewActivity, reportTitle, analysisData, councilNote }: Props) {
  const { analysis_draft: analysis } = analysisData;

  const byPhase = (phase: PhaseReviewItem["phase"]) =>
    reviewActivity.filter((item) => item.phase === phase).sort((a, b) => a.attempt - b.attempt);

  const perspectiveEntries = Object.keys(analysis.per_perspective_implications)
    .sort((a, b) => a.localeCompare(b))
    .map((key) => [key, analysis.per_perspective_implications[key]] as const)
    .filter(([, assertions]) => assertions.length > 0);

  const hasDisagreements =
    councilNote &&
    councilNote.key_disagreements.length > 0 &&
    !(councilNote.key_disagreements.length === 1 &&
      councilNote.key_disagreements[0].toLowerCase() === "none");

  return (
    <Document>
      <Page size="A4" style={styles.page}>

        {/* Document header */}
        <Text style={styles.reportTitle}>Intelligence Assessment Report</Text>
        <Text style={styles.reportSubtitle}>{reportTitle}</Text>

        {/* ── SECTION 1: Analysis ───────────────────────────────── */}
        <Text style={styles.majorSectionTitle}>Analysis</Text>

        <Text style={styles.bodyText}>{analysis.summary}</Text>

        {analysis.key_judgments.length > 0 && (
          <View>
            <Text style={styles.sectionHeading}>Key Judgments</Text>
            {analysis.key_judgments.map((judgment, i) => (
              <View key={i} style={styles.listItem}>
                <Text style={styles.listIndex}>{i + 1}.</Text>
                <Text style={styles.listText}>{judgment}</Text>
              </View>
            ))}
          </View>
        )}

        {analysis.recommended_actions.length > 0 && (
          <View>
            <Text style={styles.sectionHeading}>Recommended Actions</Text>
            {analysis.recommended_actions.map((action, i) => (
              <View key={i} style={styles.listItem}>
                <Text style={styles.listBullet}>•</Text>
                <Text style={styles.listText}>{action}</Text>
              </View>
            ))}
          </View>
        )}

        {analysis.information_gaps.length > 0 && (
          <View>
            <Text style={styles.sectionHeading}>Information Gaps</Text>
            {analysis.information_gaps.map((gap, i) => (
              <View key={i} style={styles.listItem}>
                <Text style={styles.listBullet}>•</Text>
                <Text style={styles.listText}>{gap}</Text>
              </View>
            ))}
          </View>
        )}

        {perspectiveEntries.length > 0 && (
          <View>
            <Text style={styles.sectionHeading}>Perspective Implications</Text>
            {perspectiveEntries.map(([key, assertions]) => (
              <View key={key}>
                <Text style={styles.subHeading}>{formatPerspectiveLabel(key)}</Text>
                {assertions.map((a, i) => (
                  <View key={i} style={styles.listItem}>
                    <Text style={styles.listBullet}>•</Text>
                    <Text style={styles.listText}>{a.assertion}</Text>
                  </View>
                ))}
              </View>
            ))}
          </View>
        )}

        {/* ── SECTION 2: Review Feedback ────────────────────────── */}
        <Text style={styles.majorSectionTitle}>Review Feedback</Text>

        {PHASES.map((phase) => {
          const items = byPhase(phase);
          return (
            <View key={phase}>
              <Text style={styles.sectionHeading}>{PHASE_LABELS[phase]}</Text>
              {items.length === 0 ? (
                <Text style={styles.emptyPhase}>No review attempts recorded.</Text>
              ) : (
                items.map((item) => (
                  <View key={item.attempt} style={styles.attemptBlock}>
                    <View style={styles.attemptHeader}>
                      <Text style={styles.attemptLabel}>Attempt {item.attempt}</Text>
                      <Text style={item.reviewer_approved ? styles.statusApproved : styles.statusRejected}>
                        {item.reviewer_approved ? "APPROVED" : "REJECTED"}
                      </Text>
                    </View>

                    {item.reviewer_suggestions ? (
                      <>
                        <Text style={styles.suggestionsLabel}>Reviewer Suggestions</Text>
                        <Text style={styles.suggestionsText}>{item.reviewer_suggestions}</Text>
                      </>
                    ) : (
                      <Text style={styles.noSuggestions}>No suggestions provided.</Text>
                    )}

                    {phase === "collection" && item.sources_used.length > 0 && (
                      <>
                        <Text style={styles.sourcesLabel}>Sources Used</Text>
                        <Text style={styles.sourcesText}>{item.sources_used.join(", ")}</Text>
                      </>
                    )}
                  </View>
                ))
              )}
            </View>
          );
        })}

        {/* ── SECTION 3: Council Advisory Note (optional) ───────── */}
        {councilNote && (
          <View>
            <Text style={styles.majorSectionTitle}>Council Advisory Note</Text>
            <Text style={styles.meta}>
              {councilNote.rounds_completed} round{councilNote.rounds_completed !== 1 ? "s" : ""}  ·  {councilNote.participants.length} participants
            </Text>
            <Text style={styles.bodyText}>{stripMarkdown(councilNote.question)}</Text>

            <Text style={styles.sectionHeading}>Summary</Text>
            <Text style={styles.bodyText}>{stripMarkdown(councilNote.summary)}</Text>

            {councilNote.key_agreements.length > 0 && (
              <View>
                <Text style={styles.sectionHeading}>Key Agreements</Text>
                {councilNote.key_agreements.map((item, i) => (
                  <View key={i} style={styles.listItem}>
                    <Text style={styles.listBullet}>•</Text>
                    <Text style={styles.listText}>{stripMarkdown(item)}</Text>
                  </View>
                ))}
              </View>
            )}

            {hasDisagreements && (
              <View>
                <Text style={styles.sectionHeading}>Key Disagreements</Text>
                {councilNote.key_disagreements.map((item, i) => (
                  <View key={i} style={styles.listItem}>
                    <Text style={styles.listBullet}>•</Text>
                    <Text style={styles.listText}>{stripMarkdown(item)}</Text>
                  </View>
                ))}
              </View>
            )}

            <Text style={styles.sectionHeading}>Final Recommendation</Text>
            <Text style={styles.bodyText}>{stripMarkdown(councilNote.final_recommendation)}</Text>

            <Text style={styles.sectionHeading}>Participant Positions</Text>
            {councilNote.participants.map((participant) => {
              const entries = councilNote.full_debate.filter((e) => e.participant === participant);
              const lastEntry = entries.at(-1);
              if (!lastEntry) return null;
              const { body, voteOption, voteRationale, voteConfidence } = splitVoteFromResponse(lastEntry.response);
              return (
                <View key={participant}>
                  <Text style={styles.subHeading}>{participant}</Text>
                  <Text style={styles.bodyText}>{stripMarkdown(body)}</Text>
                  {voteOption && (
                    <View style={styles.voteBlock}>
                      <Text style={styles.voteLabel}>
                        Vote: {voteOption}{voteConfidence !== null ? `  (${Math.round(voteConfidence * 100)}% confidence)` : ""}
                      </Text>
                      {voteRationale && <Text style={styles.bodyText}>{voteRationale}</Text>}
                    </View>
                  )}
                </View>
              );
            })}
          </View>
        )}

      </Page>
    </Document>
  );
}
