import { useState } from "react";
import { useSettings } from "../../contexts/SettingsContext/SettingsContext";
import { useT } from "../../i18n/useT";
import type { Language, Theme } from "../../types/settings";

/** Props for the SettingsModal component. */
interface SettingsModalProps {
  /** Whether the modal is currently visible. Controlled by the parent (App). */
  isOpen: boolean;
  /** Called when the user clicks the close button. Parent should set isOpen to false. */
  onClose: () => void;
}

/** The navigable sections in the settings left-nav. */
type NavSection = "general" | "parameters";

/**
 * Full-screen settings modal with an Obsidian-inspired two-panel layout.
 *
 * Layout:
 *   Left nav  — category buttons (Language, Appearance, Parameters).
 *   Right panel — content for the active category, with a close button.
 *
 * Visibility:
 *   Returns null when isOpen is false so the modal is fully unmounted,
 *   avoiding any background state or focus traps while closed.
 *
 * State:
 *   activeSection — which nav category is selected. Defaults to "language".
 *   All settings values come from SettingsContext via useSettings().
 */
export function SettingsModal({ isOpen, onClose }: SettingsModalProps) {
  const { settings, updateLanguage, updateTheme, updateInputParameters } =
    useSettings();
  const t = useT();

  // Tracks which settings category is displayed in the right panel.
  const [activeSection, setActiveSection] = useState<NavSection>("general");

  // Return nothing when closed — keeps the DOM clean and avoids focus issues.
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onClose}>
      {/* Modal box */}
      <div
        role="dialog"
        aria-modal="true"
        className="flex h-130 w-185 overflow-hidden rounded-lg border border-border bg-surface text-text-primary shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* ── Left nav ─────────────────────────────────────── */}
        {/* Each button sets activeSection, which swaps the right panel content. */}
        <nav className="flex w-48 flex-col gap-1 border-r border-border p-4 pt-6">
          <p className="mb-2 text-xs font-semibold uppercase tracking-widest text-text-muted">
            {t.settingsOptions}
          </p>
          {(["general", "parameters"] as const).map(
            (section) => (
              <button
                key={section}
                onClick={() => setActiveSection(section)}
                className={`rounded px-3 py-2 text-left text-sm capitalize ${
                  activeSection === section
                    ? "bg-surface-elevated text-text-primary"
                    : "text-text-secondary hover:bg-surface-elevated hover:text-text-primary"
                }`}
              >
                {t.navLabels[section]}
              </button>
            ),
          )}
        </nav>

        {/* ── Right panel ──────────────────────────────────── */}
        <div className="relative flex flex-1 flex-col p-8 pt-6">
          {/* Close button — positioned absolute so it never pushes content down. */}
          <button
            aria-label={t.closeSettings}
            onClick={onClose}
            className="absolute right-4 top-4 text-text-muted hover:text-text-primary"
          >
            ✕
          </button>

          {/* Section heading mirrors the active nav item. */}
          <h2 className="mb-1 text-base font-semibold capitalize text-text-primary">
            {t.navLabels[activeSection]}
          </h2>

          {/* Only the active section component is mounted at a time. */}
          <main className="mt-2">
            {activeSection === "general" && (
              <GeneralSection
                language={settings.language}
                onLanguageChange={updateLanguage}
                theme={settings.theme}
                onThemeChange={updateTheme}
              />
            )}
            {activeSection === "parameters" && (
              <ParametersSection
                language={settings.language}
                onLanguageChange={updateLanguage}
                timeframe={settings.inputParameters.timeframe}
                onTimeframeChange={(v) => updateInputParameters({ timeframe: v })}
              />
            )}
          </main>
        </div>
      </div>
    </div>
  );
}

// ─── Shared layout ────────────────────────────────────────────────────────────

/**
 * Reusable row layout used by every setting item.
 * Renders the label and optional description on the left,
 * and the interactive control (dropdown, buttons, input) pinned to the right.
 */
