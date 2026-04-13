import type { CollectionDisplayData, CollectedItem } from "../../types/conversation";
import { useT } from "../../i18n/useT";

// ── Pie chart ─────────────────────────────────────────────────────────────────

const SLICE_COLORS = [
  "#3b82f6", // blue
  "#10b981", // emerald
  "#f59e0b", // amber
  "#8b5cf6", // violet
  "#ef4444", // red
  "#06b6d4", // cyan
  "#f97316", // orange
  "#84cc16", // lime
];

interface SliceData {
  name: string;
  count: number;
  color: string;
}

function PieChart({ slices }: { slices: SliceData[] }) {
  const total = slices.reduce((s, d) => s + d.count, 0);
  if (total === 0) return null;

  const cx = 100, cy = 100, r = 88, innerR = 52;
  let angle = -Math.PI / 2;

  const paths = slices.map((slice) => {
    const sweep = (slice.count / total) * 2 * Math.PI;
    const start = angle;
    angle += sweep;
    const end = angle;

    const x1o = cx + r * Math.cos(start), y1o = cy + r * Math.sin(start);
    const x2o = cx + r * Math.cos(end),   y2o = cy + r * Math.sin(end);
    const x1i = cx + innerR * Math.cos(end),   y1i = cy + innerR * Math.sin(end);
    const x2i = cx + innerR * Math.cos(start), y2i = cy + innerR * Math.sin(start);
    const large = sweep > Math.PI ? 1 : 0;

    const d =
      `M ${x1o} ${y1o} A ${r} ${r} 0 ${large} 1 ${x2o} ${y2o}` +
      ` L ${x1i} ${y1i} A ${innerR} ${innerR} 0 ${large} 0 ${x2i} ${y2i} Z`;

    return { ...slice, d };
  });

  return (
    <svg viewBox="0 0 200 200" className="w-44 h-44">
      {paths.map((p) => (
        <path key={p.name} d={p.d} fill={p.color} stroke="transparent" strokeWidth="1" />
      ))}
      {/* Center label */}
      <text x="100" y="96" textAnchor="middle" fill="var(--color-text-primary)" fontSize="11" fontWeight="600">
        {total}
      </text>
      <text x="100" y="110" textAnchor="middle" fill="var(--color-text-muted)" fontSize="9">
        items
      </text>
    </svg>
  );
}

// ── Article type classification ───────────────────────────────────────────────

const NEWS_DOMAINS = new Set([
  // Global wire services
  "reuters.com", "apnews.com", "afp.com",
  // US outlets
  "bloomberg.com", "nytimes.com", "washingtonpost.com", "wsj.com",
  "cnn.com", "foxnews.com", "foxbusiness.com", "msnbc.com", "nbcnews.com",
  "abcnews.go.com", "cbsnews.com", "pbs.org", "npr.org", "axios.com",
  "politico.com", "thehill.com", "time.com", "newsweek.com",
  "usatoday.com", "latimes.com", "nypost.com", "chron.com",
  "vox.com", "businessinsider.com", "thedailybeast.com",
  // UK / Europe
  "bbc.com", "bbc.co.uk", "theguardian.com", "independent.co.uk",
  "thetimes.com", "telegraph.co.uk", "ft.com", "sky.com",
  "dailymail.co.uk", "euractiv.com", "euobserver.com", "rte.ie",
  "dw.com", "france24.com", "lemonde.fr", "lefigaro.fr",
  "spiegel.de", "dn.no", "vg.no", "aftenposten.no", "dagbladet.no",
  "svt.se", "thelocal.se", "yle.fi", "helsinkitimes.fi",
  // Asia / Pacific
  "scmp.com", "straitstimes.com", "channelnewsasia.com",
  "thehindu.com", "ndtv.com", "hindustantimes.com", "dawn.com",
  "abc.net.au", "smh.com.au",
  // Middle East / Africa
  "aljazeera.com", "iranintl.com", "haaretz.com", "timesofisrael.com",
  "middleeasteye.net", "arabnews.com",
  // Russia / Eastern Europe / China (state/independent)
  "kyivpost.com", "kyivindependent.com", "meduza.io",
  "globaltimes.cn", "xinhuanet.com", "tass.com",
  // Other
  "moderndiplomacy.eu", "defenseone.com", "defensenews.com",
  "militarytimes.com", "breakingdefense.com", "janes.com",
]);

