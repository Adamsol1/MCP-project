import { Document, Page, Text, View, StyleSheet } from "@react-pdf/renderer";
import type { AnalysisResponse } from "../../types/analysis";

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
    marginBottom: 10,
    lineHeight: 1.3,
  },
  summary: {
    fontSize: 10.5,
    marginBottom: 24,
    lineHeight: 1.7,
    color: "#444444",
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
  findingBlock: {
    marginBottom: 14,
    paddingBottom: 14,
    borderBottomWidth: 0.5,
    borderBottomColor: "#e5e5e5",
  },
  findingTitle: {
    fontSize: 10.5,
    fontFamily: "Helvetica-Bold",
    marginBottom: 3,
  },
  findingMeta: {
    fontSize: 9,
    color: "#888888",
    marginBottom: 5,
  },
  findingText: {
    lineHeight: 1.6,
    marginBottom: 4,
  },
  findingLabel: {
    fontSize: 9,
    fontFamily: "Helvetica-Bold",
    color: "#555555",
    marginTop: 5,
    marginBottom: 2,
  },
  assertionItem: {
    marginBottom: 5,
    flexDirection: "row",
    gap: 6,
  },
  assertionBullet: {
    minWidth: 10,
    color: "#555555",
  },
  assertionText: {
    flex: 1,
    lineHeight: 1.6,
  },
});

function formatPerspectiveLabel(key: string): string {
  if (key === "neutral") return "Global";
  if (key === "us" || key === "eu") return key.toUpperCase();
  return key.charAt(0).toUpperCase() + key.slice(1);
}

interface Props {
  data: AnalysisResponse;
  title: string;
}

export default function AnalysisReportPDF({ data, title }: Props) {
  const { analysis_draft: analysis, processing_result: processingResult } = data;
  const findings = processingResult.findings;

  const perspectiveEntries = Object.keys(analysis.per_perspective_implications)
    .sort((a, b) => a.localeCompare(b))
    .map((key) => [key, analysis.per_perspective_implications[key]] as const)
    .filter(([, assertions]) => assertions.length > 0);

  return (
    <Document>
      <Page size="A4" style={styles.page}>

        {/* Title & Summary */}
        <Text style={styles.title}>{title}</Text>
        <Text style={styles.summary}>{analysis.summary}</Text>

        {/* Key Judgments */}
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

        {/* Recommended Actions */}
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

        {/* Information Gaps */}
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

        {/* Perspective Implications */}
        {perspectiveEntries.length > 0 && (
          <View>
            <Text style={styles.sectionHeading}>Perspective Implications</Text>
            {perspectiveEntries.map(([key, assertions]) => (
              <View key={key}>
                <Text style={styles.subHeading}>{formatPerspectiveLabel(key)}</Text>
                {assertions.map((a, i) => (
                  <View key={i} style={styles.assertionItem}>
                    <Text style={styles.assertionBullet}>•</Text>
                    <Text style={styles.assertionText}>{a.assertion}</Text>
                  </View>
                ))}
              </View>
            ))}
          </View>
        )}

        {/* Evidence Docket */}
        {findings.length > 0 && (
          <View>
            <Text style={styles.sectionHeading}>Evidence Docket</Text>
            {findings.map((finding) => (
              <View key={finding.id} style={styles.findingBlock}>
                <Text style={styles.findingTitle}>{finding.id} — {finding.title}</Text>
                <Text style={styles.findingMeta}>
                  Source: {finding.source.replace(/_/g, " ")}  |  Confidence: {finding.confidence}%
                </Text>
                <Text style={styles.findingText}>{finding.finding}</Text>
                {finding.why_it_matters && (
                  <>
                    <Text style={styles.findingLabel}>Why it matters</Text>
                    <Text style={styles.findingText}>{finding.why_it_matters}</Text>
                  </>
                )}
                {finding.uncertainties.length > 0 && (
                  <>
                    <Text style={styles.findingLabel}>Uncertainties</Text>
                    {finding.uncertainties.map((u, i) => (
                      <View key={i} style={styles.listItem}>
                        <Text style={styles.listBullet}>•</Text>
                        <Text style={styles.listText}>{u}</Text>
                      </View>
                    ))}
                  </>
                )}
              </View>
            ))}
          </View>
        )}

      </Page>
    </Document>
  );
}
