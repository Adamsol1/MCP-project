import { useEffect, useState } from "react";
import type {
  CollectionDisplayData,
  CollectedItem,
} from "../../types/conversation";
import type { UploadedFileRecord } from "../../services/upload/upload";
import { useT } from "../../i18n/useT";

// ── Colors & abbreviations ────────────────────────────────────────────────────

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

/** Short labels shown in the pie chart leader lines. Shown alongside full names in the legend. */
const SOURCE_ABBR: Record<string, string> = {
  // Top-level sources
  "Knowledge Bank": "K.B.",
  "Web Fetch": "Web",
  "Web News": "News",
  "Web Search": "Srch",
  "AlienVault OTX": "OTX",
  "Uploaded Documents": "F.U.",
  // Article-type sub-slices (expanded from web sources) — full names
  News: "News",
  Analysis: "Analysis",
  Report: "Report",
  Official: "Official",
  Article: "Article",
};

// ── Pie chart ─────────────────────────────────────────────────────────────────

interface SliceData {
  name: string;
  count: number;
  color: string;
}

function PieChart({ slices }: { slices: SliceData[] }) {
  const [hovered, setHovered] = useState<string | null>(null);
  const total = slices.reduce((s, d) => s + d.count, 0);
  if (total === 0) return null;

  const cx = 200,
    cy = 135,
    r = 92,
    innerR = 54;

  // Single slice: SVG arc degenerates for a full 360°, use circles instead
  if (slices.length === 1) {
    const slice = slices[0];
    const isHov = hovered === slice.name;
    const abbr = SOURCE_ABBR[slice.name] ?? slice.name.slice(0, 5);
    return (
      <svg viewBox="0 0 400 270" className="w-full">
        <g
          onMouseEnter={() => setHovered(slice.name)}
          onMouseLeave={() => setHovered(null)}
          style={{ cursor: "pointer" }}
        >
          <circle
            cx={cx}
            cy={cy}
            r={r}
            fill={slice.color}
            style={{
              filter: isHov ? "brightness(1.12)" : "brightness(1)",
              transition: "filter 0.15s ease",
            }}
          />
          <circle cx={cx} cy={cy} r={innerR} fill="var(--color-surface)" />
        </g>
        <text
          x={cx}
          y={cy - 9}
          textAnchor="middle"
          dominantBaseline="middle"
          fill="var(--color-text-primary)"
          fontSize="17"
          fontWeight="600"
        >
          {total}
        </text>
        <text
          x={cx}
          y={cy + 9}
          textAnchor="middle"
          dominantBaseline="middle"
          fill="var(--color-text-muted)"
          fontSize="11"
        >
          items
        </text>
        {/* Leader line going right */}
        <polyline
          points={`${cx + r + 5},${cy} ${cx + r + 22},${cy} ${cx + r + 40},${cy}`}
          fill="none"
          stroke={slice.color}
          strokeWidth="1"
        />
        <circle cx={cx + r + 40} cy={cy} r="2" fill={slice.color} />
        <text
          x={cx + r + 45}
          y={cy - 4}
          fontSize="32"
          fontWeight="600"
          fill="var(--color-text-secondary)"
        >
          {abbr}
        </text>
        <text
          x={cx + r + 45}
          y={cy + 10}
          fontSize="11"
          fill="var(--color-text-muted)"
        >
          {total} item{total !== 1 ? "s" : ""}
        </text>
      </svg>
    );
  }

  // Multi-slice
  let angle = -Math.PI / 2;

  const computed = slices.map((slice) => {
    const sweep = (slice.count / total) * 2 * Math.PI;
    const start = angle;
    angle += sweep;
    const end = angle;
    const mid = (start + end) / 2;
    const cos_m = Math.cos(mid);
    const sin_m = Math.sin(mid);

    const x1o = cx + r * Math.cos(start),
      y1o = cy + r * Math.sin(start);
    const x2o = cx + r * Math.cos(end),
      y2o = cy + r * Math.sin(end);
    const x1i = cx + innerR * Math.cos(end),
      y1i = cy + innerR * Math.sin(end);
    const x2i = cx + innerR * Math.cos(start),
      y2i = cy + innerR * Math.sin(start);
    const large = sweep > Math.PI ? 1 : 0;

    const d =
      `M ${x1o} ${y1o} A ${r} ${r} 0 ${large} 1 ${x2o} ${y2o}` +
      ` L ${x1i} ${y1i} A ${innerR} ${innerR} 0 ${large} 0 ${x2i} ${y2i} Z`;

    // Direction to push slice on hover
    const hoverDx = 8 * cos_m;
    const hoverDy = 8 * sin_m;

    // Leader line: start just past outer edge → bend outward → horizontal to label
    const lx1 = cx + (r + 5) * cos_m,
      ly1 = cy + (r + 5) * sin_m;
    const lx2 = cx + (r + 18) * cos_m,
      ly2 = cy + (r + 18) * sin_m;
    const goRight = cos_m >= 0;
    const lx3 = lx2 + (goRight ? 16 : -16),
      ly3 = ly2;
    const textAnchor = goRight ? "start" : "end";
    const textX = lx3 + (goRight ? 4 : -4);
    const abbr = SOURCE_ABBR[slice.name] ?? slice.name;

    return {
      ...slice,
      d,
      hoverDx,
      hoverDy,
      lx1,
      ly1,
      lx2,
      ly2,
      lx3,
      ly3,
      textAnchor,
      textX,
      textY: ly3,
      abbr,
    };
  });

  return (
    <svg viewBox="0 0 400 270" className="w-full">
      {/* Leader lines — rendered behind slices */}
      {computed.map((p) => {
        const isHov = hovered === p.name;
        return (
          <g
            key={`leader-${p.name}`}
            style={{
              opacity: hovered && !isHov ? 0.25 : 1,
              transition: "opacity 0.15s ease",
            }}
          >
            <polyline
              points={`${p.lx1},${p.ly1} ${p.lx2},${p.ly2} ${p.lx3},${p.ly3}`}
              fill="none"
              stroke={p.color}
              strokeWidth="1"
            />
            <circle cx={p.lx3} cy={p.ly3} r="2" fill={p.color} />
            <text
              x={p.textX}
              y={p.textY - 3}
              textAnchor={p.textAnchor as "start" | "end"}
              fontSize="14"
              fontWeight="600"
              fill="var(--color-text-secondary)"
            >
              {p.abbr}
            </text>
            <text
              x={p.textX}
              y={p.textY + 11}
              textAnchor={p.textAnchor as "start" | "end"}
              fontSize="11"
              fill="var(--color-text-muted)"
            >
              {p.count} item{p.count !== 1 ? "s" : ""}
            </text>
          </g>
        );
      })}

      {/* Slices */}
      {computed.map((p) => {
        const isHov = hovered === p.name;
        return (
          <path
            key={p.name}
            d={p.d}
            fill={p.color}
            stroke="transparent"
            strokeWidth="1"
            style={{
              cursor: "pointer",
              transform: isHov
                ? `translate(${p.hoverDx}px, ${p.hoverDy}px)`
                : "translate(0,0)",
              transition: "transform 0.15s ease, filter 0.15s ease",
              filter: isHov ? "brightness(1.12)" : "brightness(1)",
            }}
            onMouseEnter={() => setHovered(p.name)}
            onMouseLeave={() => setHovered(null)}
          />
        );
      })}

      {/* Center label */}
      <text
        x={cx}
        y={cy - 9}
        textAnchor="middle"
        dominantBaseline="middle"
        fill="var(--color-text-primary)"
        fontSize="20"
        fontWeight="600"
      >
        {total}
      </text>
      <text
        x={cx}
        y={cy + 9}
        textAnchor="middle"
        dominantBaseline="middle"
        fill="var(--color-text-muted)"
        fontSize="11"
      >
        items
      </text>
    </svg>
  );
}

