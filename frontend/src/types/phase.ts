export type Phase =
  | "direction"
  | "collection"
  | "processing"
  | "analysis";

export type PhaseStatus = "completed" | "active" | "upcoming";

export interface PhaseInfo {
  id: Phase;
  label: string;
  description: string;
}

export const PHASES: PhaseInfo[] = [
  {
    id: "direction",
    label: "Planning and Direction",
    description: "DEFINE REQUIREMENTS AND SCOPE",
  },
  {
    id: "collection",
    label: "Collection",
    description: "IDENTIFY SOURCES AND GATHER DATA",
  },
  {
    id: "processing",
    label: "Processing",
    description: "NORMALIZE, ENRICH, AND STRUCTURE DATA",
  },
  {
    id: "analysis",
    label: "Analysis",
    description: "DERIVE INSIGHTS AND PRODUCE FINDINGS",
  },
];
