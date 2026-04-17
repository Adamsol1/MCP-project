export const en = {
  // Sidebar
  toggleSidebar: "Toggle sidebar",
  newChat: "New Chat",
  newConversationDefault: "New conversation",
  noConversations: "No conversations yet",
  chatOptions: "Chat options",
  rename: "Rename",
  delete: "Delete",
  openSettings: "Open settings",
  devTools: "Dev Tools",
  show: "Show",
  hide: "Hide",
  expandDevTools: "Expand dev tools",
  minimizeDevTools: "Minimize dev tools",
  sendTestMessage: "Send test message",
  showCollectionApproval: "Show collection approval",
  previousRun: "Previous run",
  refresh: "Refresh",
  loading: "Loading...",
  noPreviousRuns: "No previous runs found",
  loadPir: "PIR",
  loadCollection: "Collection",
  loadProcessing: "Processing",
  loadAnalysis: "Analysis",
  deleteAllConversations: "Delete all conversations",

  // ChatWindow
  readyToStart: "Ready to start?",
  sendMessage: "Send message",
  placeholderDefault: "Type anything...",
  placeholderPlanModify:
    "Describe the changes you want in the collection plan...",
  placeholderSummaryModify: "Describe how to modify the collection summary...",
  placeholderGatherMore: "Describe what to gather more information about...",
  pirHeader: "Priority Intelligence Requirements (PIRs)",
  rationale: "Rationale",
  showReasoning: "Show reasoning",
  collectionPlanHeader: "Collection Plan",
  suggestedSources: "Suggested sources",
  suggestedSourcesHeader: "Suggested Sources",
  noSourceSuggestions: "No source suggestions were returned.",
  collectionSummaryHeader: "Collection Summary",
  sourcesUsed: "Sources used",
  gaps: "Gaps",
  noGapsIdentified: "No gaps identified.",
  collectionReviewHeader: "Collection Review",
  collectionReviewSubtitle:
    "Accept the collected data or collect more from additional sources.",
  accept: "Accept",
  collectMoreData: "Collect More Data",
  collectionResultsHeader: "Collection Results",
  couldNotParseCollection: "Could not parse collection output.",
  rawOutput: "Raw output",
  selectSourcesHeader: "Select Sources",
  selectSourcesSubtitle:
    "Choose one or more data sources before collection starts.",
  noSourceSuggestionsAvailable: "No source suggestions available.",
  startCollecting: "Start Collecting",
  sourceNames: {
    "AlienVault OTX": "AlienVault OTX",
    "Knowledge Bank": "Knowledge Bank",
    "Uploaded Documents": "Uploaded Documents",
    "Web Search": "Web Search",
  } as Record<string, string>,
  sourceDescriptions: {
    "AlienVault OTX": "Open threat exchange feeds",
    "Knowledge Bank": "Your org's curated intel",
    "Uploaded Documents": "PDFs, reports, etc.",
    "Web Search": "Searching the web for relevant information",
  } as Record<string, string>,
  collecting: "Collecting",
  startingCollection: "Starting collection\u2026",
  tableSource: "Source",
  tableItems: "Items",
  tableResources: "Resources",
  tableStatus: "Status",
  dataFound: "Data found",
  empty: "Empty",
  priority: "Priority",
  priorityHigh: "High",
  priorityMedium: "Medium",
  priorityLow: "Low",
  resultSingular: "result",
  resultPlural: "results",

  // PerspectiveSelector
  perspective: "Perspective",
  perspectiveLabels: {
    NEUTRAL: "Global",
    CHINA: "China",
    EU: "EU",
    NORWAY: "Norway",
    RUSSIA: "Russia",
    US: "US",
  } as Record<string, string>,

  // PirSourcesView
  noSourcesAvailable: "No sources available.",
  pirSources: (n: number) => `Sources (${n})`,

  // CollectionStatsView
  statsSources: "Sources",
  bySource: "By Source",
  viewRawData: "View Raw Data \u2192",
  noCollectionData: "No collection data",

  // CollectionStatsModal
  sourceDistribution: "Source Distribution",
  rawCollectedData: "Raw Collected Data",
  itemsAcrossSources: (items: number, sources: number) =>
    `${items} items across ${sources} sources`,
  itemCount: (n: number) => `${n} item${n !== 1 ? "s" : ""}`,
  noDataAvailable: "No data available",
  noContent: "(no content)",

  // IntelligencePanel
  intelligenceWorkspace: "Intelligence Workspace",
  processingArtifacts: "Processing artifacts will appear here.",
  analysisOutputs: "Analysis outputs will appear here.",
  files: "Files",
  uploadFiles: "Upload Files",
  showLess: "Show less",
  showMore: (n: number) => `Show ${n} more`,
  removeFile: (name: string) => `Remove ${name}`,
  phaseLabels: {
    direction: "DIRECTION",
    collection: "COLLECTION",
    processing: "PROCESSING",
    analysis: "ANALYSIS",
    council: "COUNCIL",
  } as Record<string, string>,

  // SettingsModal
  settingsOptions: "Options",
  navLabels: {
    appearance: "appearance",
    parameters: "AI parameters",
    council: "council",
  } as Record<string, string>,
  closeSettings: "Close settings",
  uiLanguage: "Language",
  uiLanguageDesc: "The language used throughout the interface.",
  aiOutputLanguage: "AI Output Language",
  aiOutputLanguageDesc: "The language the AI will use in its responses.",
  langEnglish: "English",
  langNorwegian: "Norwegian",
  themeLabel: "Theme",
  themeDesc: "Choose between light and dark interface.",
  themeLabels: {
    light: "light",
    dark: "dark",
  } as Record<string, string>,
  timeframeLabel: "Timeframe",
  timeframeDesc:
    "Auto-filled into each prompt so the AI knows the relevant period.",
  timeframePlaceholder: "e.g. Last 30 days",

  // ApprovalPrompt
  approvalDefault: "Ready to continue?",
  approvalDefaultSubtitle: "Review the output above before continuing.",
  approvalSummary: "Does this capture your intent?",
  approvalSummarySubtitle:
    "Approve to generate your Priority Intelligence Requirements, or reject to refine the summary.",
  approvalPir: "Do these PIRs look correct?",
  approvalPirSubtitle: "Approve to move to collection planning, or reject to adjust the requirements.",
  approvalPlan: "Ready to start collection?",
  approvalPlanSubtitle:
    "Approve to select sources and begin collecting intelligence, or reject to adjust the plan.",
  approveContinue: "Approve \u0026 Continue",
  rejectWithFeedback: "Reject with Feedback",
};

export type Translations = typeof en;