// ── Article type classification ───────────────────────────────────────────────

const NEWS_DOMAINS = new Set([
  // Global wire services
  "reuters.com",
  "apnews.com",
  "afp.com",
  // US outlets
  "bloomberg.com",
  "nytimes.com",
  "washingtonpost.com",
  "wsj.com",
  "cnn.com",
  "foxnews.com",
  "foxbusiness.com",
  "msnbc.com",
  "nbcnews.com",
  "abcnews.go.com",
  "cbsnews.com",
  "pbs.org",
  "npr.org",
  "axios.com",
  "politico.com",
  "thehill.com",
  "time.com",
  "newsweek.com",
  "usatoday.com",
  "latimes.com",
  "nypost.com",
  "chron.com",
  "vox.com",
  "businessinsider.com",
  "thedailybeast.com",
  // UK / Europe
  "bbc.com",
  "bbc.co.uk",
  "theguardian.com",
  "independent.co.uk",
  "thetimes.com",
  "telegraph.co.uk",
  "ft.com",
  "sky.com",
  "dailymail.co.uk",
  "euractiv.com",
  "euobserver.com",
  "rte.ie",
  "dw.com",
  "france24.com",
  "lemonde.fr",
  "lefigaro.fr",
  "spiegel.de",
  "dn.no",
  "vg.no",
  "aftenposten.no",
  "dagbladet.no",
  "svt.se",
  "thelocal.se",
  "yle.fi",
  "helsinkitimes.fi",
  // Asia / Pacific
  "scmp.com",
  "straitstimes.com",
  "channelnewsasia.com",
  "thehindu.com",
  "ndtv.com",
  "hindustantimes.com",
  "dawn.com",
  "abc.net.au",
  "smh.com.au",
  // Middle East / Africa
  "aljazeera.com",
  "iranintl.com",
  "haaretz.com",
  "timesofisrael.com",
  "middleeasteye.net",
  "arabnews.com",
  // Russia / Eastern Europe / China (state/independent)
  "kyivpost.com",
  "kyivindependent.com",
  "meduza.io",
  "globaltimes.cn",
  "xinhuanet.com",
  "tass.com",
  // Other
  "moderndiplomacy.eu",
  "defenseone.com",
  "defensenews.com",
  "militarytimes.com",
  "breakingdefense.com",
  "janes.com",
]);

