import type { CollectionDisplayData, CollectedItem } from "../../types/conversation";

// ── Article type classification ──────────────────────────────────────────────

const NEWS_DOMAINS = new Set([
  "reuters.com", "bloomberg.com", "bbc.com", "bbc.co.uk", "nytimes.com",
  "theguardian.com", "washingtonpost.com", "apnews.com", "cnn.com",
  "aljazeera.com", "cbsnews.com", "pbs.org", "foxbusiness.com", "rte.ie",
  "time.com", "thehill.com", "wsj.com", "ft.com", "thetimes.com",
  "independent.co.uk", "euobserver.com", "iranintl.com", "moderndiplomacy.eu",
]);

const ANALYSIS_DOMAINS = new Set([
  "chathamhouse.org", "csis.org", "rand.org", "brookings.edu", "cfr.org",
  "atlanticcouncil.org", "carnegieendowment.org", "iiss.org", "rusi.org",
  "hstoday.us", "orfonline.org", "isdglobal.org", "fpri.org", "sldinfo.com",
  "foreignaffairs.com", "foreignpolicy.com", "thediplomat.com",
  "energypolicy.columbia.edu", "crisisgroup.org", "pacforum.org",
  "instituteofgeoeconomics.org", "nextcenturyfoundation.org",
]);

type ArticleLabel = "News" | "Analysis" | "Report" | "Official" | "Article";