function SettingRow({
  label,
  description,
  control,
  htmlFor,
}: {
  /** Bold setting name shown to the user. */
  label: string;
  /** Optional muted sub-text explaining what the setting does. */
  description?: string;
  /** The interactive control element (select, buttons, input, etc.). */
  control: React.ReactNode;
  /** When provided, renders the label as a <label> linked to the control's id. */
  htmlFor?: string;
}) {
  return (
    <div className="flex items-start justify-between border-b border-border py-4">
      <div className="mr-8">
        {htmlFor ? (
          <label
            htmlFor={htmlFor}
            className="block text-sm font-medium text-text-primary"
          >
            {label}
          </label>
        ) : (
          <p className="text-sm font-medium text-text-primary">{label}</p>
        )}
        {description && (
          <p className="mt-0.5 text-xs text-text-muted">{description}</p>
        )}
      </div>
      {/* shrink-0 prevents the control from being squeezed by long label text. */}
      <div className="shrink-0 pt-0.5">{control}</div>
    </div>
  );
}

// ─── Shared control styles ────────────────────────────────────────────────────
// Defined as constants so all controls share identical look and focus styles.

/** Tailwind classes applied to every <select> element in the modal. */
const selectClass =
  "rounded border border-border bg-surface px-3 py-1.5 text-sm text-text-primary focus:outline-none focus:ring-1 focus:ring-primary";

/** Tailwind classes applied to every <input type="text"> element in the modal. */
const inputClass =
  "w-52 rounded border border-border bg-surface px-3 py-1.5 text-sm text-text-primary placeholder-text-secondary focus:outline-none focus:ring-1 focus:ring-primary";

// ─── Section components ───────────────────────────────────────────────────────

/** General section — interface language and theme. */
function GeneralSection({
  language,
  onLanguageChange,
  theme,
  onThemeChange,
}: {
  language: Language;
  onLanguageChange: (l: Language) => void;
  theme: Theme;
  onThemeChange: (t: Theme) => void;
}) {
  const t = useT();
  return (
    <>
      <SettingRow
        label={t.uiLanguage}
        description={t.uiLanguageDesc}
        control={
          <select
            value={language}
            onChange={(e) => onLanguageChange(e.target.value as Language)}
            className={selectClass}
          >
            <option value="en">{t.langEnglish}</option>
            <option value="no">{t.langNorwegian}</option>
          </select>
        }
      />
      <SettingRow
        label={t.themeLabel}
        description={t.themeDesc}
        control={
          <div className="flex gap-2">
            {(["light", "dark"] as const).map((themeOption) => (
              <button
                key={themeOption}
                aria-pressed={theme === themeOption}
                onClick={() => onThemeChange(themeOption)}
                className={`rounded border px-4 py-1.5 text-sm capitalize transition-colors ${
                  theme === themeOption
                    ? "border-primary bg-primary-dark text-text-inverse"
                    : "border-border bg-surface text-text-primary hover:bg-surface-elevated"
                }`}
              >
                {t.themeLabels[themeOption]}
              </button>
            ))}
          </div>
        }
      />
    </>
  );
}

/** Parameters section — AI output language and prompt context fields. */
function ParametersSection({
  language,
  onLanguageChange,
  timeframe,
  onTimeframeChange,
}: {
  language: Language;
  onLanguageChange: (l: Language) => void;
  timeframe: string;
  onTimeframeChange: (v: string) => void;
}) {
  const t = useT();
  return (
    <>
      <SettingRow
        label={t.aiOutputLanguage}
        description={t.aiOutputLanguageDesc}
        control={
          <select
            value={language}
            onChange={(e) => onLanguageChange(e.target.value as Language)}
            className={selectClass}
          >
            <option value="en">{t.langEnglish}</option>
            <option value="no">{t.langNorwegian}</option>
          </select>
        }
      />
      <SettingRow
        label={t.timeframeLabel}
        htmlFor="timeframe"
        description={t.timeframeDesc}
        control={
          <input
            id="timeframe"
            type="text"
            value={timeframe}
            onChange={(e) => onTimeframeChange(e.target.value)}
            placeholder={t.timeframePlaceholder}
            className={inputClass}
          />
        }
      />
    </>
  );
}
