import { Document, Page, Text, View, StyleSheet } from "@react-pdf/renderer";
import type { PhaseReviewItem } from "../../types/conversation";

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
  title: {
    fontSize: 22,
    fontFamily: "Helvetica-Bold",
    marginBottom: 6,
    lineHeight: 1.3,
  },
  subtitle: {
    fontSize: 10.5,
    color: "#666666",
    marginBottom: 28,
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
});

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
}

export default function ReviewFeedbackPDF({ reviewActivity, reportTitle }: Props) {
  const byPhase = (phase: PhaseReviewItem["phase"]) =>
    reviewActivity.filter((item) => item.phase === phase).sort((a, b) => a.attempt - b.attempt);

  return (
    <Document>
      <Page size="A4" style={styles.page}>
        <Text style={styles.title}>Review Feedback Report</Text>
        <Text style={styles.subtitle}>{reportTitle}</Text>

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
      </Page>
    </Document>
  );
}