function classifyArticle(url: string, source: string): ArticleLabel {
  if (source === "google_news_search") return "News";
  let hostname = "";
  try { hostname = new URL(url).hostname.replace(/^www\./, ""); } catch { /* invalid url */ }

  if (NEWS_DOMAINS.has(hostname)) return "News";
  if (ANALYSIS_DOMAINS.has(hostname)) return "Analysis";
  if (/\.(gov|mil)$/.test(hostname)) return "Official";

  const path = url.toLowerCase();
  if (/\/(news|breaking|latest|article)\//.test(path)) return "News";
  if (/\/(research|report|paper|publication|brief|working-paper)\//.test(path)) return "Report";
  if (/\/(analysis|insight|commentary|opinion|perspective|dispatch)\//.test(path)) return "Analysis";

  return "Article";
}

const LABEL_STYLES: Record<ArticleLabel, string> = {
  News:     "bg-info-subtle text-info-text",
  Analysis: "bg-warning-subtle text-warning-text",
  Report:   "bg-primary-subtle text-primary",
  Official: "bg-success-subtle text-success-text",
  Article:  "bg-surface-elevated text-text-secondary",
};

// ── Helpers ───────────────────────────────────────────────────────────────────

function cleanTitle(title: string): string {
  // Strip trailing "| Publisher", "- Publisher", "— Publisher" suffixes from page <title> tags
  return title.replace(/\s*[|–—]\s*[^|–—]+$/, "").replace(/\s+-\s+[^-]+$/, "").trim();
}

function displayLabel(item: CollectedItem): string | null {
  if (!item.resource_id) return null;
  if (item.source === "fetch_page") return classifyArticle(item.resource_id, item.source);
  if (item.source === "google_news_search") return "News";
  return null;
}

const TOOL_DISPLAY_NAMES: Record<string, string> = {
  list_knowledge_base: "Internal Knowledge Bank",
  read_knowledge_base: "Internal Knowledge Bank",
  query_otx: "AlienVault OTX",
  search_local_data: "Uploaded Documents",
  list_uploads: "Uploaded Documents",
  read_upload: "Uploaded Documents",
  google_search: "Web Search",
  google_news_search: "Web News",
  fetch_page: "Web Fetch",
};

interface CollectionStatsModalProps {
  isOpen: boolean;
  onClose: () => void;
  collectionData: CollectionDisplayData | null;
}

function groupBySource(items: CollectedItem[]): Record<string, CollectedItem[]> {
  const groups: Record<string, CollectedItem[]> = {};
  for (const item of items) {
    const name = TOOL_DISPLAY_NAMES[item.source] ?? item.source;
    if (!groups[name]) groups[name] = [];
    groups[name].push(item);
  }
  return groups;
}

export default function CollectionStatsModal({
  isOpen,
  onClose,
  collectionData,
}: CollectionStatsModalProps) {
  if (!isOpen) return null;

  if (!collectionData)
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
        <div
          data-testid="collection-stats-modal"
          className="rounded-lg border border-border bg-surface p-8 shadow-2xl"
        >
          <p className="text-sm text-text-secondary">No data available</p>
        </div>
      </div>
    );

  const groups = groupBySource(collectionData.collected_data);
  const totalItems = collectionData.source_summary.reduce((sum, s) => sum + s.count, 0);
  const maxCount = Math.max(...collectionData.source_summary.map((s) => s.count), 1);

  return (
    <div
      data-testid="modal-backdrop"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
      onClick={onClose}
    >
      <div
        data-testid="collection-stats-modal"
        role="dialog"
        aria-modal="true"
        className="flex h-[85vh] w-225 max-w-[95vw] flex-col overflow-hidden rounded-lg border border-border bg-surface shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* ── Header ── */}
        <div className="flex items-center justify-between border-b border-border px-16 py-4">
          <div>
            <h2 className="text-base font-semibold text-text-primary">Collection Results</h2>
            <p className="mt-0.5 text-xs text-text-muted">
              {totalItems} items across {collectionData.source_summary.length} sources
            </p>
          </div>
          <button
            aria-label="close"
            onClick={onClose}
            className="text-text-muted hover:text-text-primary transition-colors"
          >
            ✕
          </button>
        </div>

        {/* ── Scrollable body ── */}
        <div className="flex-1 overflow-y-auto px-16 py-5 space-y-6">

          {/* Stats section */}
          <section>
            <p className="mb-3 text-[11px] font-semibold uppercase tracking-widest text-text-muted">
              Source Distribution
            </p>
            <div className="space-y-2">
              {collectionData.source_summary.map((source) => (
                <div key={source.display_name} className="flex items-center gap-3">
                  <span className="w-44 shrink-0 text-xs text-text-secondary truncate">
                    {source.display_name}
                  </span>
                  <div className="flex-1 h-2 rounded-full bg-surface-elevated overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all ${
                        source.has_content ? "bg-primary" : "bg-border"
                      }`}
                      style={{ width: `${(source.count / maxCount) * 100}%` }}
                    />
                  </div>
                  <span className="w-8 text-right text-xs font-medium tabular-nums text-text-secondary">
                    {source.count}
                  </span>
                  {!source.has_content && (
                    <span className="text-[10px] uppercase tracking-wide text-text-muted">
                      Empty
                    </span>
                  )}
                </div>
              ))}
            </div>
          </section>

          {/* Raw data section */}
          <section>
            <p className="mb-3 text-[11px] font-semibold uppercase tracking-widest text-text-muted">
              Raw Collected Data
            </p>
            <div className="rounded-lg border border-border overflow-hidden divide-y divide-border">
              {Object.entries(groups).map(([groupName, items]) => (
                <details
                  key={groupName}
                  role="group"
                  open
                  className="group"
                >
                  <summary className="flex cursor-pointer select-none items-center justify-between px-4 py-2.5 bg-surface-muted border-b border-border-muted text-sm font-medium text-text-secondary hover:text-text-primary list-none">
                    {groupName}
                    <span className="text-xs text-text-muted">{items.length} items</span>
                  </summary>
                  <div className="divide-y divide-border-muted">
                    {items.map((item, i) => {
                      const label = displayLabel(item) as ArticleLabel | null;
                      const displayTitle = item.source === "fetch_page"
                        ? (item.title ? cleanTitle(item.title) : item.resource_id)
                        : item.resource_id;
                      return (
                        <div key={i} className="px-4 py-3">
                          {item.resource_id && (
                            <div className="mb-1.5 flex flex-wrap items-center gap-1.5">
                              {label && (
                                <span className={`rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${LABEL_STYLES[label]}`}>
                                  {label}
                                </span>
                              )}
                              <a
                                href={item.resource_id}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="rounded bg-primary-subtle px-1.5 py-0.5 text-[11px] font-medium text-info-text hover:underline max-w-[60ch] truncate inline-block"
                                title={item.resource_id}
                              >
                                {displayTitle}
                              </a>
                            </div>
                          )}
                          <pre className="mt-1 max-h-36 overflow-auto whitespace-pre-wrap break-all rounded border border-border-muted bg-surface-muted p-3 text-xs text-text-secondary">
                            {item.content || "(no content)"}
                          </pre>
                        </div>
                      );
                    })}
                  </div>
                </details>
              ))}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
