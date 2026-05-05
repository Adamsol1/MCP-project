import { Document, Page, Text, View, StyleSheet } from "@react-pdf/renderer";
import type { CouncilNote } from "../../types/analysis";

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
    fontSize: 20,
    fontFamily: "Helvetica-Bold",
    marginBottom: 6,
    lineHeight: 1.3,
  },
  subtitle: {
    fontSize: 10.5,
    color: "#444444",
    marginBottom: 24,
    lineHeight: 1.6,
  },
  meta: {
    fontSize: 9,
    color: "#888888",
    marginBottom: 20,
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
    marginTop: 16,
  },
  bodyText: {
    lineHeight: 1.7,
    marginBottom: 6,
  },
  listItem: {
    flexDirection: "row",
    marginBottom: 5,
    gap: 6,
  },
  listBullet: {
    minWidth: 10,
    color: "#555555",
  },
  listText: {
    flex: 1,
    lineHeight: 1.6,
  },
  roundBlock: {
    marginBottom: 16,
    paddingBottom: 16,
    borderBottomWidth: 0.5,
    borderBottomColor: "#e5e5e5",
  },
  roundHeading: {
    fontSize: 10.5,
    fontFamily: "Helvetica-Bold",
    marginBottom: 8,
  },
  entryBlock: {
    marginBottom: 10,
    paddingLeft: 10,
    borderLeftWidth: 1.5,
    borderLeftColor: "#cccccc",
  },
  entryParticipant: {
    fontSize: 9.5,
    fontFamily: "Helvetica-Bold",
    marginBottom: 2,
  },
  entryTimestamp: {
    fontSize: 8.5,
    color: "#888888",
    marginBottom: 4,
  },
  entryText: {
    lineHeight: 1.6,
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

function splitVoteFromResponse(response: string): { body: string; voteOption: string | null; voteRationale: string | null; voteConfidence: number | null } {
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

interface Props {
  councilNote: CouncilNote;
}

export default function CouncilReportPDF({ councilNote }: Props) {
  const roundsMap = councilNote.full_debate.reduce<Record<number, typeof councilNote.full_debate>>(
    (acc, entry) => {
      (acc[entry.round] ??= []).push(entry);
      return acc;
    },
    {},
  );

  const sortedRounds = Object.entries(roundsMap).sort(([a], [b]) => Number(a) - Number(b));

  const hasDisagreements =
    councilNote.key_disagreements.length > 0 &&
    !(councilNote.key_disagreements.length === 1 &&
      councilNote.key_disagreements[0].toLowerCase() === "none");

  return (
    <Document>
      <Page size="A4" style={styles.page}>

        {/* Header */}
        <Text style={styles.title}>Council Advisory Note</Text>
        <Text style={styles.meta}>
          {councilNote.rounds_completed} round{councilNote.rounds_completed !== 1 ? "s" : ""}  ·  {councilNote.participants.length} participants
        </Text>
        <Text style={styles.subtitle}>{stripMarkdown(councilNote.question)}</Text>

        {/* Summary */}
        <Text style={styles.sectionHeading}>Summary</Text>
        <Text style={styles.bodyText}>{stripMarkdown(councilNote.summary)}</Text>

        {/* Key Agreements */}
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

        {/* Key Disagreements */}
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

        {/* Final Recommendation */}
        <Text style={styles.sectionHeading}>Final Recommendation</Text>
        <Text style={styles.bodyText}>{stripMarkdown(councilNote.final_recommendation)}</Text>

        {/* Participant Positions */}
        <Text style={styles.sectionHeading}>Participant Positions</Text>
        {councilNote.participants.map((participant) => {
          const entries = councilNote.full_debate.filter((e) => e.participant === participant);
          const lastEntry = entries.at(-1);
          if (!lastEntry) return null;
          const { body, voteOption, voteRationale, voteConfidence } = splitVoteFromResponse(lastEntry.response);
          const cleanBody = stripMarkdown(body);

          return (
            <View key={participant}>
              <Text style={styles.subHeading}>{participant}</Text>
              <Text style={styles.bodyText}>{cleanBody}</Text>
              {voteOption && (
                <View style={styles.voteBlock}>
                  <Text style={styles.voteLabel}>Vote: {voteOption}{voteConfidence !== null ? `  (${Math.round(voteConfidence * 100)}% confidence)` : ""}</Text>
                  {voteRationale && <Text style={styles.bodyText}>{voteRationale}</Text>}
                </View>
              )}
            </View>
          );
        })}

        {/* Full Transcript */}
        <Text style={styles.sectionHeading}>Full Transcript</Text>
        {sortedRounds.map(([round, entries]) => (
          <View key={round} style={styles.roundBlock}>
            <Text style={styles.roundHeading}>Round {round}</Text>
            {entries.map((entry, i) => {
              const { body, voteOption, voteRationale, voteConfidence } = splitVoteFromResponse(entry.response);
              return (
                <View key={i} style={styles.entryBlock}>
                  <Text style={styles.entryParticipant}>{entry.participant}</Text>
                  {entry.timestamp ? <Text style={styles.entryTimestamp}>{entry.timestamp}</Text> : null}
                  <Text style={styles.entryText}>{stripMarkdown(body)}</Text>
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
        ))}

      </Page>
    </Document>
  );
}