const ANALYSIS_DOMAINS = new Set([
  // Major think tanks
  "chathamhouse.org",
  "csis.org",
  "rand.org",
  "brookings.edu",
  "cfr.org",
  "atlanticcouncil.org",
  "carnegieendowment.org",
  "iiss.org",
  "rusi.org",
  "stimson.org",
  "wilsoncenter.org",
  "sipri.org",
  "ecfr.eu",
  "gmfus.org",
  "lowyinstitute.org",
  "auspi.org",
  // Security & defence
  "foreignaffairs.com",
  "foreignpolicy.com",
  "thediplomat.com",
  "warontherocks.com",
  "lawfaremedia.org",
  "justsecurity.org",
  "c4isrnet.com",
  "fpri.org",
  "sldinfo.com",
  // Cyber & threat intel
  "bellingcat.com",
  "recordedfuture.com",
  "crowdstrike.com",
  "mandiant.com",
  "secureworks.com",
  "unit42.paloaltonetworks.com",
  "krebsonsecurity.com",
  "therecord.media",
  "cyberscoop.com",
  "darkreading.com",
  "securityweek.com",
  // Policy & area studies
  "hstoday.us",
  "orfonline.org",
  "isdglobal.org",
  "energypolicy.columbia.edu",
  "crisisgroup.org",
  "pacforum.org",
  "instituteofgeoeconomics.org",
  "nextcenturyfoundation.org",
  "heritage.org",
  "aei.org",
  "fdd.org",
  "defenddemocracy.org",
  "thebulletin.org",
  "nsi.org",
]);

type ArticleLabel = "News" | "Analysis" | "Report" | "Official" | "Article";

