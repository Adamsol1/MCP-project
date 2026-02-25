import { useState } from "react";
import { useSettings } from "../../contexts/SettingsContext";
import type { Language, Theme } from "../../types/settings";

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

type NavSection = "language" | "appearance" | "parameters";

export function SettingsModal({ isOpen, onClose }: SettingsModalProps) {
  const { settings, updateLanguage, updateTheme, updateInputParameters } =
    useSettings();
  const [activeSection, setActiveSection] = useState<NavSection>("language");

  if (!isOpen) return null;

  return (
    /* Full-screen dark backdrop */
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      {/* Modal box */}
      <div
        role="dialog"
        aria-modal="true"
        className="flex h-130 w-185 overflow-hidden rounded-lg bg-gray-800 text-gray-100 shadow-2xl"
      >
        {/* ── Left nav ─────────────────────────────────────── */}
        <nav className="flex w-48 flex-col gap-1 border-r border-gray-700 p-4 pt-6">
          <p className="mb-2 text-xs font-semibold uppercase tracking-widest text-gray-400">
            Options
          </p>
          {(["language", "appearance", "parameters"] as const).map((section) => (
            <button
              key={section}
              onClick={() => setActiveSection(section)}
              className={`rounded px-3 py-2 text-left text-sm capitalize ${
                activeSection === section
                  ? "bg-gray-600 text-white"
                  : "text-gray-300 hover:bg-gray-700"
              }`}
            >
              {section}
            </button>
          ))}
        </nav>

        {/* ── Right panel ──────────────────────────────────── */}
        <div className="relative flex flex-1 flex-col p-8 pt-6">
          {/* Close button */}
          <button
            aria-label="Close settings"
            onClick={onClose}
            className="absolute right-4 top-4 text-gray-400 hover:text-white"
          >
            ✕
          </button>

          <h2 className="mb-1 text-base font-semibold capitalize text-gray-100">
            {activeSection}
          </h2>
          <main className="mt-2">
            {activeSection === "language" && (
              <LanguageSection
                language={settings.language}
                onChange={updateLanguage}
              />
            )}
            {activeSection === "appearance" && (
              <AppearanceSection theme={settings.theme} onChange={updateTheme} />
            )}
            {activeSection === "parameters" && (
              <ParametersSection
                timeframe={settings.inputParameters.timeframe}
                onChange={(v) => updateInputParameters({ timeframe: v })}
              />
            )}
          </main>
        </div>
      </div>
    </div>
  );
}

// ─── Shared layout ───────────────────────────────────────────────────────────
// Every setting row: label+description on the left, control on the right.
function SettingRow({
  label,
  description,
  control,
}: {
  label: string;
  description?: string;
  control: React.ReactNode;
}) {
  return (
    <div className="flex items-center justify-between border-b border-gray-700 py-4">
      <div className="mr-8">
        <p className="text-sm font-medium text-gray-100">{label}</p>
        {description && (
          <p className="mt-0.5 text-xs text-gray-400">{description}</p>
        )}
      </div>
      <div className="shrink-0">{control}</div>
    </div>
  );
}

// ─── Shared control styles ────────────────────────────────────────────────────
const selectClass =
  "rounded border border-gray-600 bg-gray-700 px-3 py-1.5 text-sm text-gray-100 focus:outline-none focus:ring-1 focus:ring-blue-500";

const inputClass =
  "w-52 rounded border border-gray-600 bg-gray-700 px-3 py-1.5 text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-blue-500";

// ─── Sections ─────────────────────────────────────────────────────────────────

function LanguageSection({
  language,
  onChange,
}: {
  language: Language;
  onChange: (l: Language) => void;
}) {
  return (
    <SettingRow
      label="AI Output Language"
      description="The language the AI will use in its responses."
      control={
        <select
          value={language}
          onChange={(e) => onChange(e.target.value as Language)}
          className={selectClass}
        >
          <option value="en">English</option>
          <option value="no">Norwegian</option>
        </select>
      }
    />
  );
}

function AppearanceSection({
  theme,
  onChange,
}: {
  theme: Theme;
  onChange: (t: Theme) => void;
}) {
  return (
    <SettingRow
      label="Theme"
      description="Choose between light and dark interface."
      control={
        <div className="flex gap-2">
          {(["light", "dark"] as const).map((t) => (
            <button
              key={t}
              aria-pressed={theme === t}
              onClick={() => onChange(t)}
              className={`rounded border px-4 py-1.5 text-sm capitalize transition-colors ${
                theme === t
                  ? "border-blue-500 bg-blue-600 text-white"
                  : "border-gray-600 bg-gray-700 text-gray-300 hover:bg-gray-600"
              }`}
            >
              {t}
            </button>
          ))}
        </div>
      }
    />
  );
}

function ParametersSection({
  timeframe,
  onChange,
}: {
  timeframe: string;
  onChange: (v: string) => void;
}) {
  return (
    <SettingRow
      label="Timeframe"
      description="Auto-filled into each prompt so the AI knows the relevant period."
      control={
        <input
          id="timeframe"
          type="text"
          value={timeframe}
          onChange={(e) => onChange(e.target.value)}
          placeholder="e.g. Last 30 days"
          className={inputClass}
        />
      }
    />
  );
}
