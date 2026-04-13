import type { Translations } from "./en";

export const no = {
  // Sidebar
  toggleSidebar: "Veksle sidefelt",
  newChat: "Ny chat",
  newConversationDefault: "Ny samtale",
  noConversations: "Ingen samtaler enn\u00e5",
  chatOptions: "Chatalternativer",
  rename: "Gi nytt navn",
  delete: "Slett",
  openSettings: "\u00c5pne innstillinger",
  devTools: "Utviklerverkt\u00f8y",
  show: "Vis",
  hide: "Skjul",
  expandDevTools: "Utvid utviklerverkt\u00f8y",
  minimizeDevTools: "Minimer utviklerverkt\u00f8y",
  sendTestMessage: "Send testmelding",
  showCollectionApproval: "Vis innsamlingsgodkjenning",
  directionPhase: "Retningsfase",
  expandDirectionPhase: "Utvid retningsfase",
  minimizeDirectionPhase: "Minimer retningsfase",
  jumpToInitial: "Hopp til start",
  jumpToGathering: "Hopp til innsamling",
  jumpToSummary: "Hopp til oppsummering",
  jumpToPir: "Hopp til PIR",
  jumpToComplete: "Hopp til ferdig",
  syncStage: "Synkroniser fase",
  resetStage: "Tilbakestill fase",
  deleteAllConversations: "Slett alle samtaler",

  // ChatWindow
  readyToStart: "Klar til \u00e5 begynne?",
  sendMessage: "Send melding",
  placeholderDefault: "Skriv hva som helst...",
  placeholderPlanModify:
    "Beskriv endringene du \u00f8nsker i innsamlingsplanen...",
  placeholderSummaryModify:
    "Beskriv hvordan du vil endre innsamlingsoppsummeringen...",
  placeholderGatherMore: "Beskriv hva du vil samle mer informasjon om...",
  pirHeader: "Prioriterte etterretningskrav (PIRer)",
  rationale: "Begrunnelse",
  showReasoning: "Vis resonnement",
  collectionPlanHeader: "Innsamlingsplan",
  suggestedSources: "Foresl\u00e5tte kilder",
  suggestedSourcesHeader: "Foresl\u00e5tte kilder",
  noSourceSuggestions: "Ingen kildeforslag ble returnert.",
  collectionSummaryHeader: "Innsamlingsoppsummering",
  sourcesUsed: "Brukte kilder",
  gaps: "Mangler",
  noGapsIdentified: "Ingen mangler identifisert.",
  collectionReviewHeader: "Innsamlingsgjennomgang",
  collectionReviewSubtitle:
    "Godta de innsamlede dataene eller samle inn mer fra andre kilder.",
  accept: "Godta",
  collectMoreData: "Samle inn mer data",
  collectionResultsHeader: "Innsamlingsresultater",
  couldNotParseCollection: "Kunne ikke tolke innsamlingsresultater.",
  rawOutput: "R\u00e5data",
  selectSourcesHeader: "Velg kilder",
  selectSourcesSubtitle:
    "Velg \u00e9n eller flere datakilder f\u00f8r innsamlingen starter.",
  noSourceSuggestionsAvailable: "Ingen tilgjengelige kildeforslag.",
  startCollecting: "Start innsamling",
  sourceNames: {
    "AlienVault OTX": "AlienVault OTX",
    "Internal Knowledge Bank": "Intern kunnskapsbank",
    "Uploaded Documents": "Opplastede dokumenter",
    "Web Search": "Nettsøk",
  } as Record<string, string>,
  sourceDescriptions: {
    "AlienVault OTX": "Åpne trusselinnmatinger",
    "Internal Knowledge Bank": "Organisasjonens kuraterte intel",
    "Uploaded Documents": "PDF-er, rapporter, o.l.",
    "Web Search": "Søker på nettet etter relevant informasjon",
  } as Record<string, string>,
  collecting: "Samler inn",
  startingCollection: "Starter innsamling\u2026",
  tableSource: "Kilde",
  tableItems: "Elementer",
  tableResources: "Ressurser",
  tableStatus: "Status",
  dataFound: "Data funnet",
  empty: "Tom",
  priorityHigh: "H\u00f8y",
  priorityMedium: "Middels",
  priorityLow: "Lav",
  resultSingular: "resultat",
  resultPlural: "resultater",

  // PerspectiveSelector
  perspective: "Perspektiv",
  perspectiveLabels: {
    NEUTRAL: "N\u00f8ytral",
    CHINA: "Kina",
    EU: "EU",
    NORWAY: "Norge",
    RUSSIA: "Russland",
    US: "USA",
  } as Record<string, string>,

  // PirSourcesView
  noSourcesAvailable: "Ingen kilder tilgjengelig.",
  pirSources: (n: number) => `Kilder (${n})`,

  // CollectionStatsView
  statsSources: "Kilder",
  bySource: "Kilder:",
  viewRawData: "Se r\u00e5data \u2192",
  noCollectionData: "Ingen innsamlingsdata",

  // CollectionStatsModal
  sourceDistribution: "Kildedistribusjon",
  rawCollectedData: "R\u00e5innsamlede data",
  itemsAcrossSources: (items: number, sources: number) =>
    `${items} elementer fra ${sources} kilder`,
  itemCount: (n: number) => `${n} element${n !== 1 ? "er" : ""}`,
  noDataAvailable: "Ingen data tilgjengelig",
  noContent: "(ingen innhold)",

  // IntelligencePanel
  intelligenceWorkspace: "Etterretningsarbeidsrom",
  processingArtifacts: "Behandlingsartefakter vil vises her.",
  analysisOutputs: "Analyseresultater vil vises her.",
  files: "Filer",
  uploadFiles: "Last opp filer",
  showLess: "Vis f\u00e6rre",
  showMore: (n: number) => `Vis ${n} til`,
  removeFile: (name: string) => `Fjern ${name}`,
  phaseLabels: {
    direction: "RETNING",
    collection: "INNSAMLING",
    processing: "BEHANDLING",
    analysis: "ANALYSE",
  } as Record<string, string>,

  // SettingsModal
  settingsOptions: "Alternativer",
  navLabels: {
    appearance: "utseende",
    parameters: "AI-parametere",
    council: "r\u00e5d",
  } as Record<string, string>,
  closeSettings: "Lukk innstillinger",
  uiLanguage: "Spr\u00e5k",
  uiLanguageDesc: "Spr\u00e5ket som brukes i grensesnittet.",
  aiOutputLanguage: "AI-utdataspr\u00e5k",
  aiOutputLanguageDesc: "Spr\u00e5ket som AI vil bruke i sine svar.",
  langEnglish: "Engelsk",
  langNorwegian: "Norsk",
  themeLabel: "Tema",
  themeDesc: "Velg mellom lyst og m\u00f8rkt grensesnitt.",
  themeLabels: {
    light: "lyst",
    dark: "m\u00f8rkt",
  } as Record<string, string>,
  timeframeLabel: "Tidsramme",
  timeframeDesc:
    "Fylles automatisk inn i hver foresp\u00f8rsel slik at AI vet den relevante perioden.",
  timeframePlaceholder: "f.eks. Siste 30 dager",

  // ApprovalPrompt
  approvalDefault: "Klar til \u00e5 fortsette?",
  approvalDefaultSubtitle:
    "Gjennomg\u00e5 resultatet ovenfor f\u00f8r du fortsetter.",
  approvalSummary: "Stemmer dette med din intensjon?",
  approvalSummarySubtitle:
    "Godkjenn for \u00e5 generere prioriterte etterretningskrav, eller avvis for \u00e5 justere oppsummeringen.",
  approvalPir: "Ser disse PIR-ene riktige ut?",
  approvalPirSubtitle:
    "Godkjenn for \u00e5 g\u00e5 til innsamlingsplanlegging, eller avvis for \u00e5 justere kravene.",
  approvalPlan: "Klar til \u00e5 starte innsamling?",
  approvalPlanSubtitle:
    "Godkjenn for \u00e5 velge kilder og starte innsamling, eller avvis for \u00e5 justere planen.",
  approveContinue: "Godkjenn og fortsett",
  rejectWithFeedback: "Avvis med tilbakemelding",
} satisfies Translations;