const ANALYSIS_DOMAINS = new Set([
  // Major think tanks
  "chathamhouse.org", "csis.org", "rand.org", "brookings.edu", "cfr.org",
  "atlanticcouncil.org", "carnegieendowment.org", "iiss.org", "rusi.org",
  "stimson.org", "wilsoncenter.org", "sipri.org", "ecfr.eu",
  "gmfus.org", "lowyinstitute.org", "auspi.org",
  // Security & defence
  "foreignaffairs.com", "foreignpolicy.com", "thediplomat.com",
  "warontherocks.com", "lawfaremedia.org", "justsecurity.org",
  "c4isrnet.com", "fpri.org", "sldinfo.com",
  // Cyber & threat intel
  "bellingcat.com", "recordedfuture.com", "crowdstrike.com",
  "mandiant.com", "secureworks.com", "unit42.paloaltonetworks.com",
  "krebsonsecurity.com", "therecord.media", "cyberscoop.com",
  "darkreading.com", "securityweek.com",
  // Policy & area studies
  "hstoday.us", "orfonline.org", "isdglobal.org",
  "energypolicy.columbia.edu", "crisisgroup.org", "pacforum.org",
  "instituteofgeoeconomics.org", "nextcenturyfoundation.org",
  "heritage.org", "aei.org", "fdd.org", "defenddemocracy.org",
  "thebulletin.org", "nsi.org",
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
  return title.replace(/\s*[|–—]\s*[^|–—]+$/, "").replace(/\s+-\s+[^-]+$/, "").trim();
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

function groupBySource(items: CollectedItem[]): Record<string, CollectedItem[]> {
  const groups: Record<string, CollectedItem[]> = {};
  for (const item of items) {
    const name = TOOL_DISPLAY_NAMES[item.source] ?? item.source;
    if (!groups[name]) groups[name] = [];
    groups[name].push(item);
  }
  return groups;
}

// ── Content parsers ───────────────────────────────────────────────────────────

/** Render KB markdown content as formatted HTML-like JSX. */
function KbContent({ content }: { content: string }) {
  if (!content.trim()) return <span className="text-text-muted text-xs italic">(no content)</span>;

  const lines = content.split("\n");
  const elements: React.ReactNode[] = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    if (/^### /.test(line)) {
      elements.push(
        <h4 key={i} className="text-xs font-bold text-text-primary mt-3 mb-1">
          {line.slice(4)}
        </h4>
      );
    } else if (/^## /.test(line)) {
      elements.push(
        <h3 key={i} className="text-sm font-bold text-text-primary mt-3 mb-1">
          {line.slice(3)}
        </h3>
      );
    } else if (/^# /.test(line)) {
      elements.push(
        <h2 key={i} className="text-sm font-semibold text-text-primary mt-3 mb-1 border-b border-border pb-1">
          {line.slice(2)}
        </h2>
      );
    } else if (/^[-*] /.test(line)) {
      elements.push(
        <li key={i} className="ml-4 text-xs text-text-secondary list-disc">
          <InlineMarkdown text={line.slice(2)} />
        </li>
      );
    } else if (/^\d+\. /.test(line)) {
      elements.push(
        <li key={i} className="ml-4 text-xs text-text-secondary list-decimal">
          <InlineMarkdown text={line.replace(/^\d+\. /, "")} />
        </li>
      );
    } else if (line.trim() === "") {
      elements.push(<div key={i} className="h-1" />);
    } else {
      elements.push(
        <p key={i} className="text-xs text-text-secondary">
          <InlineMarkdown text={line} />
        </p>
      );
    }
    i++;
  }

  return <div className="space-y-0.5">{elements}</div>;
}

function InlineMarkdown({ text }: { text: string }) {
  // Handle **bold** and *italic*
  const parts = text.split(/(\*\*[^*]+\*\*|\*[^*]+\*)/g);
  return (
    <>
      {parts.map((part, i) => {
        if (/^\*\*[^*]+\*\*$/.test(part)) {
          return <strong key={i} className="font-semibold text-text-primary">{part.slice(2, -2)}</strong>;
        }
        if (/^\*[^*]+\*$/.test(part)) {
          return <em key={i}>{part.slice(1, -1)}</em>;
        }
        return <span key={i}>{part}</span>;
      })}
    </>
  );
}

interface OtxPulse {
  // present on both search results and detail-enriched pulses
  pulse_name?: string;
  name?: string;          // from _fetch_pulse_details (richer source)
  adversary?: string;
  tags?: string[];
  targeted_countries?: string[];
  malware_families?: string[];
  attack_ids?: string[];
  description?: string;
  created?: string;
  modified?: string;
  indicator_count?: number;
  references?: string[];
}

/** Extract a flat array of pulses from the query_otx JSON response.
 *
 * The tool returns:
 *   { search_term, total_results, enriched_pulses: [...], additional_pulses: [...] }
 * or for indicator lookups:
 *   { search_term, indicator_type, results: [...], total_results }
 * or legacy: a flat array.
 */
function extractOtxPulses(parsed: unknown): OtxPulse[] {
  if (Array.isArray(parsed)) return parsed as OtxPulse[];
  if (parsed && typeof parsed === "object") {
    const obj = parsed as Record<string, unknown>;
    // Keyword search response
    const enriched = obj["enriched_pulses"];
    const additional = obj["additional_pulses"];
    if (Array.isArray(enriched)) {
      return [
        ...(enriched as OtxPulse[]),
        ...(Array.isArray(additional) ? (additional as OtxPulse[]) : []),
      ];
    }
    // Indicator search response
    const results = obj["results"];
    if (Array.isArray(results)) return results as OtxPulse[];
  }
  return [];
}

/** Try to render OTX content as structured pulse cards, fall back to raw text. */
function OtxContent({ content }: { content: string }) {
  if (!content.trim()) return <span className="text-text-muted text-xs italic">(no content)</span>;

  let parsed: unknown = null;
  try {
    parsed = JSON.parse(content);
  } catch {
    // not JSON — show raw text
  }

  if (!parsed) {
    return <pre className="text-xs text-text-secondary whitespace-pre-wrap break-all">{content}</pre>;
  }

  const pulses = extractOtxPulses(parsed);
  if (pulses.length === 0) {
    // Parsed fine but unexpected shape — show raw
    return <pre className="text-xs text-text-secondary whitespace-pre-wrap break-all">{content}</pre>;
  }

  return (
    <div className="space-y-3">
      {pulses.map((pulse, i) => {
        const title = pulse.name || pulse.pulse_name;
        return (
          <div key={i} className="rounded border border-border bg-surface-muted p-3 space-y-2">
            {title && (
              <p className="text-xs font-semibold text-text-primary">{title}</p>
            )}
            {pulse.description && (
              <p className="text-xs text-text-secondary">{pulse.description}</p>
            )}
            <div className="flex flex-wrap gap-x-6 gap-y-1">
              {pulse.adversary && (
                <span className="text-xs text-text-muted">
                  <span className="font-medium text-text-secondary">Adversary:</span> {pulse.adversary}
                </span>
              )}
              {pulse.indicator_count !== undefined && (
                <span className="text-xs text-text-muted">
                  <span className="font-medium text-text-secondary">Indicators:</span> {pulse.indicator_count}
                </span>
              )}
              {pulse.created && (
                <span className="text-xs text-text-muted">
                  <span className="font-medium text-text-secondary">Created:</span>{" "}
                  {new Date(pulse.created).toLocaleDateString()}
                </span>
              )}
            </div>
            {pulse.tags && pulse.tags.length > 0 && (
              <div className="flex flex-wrap gap-1">
                {pulse.tags.slice(0, 12).map((tag) => (
                  <span key={tag} className="rounded bg-surface-elevated px-1.5 py-0.5 text-[10px] text-text-muted">
                    {tag}
                  </span>
                ))}
                {pulse.tags.length > 12 && (
                  <span className="text-[10px] text-text-muted">+{pulse.tags.length - 12} more</span>
                )}
              </div>
            )}
            {pulse.targeted_countries && pulse.targeted_countries.length > 0 && (
              <p className="text-xs text-text-muted">
                <span className="font-medium text-text-secondary">Countries:</span>{" "}
                {pulse.targeted_countries.join(", ")}
              </p>
            )}
            {pulse.malware_families && pulse.malware_families.length > 0 && (
              <p className="text-xs text-text-muted">
                <span className="font-medium text-text-secondary">Malware:</span>{" "}
                {pulse.malware_families.join(", ")}
              </p>
            )}
            {pulse.attack_ids && pulse.attack_ids.length > 0 && (
              <p className="text-xs text-text-muted">
                <span className="font-medium text-text-secondary">ATT&CK:</span>{" "}
                {pulse.attack_ids.join(", ")}
              </p>
            )}
          </div>
        );
      })}
    </div>
  );
}

function isOtxSource(source: string) {
  return source === "query_otx";
}

function isKbSource(source: string) {
  return source === "list_knowledge_base" || source === "read_knowledge_base";
}

// ── Item renderer ─────────────────────────────────────────────────────────────

function ItemCard({ item }: { item: CollectedItem }) {
  const isOtx = isOtxSource(item.source);
  const isKb = isKbSource(item.source);
  const isFetch = item.source === "fetch_page";

  const label = isFetch && item.resource_id
    ? classifyArticle(item.resource_id, item.source) as ArticleLabel
    : item.source === "google_news_search" ? "News" as ArticleLabel
    : null;

  const displayTitle = isFetch
    ? (item.title ? cleanTitle(item.title) : item.resource_id)
    : item.resource_id;

  return (
    <div className="rounded border border-border bg-surface p-3 space-y-2">
      {item.resource_id && (
        <div className="flex flex-wrap items-center gap-1.5">
          {label && (
            <span className={`rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${LABEL_STYLES[label]}`}>
              {label}
            </span>
          )}
          {isKb ? (
            <span
              className="rounded bg-surface-muted px-1.5 py-0.5 text-[11px] font-medium text-text-muted max-w-[60ch] truncate inline-block"
              title={item.resource_id}
            >
              {displayTitle}
            </span>
          ) : (
            <a
              href={item.resource_id}
              target="_blank"
              rel="noopener noreferrer"
              className="rounded bg-primary-subtle px-1.5 py-0.5 text-[11px] font-medium text-info-text hover:underline max-w-[60ch] truncate inline-block"
              title={item.resource_id}
            >
              {displayTitle}
            </a>
          )}
        </div>
      )}
      {isOtx ? (
        <OtxContent content={item.content} />
      ) : isKb ? (
        <KbContent content={item.content} />
      ) : (
        <pre className="max-h-48 overflow-auto whitespace-pre-wrap break-all rounded border border-border-muted bg-surface-muted p-3 text-xs text-text-secondary">
          {item.content || "(no content)"}
        </pre>
      )}
    </div>
  );
}

// ── Modal ─────────────────────────────────────────────────────────────────────

interface CollectionStatsModalProps {
  isOpen: boolean;
  onClose: () => void;
  collectionData: CollectionDisplayData | null;
}

export default function CollectionStatsModal({
  isOpen,
  onClose,
  collectionData,
}: CollectionStatsModalProps) {
  const t = useT();

  if (!isOpen) return null;

  if (!collectionData)
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
        <div
          data-testid="collection-stats-modal"
          className="rounded-lg border border-border bg-surface p-8 shadow-2xl"
        >
          <p className="text-sm text-text-secondary">{t.noDataAvailable}</p>
        </div>
      </div>
    );

  const groups = groupBySource(collectionData.collected_data);
  const totalItems = collectionData.source_summary.reduce((sum, s) => sum + s.count, 0);

  const slices: SliceData[] = collectionData.source_summary
    .filter((s) => s.count > 0)
    .map((s, i) => ({
      name: s.display_name,
      count: s.count,
      color: SLICE_COLORS[i % SLICE_COLORS.length],
    }));

  return (
    <div
      data-testid="modal-backdrop"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"
      onClick={onClose}
    >
      <div
        data-testid="collection-stats-modal"
        role="dialog"
        aria-modal="true"
        className="flex h-[95vh] w-[95vw] max-w-7xl flex-col overflow-hidden rounded-xl border border-border bg-surface shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* ── Header ── */}
        <div className="flex shrink-0 items-center justify-between border-b border-border px-8 py-4">
          <div>
            <h2 className="text-base font-semibold text-text-primary">{t.collectionResultsHeader}</h2>
            <p className="mt-0.5 text-xs text-text-muted">
              {t.itemsAcrossSources(totalItems, collectionData.source_summary.length)}
            </p>
          </div>
          <button
            aria-label="close"
            onClick={onClose}
            className="rounded p-1.5 text-text-muted hover:bg-surface-elevated hover:text-text-primary transition-colors"
          >
            ✕
          </button>
        </div>

        {/* ── Body: two-column layout ── */}
        <div className="flex flex-1 overflow-hidden">
          {/* Left panel — pie chart + legend */}
          <div className="flex w-72 shrink-0 flex-col gap-6 border-r border-border overflow-y-auto px-6 py-6">
            <div>
              <p className="mb-4 text-[11px] font-semibold uppercase tracking-widest text-text-muted">
                {t.sourceDistribution}
              </p>
              <div className="flex justify-center">
                <PieChart slices={slices} />
              </div>
            </div>

            {/* Legend */}
            <div className="space-y-2">
              {slices.map((slice) => (
                <div key={slice.name} className="flex items-center gap-2.5">
                  <span
                    className="h-3 w-3 shrink-0 rounded-sm"
                    style={{ backgroundColor: slice.color }}
                  />
                  <span className="flex-1 truncate text-xs text-text-secondary">{slice.name}</span>
                  <span className="tabular-nums text-xs font-medium text-text-primary">{slice.count}</span>
                </div>
              ))}
              {collectionData.source_summary
                .filter((s) => !s.has_content)
                .map((s) => (
                  <div key={s.display_name} className="flex items-center gap-2.5 opacity-50">
                    <span className="h-3 w-3 shrink-0 rounded-sm bg-border" />
                    <span className="flex-1 truncate text-xs text-text-muted">{s.display_name}</span>
                    <span className="text-[10px] uppercase tracking-wide text-text-muted">{t.empty}</span>
                  </div>
                ))}
            </div>
          </div>

          {/* Right panel — collected data by source */}
          <div className="flex-1 overflow-y-auto px-8 py-6 space-y-4">
            <p className="text-[11px] font-semibold uppercase tracking-widest text-text-muted">
              {t.rawCollectedData}
            </p>
            <div className="rounded-lg border border-border overflow-hidden divide-y divide-border">
              {Object.entries(groups).map(([groupName, items]) => (
                <details key={groupName} open className="group">
                  <summary className="flex cursor-pointer select-none items-center justify-between px-5 py-3 bg-surface-muted hover:bg-surface-elevated transition-colors list-none">
                    <span className="text-sm font-medium text-text-primary">{groupName}</span>
                    <div className="flex items-center gap-3">
                      <span className="text-xs text-text-muted">{t.itemCount(items.length)}</span>
                      <svg
                        className="h-4 w-4 text-text-muted transition-transform group-open:rotate-180"
                        viewBox="0 0 16 16"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="1.5"
                      >
                        <path d="M4 6l4 4 4-4" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    </div>
                  </summary>
                  <div className="divide-y divide-border-muted px-5 py-4 space-y-3">
                    {items.map((item, i) => (
                      <div key={i} className={i > 0 ? "pt-3" : ""}>
                        <ItemCard item={item} />
                      </div>
                    ))}
                  </div>
                </details>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