function classifyArticle(url: string, source: string): ArticleLabel {
  if (source === "google_news_search") return "News";
  let hostname = "";
  try {
    hostname = new URL(url).hostname.replace(/^www\./, "");
  } catch {
    /* invalid url */
  }
  if (NEWS_DOMAINS.has(hostname)) return "News";
  if (ANALYSIS_DOMAINS.has(hostname)) return "Analysis";
  if (/\.(gov|mil)$/.test(hostname)) return "Official";
  const path = url.toLowerCase();
  if (/\/(news|breaking|latest|article)\//.test(path)) return "News";
  if (/\/(research|report|paper|publication|brief|working-paper)\//.test(path))
    return "Report";
  if (
    /\/(analysis|insight|commentary|opinion|perspective|dispatch)\//.test(path)
  )
    return "Analysis";
  return "Article";
}

const LABEL_STYLES: Record<ArticleLabel, string> = {
  News: "bg-info-subtle text-info-text",
  Analysis: "bg-warning-subtle text-warning-text",
  Report: "bg-primary-subtle text-primary",
  Official: "bg-success-subtle text-success-text",
  Article: "bg-surface-elevated text-text-secondary",
};

/** Hex colors for article-type pie slices — visually aligned with LABEL_STYLES badges */
const ARTICLE_TYPE_COLORS: Record<ArticleLabel, string> = {
  News: "#3b82f6", // blue   — info
  Analysis: "#f59e0b", // amber  — warning
  Report: "#8b5cf6", // violet — primary
  Official: "#10b981", // emerald — success
  Article: "#94a3b8", // slate  — muted fallback
};

// ── Helpers ───────────────────────────────────────────────────────────────────

function cleanTitle(title: string): string {
  return title
    .replace(/\s*[|–—]\s*[^|–—]+$/, "")
    .replace(/\s+-\s+[^-]+$/, "")
    .trim();
}

const TOOL_DISPLAY_NAMES: Record<string, string> = {
  knowledge_base: "Knowledge Bank",
  list_knowledge_base: "Knowledge Bank",
  read_knowledge_base: "Knowledge Bank",
  query_otx: "AlienVault OTX",
  search_local_data: "Uploaded Documents",
  list_uploads: "Uploaded Documents",
  read_upload: "Uploaded Documents",
  google_search: "Web Search",
  google_news_search: "Web News",
  fetch_page: "Web Fetch",
};

function groupBySource(
  items: CollectedItem[],
): Record<string, CollectedItem[]> {
  const groups: Record<string, CollectedItem[]> = {};
  for (const item of items) {
    const name = TOOL_DISPLAY_NAMES[item.source] ?? item.source;
    if (!groups[name]) groups[name] = [];
    groups[name].push(item);
  }
  return groups;
}

// ── Source type guards ────────────────────────────────────────────────────────

function isOtxSource(source: string) {
  return source === "query_otx";
}

function isKbSource(source: string) {
  return source === "list_knowledge_base" || source === "read_knowledge_base";
}

function isWebSource(source: string) {
  return (
    source === "fetch_page" ||
    source === "google_news_search" ||
    source === "google_search"
  );
}

function isUploadSource(source: string) {
  return (
    source === "read_upload" ||
    source === "search_local_data" ||
    source === "list_uploads"
  );
}

/** Display-name groups that contain web-fetched content and should be sub-grouped by article type */
const WEB_GROUP_NAMES = new Set(["Web Fetch", "Web News", "Web Search"]);

function groupWebByType(
  items: CollectedItem[],
): [ArticleLabel, CollectedItem[]][] {
  const ORDER: ArticleLabel[] = [
    "News",
    "Analysis",
    "Report",
    "Official",
    "Article",
  ];
  const map = new Map<ArticleLabel, CollectedItem[]>();
  for (const item of items) {
    const label: ArticleLabel = item.resource_id
      ? classifyArticle(item.resource_id, item.source)
      : "Article";
    if (!map.has(label)) map.set(label, []);
    map.get(label)!.push(item);
  }
  return ORDER.filter((l) => map.has(l)).map((l) => [l, map.get(l)!]);
}

/**
 * Build the pie slice list.
 * Non-web sources get one slice each. Web sources are expanded into per-article-type slices
 * so the chart shows News / Analysis / Article / etc. rather than a single "Web Fetch" wedge.
 */
function buildSlices(collectionData: CollectionDisplayData): SliceData[] {
  const result: SliceData[] = [];
  let nonWebColorIdx = 0;

  // 1. Non-web sources — one slice each with the generic palette
  for (const source of collectionData.source_summary) {
    // Normalise legacy name sent by older backend sessions
    const displayName =
      source.display_name === "Internal Knowledge Bank"
        ? "Knowledge Bank"
        : source.display_name;
    if (source.count > 0 && !WEB_GROUP_NAMES.has(displayName)) {
      result.push({
        name: displayName,
        count: source.count,
        color: SLICE_COLORS[nonWebColorIdx++ % SLICE_COLORS.length],
      });
    }
  }

  // 2. Web sources — expand into article-type slices
  const webItems = collectionData.collected_data.filter((item) =>
    WEB_GROUP_NAMES.has(TOOL_DISPLAY_NAMES[item.source] ?? ""),
  );
  if (webItems.length > 0) {
    for (const [type, items] of groupWebByType(webItems)) {
      result.push({
        name: type,
        count: items.length,
        color: ARTICLE_TYPE_COLORS[type],
      });
    }
  }

  return result;
}

// ── Content parsers ───────────────────────────────────────────────────────────

/** Render markdown-ish content as formatted JSX (used for KB and web items). */
function KbContent({ content }: { content: string }) {
  if (!content.trim())
    return <span className="text-text-muted text-xs italic">(no content)</span>;

  const lines = content.split("\n");
  const elements: React.ReactNode[] = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    // [Title in brackets] → render as a heading (common in web-fetched articles)
    if (/^\[.+\]$/.test(line.trim())) {
      elements.push(
        <h2
          key={i}
          className="text-sm font-semibold text-text-primary mb-2 border-b border-border pb-1"
        >
          {line.trim().slice(1, -1)}
        </h2>,
      );
    } else if (/^### /.test(line)) {
      elements.push(
        <h4 key={i} className="text-sm font-bold text-text-primary mt-3 mb-1">
          {line.slice(4)}
        </h4>,
      );
    } else if (/^## /.test(line)) {
      elements.push(
        <h3 key={i} className="text-base font-bold text-text-primary mt-3 mb-1">
          {line.slice(3)}
        </h3>,
      );
    } else if (/^# /.test(line)) {
      elements.push(
        <h2
          key={i}
          className="text-base font-semibold text-text-primary mt-3 mb-1 border-b border-border pb-1"
        >
          {line.slice(2)}
        </h2>,
      );
    } else if (/^[-*] /.test(line)) {
      elements.push(
        <li key={i} className="ml-4 text-sm text-text-secondary list-disc">
          <InlineMarkdown text={line.slice(2)} />
        </li>,
      );
    } else if (/^\d+\. /.test(line)) {
      elements.push(
        <li key={i} className="ml-4 text-sm text-text-secondary list-decimal">
          <InlineMarkdown text={line.replace(/^\d+\. /, "")} />
        </li>,
      );
    } else if (line.trim() === "") {
      elements.push(<div key={i} className="h-1" />);
    } else {
      elements.push(
        <p key={i} className="text-sm text-text-secondary">
          <InlineMarkdown text={line} />
        </p>,
      );
    }
    i++;
  }

  return <div className="space-y-0.5">{elements}</div>;
}

function InlineMarkdown({ text }: { text: string }) {
  const parts = text.split(/(\*\*[^*]+\*\*|\*[^*]+\*|<i>[^<]*<\/i>|<em>[^<]*<\/em>|<b>[^<]*<\/b>|<strong>[^<]*<\/strong>)/g);
  return (
    <>
      {parts.map((part, i) => {
        if (/^\*\*[^*]+\*\*$/.test(part)) {
          return (
            <strong key={i} className="font-semibold text-text-primary">
              {part.slice(2, -2)}
            </strong>
          );
        }
        if (/^\*[^*]+\*$/.test(part)) {
          return <em key={i}>{part.slice(1, -1)}</em>;
        }
        if (/^<i>[^<]*<\/i>$/.test(part) || /^<em>[^<]*<\/em>$/.test(part)) {
          const inner = part.replace(/^<(?:i|em)>/, "").replace(/<\/(?:i|em)>$/, "");
          return <em key={i}>{inner}</em>;
        }
        if (/^<b>[^<]*<\/b>$/.test(part) || /^<strong>[^<]*<\/strong>$/.test(part)) {
          const inner = part.replace(/^<(?:b|strong)>/, "").replace(/<\/(?:b|strong)>$/, "");
          return <strong key={i} className="font-semibold text-text-primary">{inner}</strong>;
        }
        return <span key={i}>{part}</span>;
      })}
    </>
  );
}

interface OtxPulse {
  pulse_name?: string;
  name?: string;
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

function extractOtxPulses(parsed: unknown): OtxPulse[] {
  if (Array.isArray(parsed)) return parsed as OtxPulse[];
  if (parsed && typeof parsed === "object") {
    const obj = parsed as Record<string, unknown>;
    const enriched = obj["enriched_pulses"];
    const additional = obj["additional_pulses"];
    if (Array.isArray(enriched)) {
      return [
        ...(enriched as OtxPulse[]),
        ...(Array.isArray(additional) ? (additional as OtxPulse[]) : []),
      ];
    }
    const results = obj["results"];
    if (Array.isArray(results)) return results as OtxPulse[];
  }
  return [];
}

function OtxContent({ content }: { content: string }) {
  if (!content.trim())
    return <span className="text-text-muted text-xs italic">(no content)</span>;

  let parsed: unknown = null;
  try {
    parsed = JSON.parse(content);
  } catch {
    /* not JSON */
  }

  if (!parsed) {
    return (
      <pre className="text-xs text-text-secondary whitespace-pre-wrap break-all">
        {content}
      </pre>
    );
  }

  const pulses = extractOtxPulses(parsed);
  if (pulses.length === 0) {
    return (
      <pre className="text-xs text-text-secondary whitespace-pre-wrap break-all">
        {content}
      </pre>
    );
  }

  return (
    <div className="space-y-3">
      {pulses.map((pulse, i) => {
        const title = pulse.name || pulse.pulse_name;
        return (
          <div
            key={i}
            className="rounded border border-border bg-surface-muted p-3 space-y-2"
          >
            {title && (
              <p className="text-xs font-semibold text-text-primary">{title}</p>
            )}
            {pulse.description && (
              <p className="text-xs text-text-secondary">{pulse.description}</p>
            )}
            <div className="flex flex-wrap gap-x-6 gap-y-1">
              {pulse.adversary && (
                <span className="text-xs text-text-muted">
                  <span className="font-medium text-text-secondary">
                    Adversary:
                  </span>{" "}
                  {pulse.adversary}
                </span>
              )}
              {pulse.indicator_count !== undefined && (
                <span className="text-xs text-text-muted">
                  <span className="font-medium text-text-secondary">
                    Indicators:
                  </span>{" "}
                  {pulse.indicator_count}
                </span>
              )}
              {pulse.created && (
                <span className="text-xs text-text-muted">
                  <span className="font-medium text-text-secondary">
                    Created:
                  </span>{" "}
                  {new Date(pulse.created).toLocaleDateString()}
                </span>
              )}
            </div>
            {pulse.tags && pulse.tags.length > 0 && (
              <div className="flex flex-wrap gap-1">
                {pulse.tags.slice(0, 12).map((tag) => (
                  <span
                    key={tag}
                    className="rounded bg-surface-elevated px-1.5 py-0.5 text-[10px] text-text-muted"
                  >
                    {tag}
                  </span>
                ))}
                {pulse.tags.length > 12 && (
                  <span className="text-[10px] text-text-muted">
                    +{pulse.tags.length - 12} more
                  </span>
                )}
              </div>
            )}
            {pulse.targeted_countries &&
              pulse.targeted_countries.length > 0 && (
                <p className="text-xs text-text-muted">
                  <span className="font-medium text-text-secondary">
                    Countries:
                  </span>{" "}
                  {pulse.targeted_countries.join(", ")}
                </p>
              )}
            {pulse.malware_families && pulse.malware_families.length > 0 && (
              <p className="text-xs text-text-muted">
                <span className="font-medium text-text-secondary">
                  Malware:
                </span>{" "}
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

// ── Translation ───────────────────────────────────────────────────────────────

/** Module-level cache so translations survive re-renders and aren't re-fetched. */
const translationCache = new Map<string, string>();

/**
 * Detect the ISO 639-1 language code from Unicode block ranges.
 * Returns null if the text is Latin-script (no translation needed).
 * MyMemory rejects "auto" as a source language, so explicit codes are required.
 */
function detectLangCode(text: string): string | null {
  if (/[\u0400-\u04FF]/.test(text)) return "ru";             // Cyrillic  → Russian
  if (/[\u4E00-\u9FFF\u3400-\u4DBF]/.test(text)) return "zh-CN"; // CJK  → Chinese
  if (/[\u3040-\u309F\u30A0-\u30FF]/.test(text)) return "ja"; // Kana     → Japanese
  if (/[\uAC00-\uD7AF\u1100-\u11FF]/.test(text)) return "ko"; // Hangul   → Korean
  if (/[\u0600-\u06FF]/.test(text)) return "ar";             // Arabic
  if (/[\u0900-\u097F]/.test(text)) return "hi";             // Devanagari → Hindi
  if (/[\u0E00-\u0E7F]/.test(text)) return "th";             // Thai
  return null;
}

/**
 * Fetches an English translation via the free MyMemory API with an explicit
 * source language code. Results are cached per text.
 */
function useTranslation(text: string): { translated: string | null; loading: boolean } {
  const [translated, setTranslated] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!text) return;
    const langCode = detectLangCode(text);
    if (!langCode) return; // already Latin, skip

    const cached = translationCache.get(text);
    if (cached) { setTranslated(cached); return; }

    setLoading(true);
    fetch(
      `https://api.mymemory.translated.net/get?q=${encodeURIComponent(text)}&langpair=${langCode}|en`,
    )
      .then((r) => r.json())
      .then((data) => {
        const result: string | undefined = data?.responseData?.translatedText;
        if (result && result.toLowerCase() !== text.toLowerCase()) {
          translationCache.set(text, result);
          setTranslated(result);
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [text]);

  return { translated, loading };
}

// ── Shared chevron ────────────────────────────────────────────────────────────

function Chevron({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
    >
      <path d="M4 6l4 4 4-4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

// ── Item card (collapsible) ───────────────────────────────────────────────────

function ItemCard({ item, uploadedFiles }: { item: CollectedItem; uploadedFiles?: UploadedFileRecord[] }) {
  const isOtx = isOtxSource(item.source);
  const isKb = isKbSource(item.source);
  const isWeb = isWebSource(item.source);
  const isUpload = isUploadSource(item.source);
  const isFetch = item.source === "fetch_page";

  const displayTitle: string = (() => {
    if (isFetch) {
      return item.title ? cleanTitle(item.title) : (item.resource_id ?? "(untitled)");
    }
    if (isUpload && item.resource_id && uploadedFiles) {
      const match = uploadedFiles.find((f) => f.file_upload_id === item.resource_id);
      if (match) return match.original_filename;
    }
    return item.title ?? item.resource_id ?? "(no resource)";
  })();

  // Translate non-Latin titles for web articles
  const { translated, loading } = useTranslation(isWeb ? displayTitle : "");

  return (
    <details className="group/item rounded border border-border bg-surface overflow-hidden">
      <summary className="flex cursor-pointer select-none items-center gap-2 px-3 py-2 hover:bg-surface-muted transition-colors list-none">
        <span
          className="flex-1 min-w-0 truncate text-[11px] text-text-secondary"
          title={displayTitle}
        >
          {translated ? (
            <>
              <span className="text-text-muted italic font-normal">
                Translated:{" "}
              </span>
              <span className="font-medium">{translated}</span>
            </>
          ) : loading ? (
            <span className="font-medium text-text-muted">{displayTitle}</span>
          ) : (
            <span className="font-medium">{displayTitle}</span>
          )}
        </span>
        <Chevron className="h-3.5 w-3.5 shrink-0 text-text-muted transition-transform group-open/item:rotate-180" />
      </summary>
      <div className="border-t border-border-muted px-3 pb-3 pt-2 space-y-2">
        {/* Clickable URL for non-KB web items */}
        {item.resource_id && !isKb && (
          <a
            href={item.resource_id}
            target="_blank"
            rel="noopener noreferrer"
            className="text-[10px] text-info-text hover:underline truncate block"
            title={item.resource_id}
          >
            {item.resource_id}
          </a>
        )}
        {isOtx ? (
          <OtxContent content={item.content} />
        ) : isKb || isWeb || isUpload ? (
          <KbContent content={item.content} />
        ) : (
          <pre className="max-h-48 overflow-auto whitespace-pre-wrap break-all rounded border border-border-muted bg-surface-muted p-3 text-xs text-text-secondary">
            {item.content || "(no content)"}
          </pre>
        )}
      </div>
    </details>
  );
}

// ── Modal ─────────────────────────────────────────────────────────────────────

interface CollectionStatsModalProps {
  isOpen: boolean;
  onClose: () => void;
  collectionData: CollectionDisplayData | null;
  uploadedFiles?: UploadedFileRecord[];
}

export default function CollectionStatsModal({
  isOpen,
  onClose,
  collectionData,
  uploadedFiles,
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
  const totalItems = collectionData.source_summary.reduce(
    (sum, s) => sum + s.count,
    0,
  );

  const slices = buildSlices(collectionData);

  // Separate non-web and web-type slices for the legend grouping
  const articleTypeNames = new Set<string>([
    "News",
    "Analysis",
    "Report",
    "Official",
    "Article",
  ]);
  const nonWebSlices = slices.filter((s) => !articleTypeNames.has(s.name));
  const webTypeSlices = slices.filter((s) => articleTypeNames.has(s.name));

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
            <h2 className="text-base font-semibold text-text-primary">
              {t.collectionResultsHeader}
            </h2>
            <p className="mt-0.5 text-xs text-text-muted">
              {t.itemsAcrossSources(
                totalItems,
                collectionData.source_summary.length,
              )}
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
          <div className="flex w-80 shrink-0 flex-col gap-5 border-r border-border overflow-y-auto px-5 py-6">
            <div>
              <p className="mb-3 text-[11px] font-semibold uppercase tracking-widest text-text-muted">
                {t.sourceDistribution}
              </p>
              {/* SVG chart fills panel width; leader lines are embedded inside */}
              <PieChart slices={slices} />
            </div>

            {/* Legend */}
            <div className="space-y-2">
              {/* Non-web sources */}
              {nonWebSlices.map((slice) => (
                <div key={slice.name} className="flex items-center gap-2">
                  <span
                    className="h-3 w-3 shrink-0 rounded-sm"
                    style={{ backgroundColor: slice.color }}
                  />
                  <span className="flex-1 min-w-0 truncate text-xs text-text-secondary">
                    {slice.name}
                  </span>
                  {SOURCE_ABBR[slice.name] && (
                    <span className="shrink-0 text-[10px] font-bold font-mono text-text-muted">
                      {SOURCE_ABBR[slice.name]}
                    </span>
                  )}
                  <span className="tabular-nums text-xs font-medium text-text-primary">
                    {slice.count}
                  </span>
                </div>
              ))}

              {/* Web article-type breakdown */}
              {webTypeSlices.map((slice) => (
                <div key={slice.name} className="flex items-center gap-2">
                  <span
                    className="h-3 w-3 shrink-0 rounded-sm"
                    style={{ backgroundColor: slice.color }}
                  />
                  <span className="flex-1 min-w-0 truncate text-xs text-text-secondary">
                    {slice.name}
                  </span>
                  <span className="tabular-nums text-xs font-medium text-text-primary">
                    {slice.count}
                  </span>
                </div>
              ))}

              {/* Empty sources */}
              {collectionData.source_summary
                .filter((s) => !s.has_content)
                .map((s) => (
                  <div
                    key={s.display_name}
                    className="flex items-center gap-2 opacity-50"
                  >
                    <span className="h-3 w-3 shrink-0 rounded-sm bg-border" />
                    <span className="flex-1 truncate text-xs text-text-muted">
                      {s.display_name}
                    </span>
                    <span className="text-[10px] uppercase tracking-wide text-text-muted">
                      {t.empty}
                    </span>
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
              {Object.entries(groups).map(([groupName, items]) => {
                const isWebGroup = WEB_GROUP_NAMES.has(groupName);
                const webSubGroups = isWebGroup ? groupWebByType(items) : null;

                return (
                  <details key={groupName} className="group">
                    <summary className="flex cursor-pointer select-none items-center justify-between px-5 py-3 bg-surface-muted hover:bg-surface-elevated transition-colors list-none">
                      <span className="text-sm font-medium text-text-primary">
                        {groupName}
                      </span>
                      <div className="flex items-center gap-3">
                        <span className="text-xs text-text-muted">
                          {t.itemCount(items.length)}
                        </span>
                        <Chevron className="h-4 w-4 text-text-muted transition-transform group-open:rotate-180" />
                      </div>
                    </summary>

                    <div className="px-4 py-3 space-y-2">
                      {webSubGroups
                        ? // ── Web: nested by article type ──────────────────────
                          webSubGroups.map(([type, typeItems]) => (
                            <details
                              key={type}
                              className="group/sub rounded border border-border overflow-hidden"
                            >
                              <summary className="flex cursor-pointer select-none items-center justify-between px-4 py-2 bg-surface hover:bg-surface-muted transition-colors list-none">
                                <div className="flex items-center gap-2">
                                  <span
                                    className={`rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${LABEL_STYLES[type]}`}
                                  >
                                    {type}
                                  </span>
                                  <span className="text-xs text-text-muted">
                                    {t.itemCount(typeItems.length)}
                                  </span>
                                </div>
                                <Chevron className="h-3.5 w-3.5 shrink-0 text-text-muted transition-transform group-open/sub:rotate-180" />
                              </summary>
                              <div className="px-3 py-3 space-y-2 bg-surface-muted">
                                {typeItems.map((item, i) => (
                                  <ItemCard key={i} item={item} uploadedFiles={uploadedFiles} />
                                ))}
                              </div>
                            </details>
                          ))
                        : // ── Non-web: flat list of collapsible items ───────────
                          items.map((item, i) => (
                            <ItemCard key={i} item={item} uploadedFiles={uploadedFiles} />
                          ))}
                    </div>
                  </details>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
