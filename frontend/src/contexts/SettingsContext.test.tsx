import { describe, it, expect, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import type { ReactNode } from "react";
import { SettingsProvider } from "./SettingsContext";
import { useSettings } from "./SettingsContext";
import { DEFAULT_SETTINGS } from "../types/settings";

// ─── Test helper ────────────────────────────────────────────────────────────
// Every renderHook call needs the hook to live inside a SettingsProvider.
// This wrapper factory keeps each test clean — just pass it as `wrapper`.
function createWrapper() {
  return function Wrapper({ children }: { children: ReactNode }) {
    return <SettingsProvider>{children}</SettingsProvider>;
  };
}

// ─── SettingsContext tests ───────────────────────────────────────────────────
describe("SettingsContext", () => {
  beforeEach(() => {
    // Start every test with a clean localStorage so stored values
    // from a previous test don't leak into the next one.
    localStorage.clear();
  });

  // ── Initialisation ─────────────────────────────────────────────────────────
  // These tests verify the initial state when nothing is stored yet.
  // They tell us: "on first load, the context must expose DEFAULT_SETTINGS".

  describe("initialisation", () => {
    it("exposes default language when localStorage is empty", () => {
      const { result } = renderHook(() => useSettings(), {
        wrapper: createWrapper(),
      });

      expect(result.current.settings.language).toBe(DEFAULT_SETTINGS.language);
    });

    it("exposes default theme when localStorage is empty", () => {
      const { result } = renderHook(() => useSettings(), {
        wrapper: createWrapper(),
      });

      expect(result.current.settings.theme).toBe(DEFAULT_SETTINGS.theme);
    });

    it("exposes default inputParameters when localStorage is empty", () => {
      const { result } = renderHook(() => useSettings(), {
        wrapper: createWrapper(),
      });

      expect(result.current.settings.inputParameters).toEqual(
        DEFAULT_SETTINGS.inputParameters,
      );
    });
  });

  // ── Persistence ────────────────────────────────────────────────────────────
  // These tests verify that previously saved settings are restored on mount.
  // They tell us: "if the user already configured something, respect it".

  describe("persistence", () => {
    it("loads saved settings from localStorage on mount", () => {
      // Pre-seed localStorage — simulates a returning user.
      localStorage.setItem(
        "mcp-settings",
        JSON.stringify({
          language: "no",
          theme: "light",
          inputParameters: { timeframe: "Last 30 days" },
        }),
      );

      const { result } = renderHook(() => useSettings(), {
        wrapper: createWrapper(),
      });

      expect(result.current.settings.language).toBe("no");
      expect(result.current.settings.theme).toBe("light");
      expect(result.current.settings.inputParameters.timeframe).toBe(
        "Last 30 days",
      );
    });

    it("falls back to defaults when localStorage contains invalid JSON", () => {
      localStorage.setItem("mcp-settings", "not-valid-json{{{");

      const { result } = renderHook(() => useSettings(), {
        wrapper: createWrapper(),
      });

      expect(result.current.settings).toEqual(DEFAULT_SETTINGS);
    });
  });

  // ── updateLanguage ─────────────────────────────────────────────────────────
  // These tests describe what calling updateLanguage should do.
  // We test the state change AND that it is persisted to localStorage,
  // because both are observable effects of calling the function.

  describe("updateLanguage", () => {
    it("updates the language in state", () => {
      const { result } = renderHook(() => useSettings(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.updateLanguage("no");
      });

      expect(result.current.settings.language).toBe("no");
    });

    it("persists the new language to localStorage", () => {
      const { result } = renderHook(() => useSettings(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.updateLanguage("no");
      });

      const stored = JSON.parse(localStorage.getItem("mcp-settings")!);
      expect(stored.language).toBe("no");
    });

    it("does not change theme or inputParameters when updating language", () => {
      const { result } = renderHook(() => useSettings(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.updateLanguage("no");
      });

      expect(result.current.settings.theme).toBe(DEFAULT_SETTINGS.theme);
      expect(result.current.settings.inputParameters).toEqual(
        DEFAULT_SETTINGS.inputParameters,
      );
    });
  });

  // ── updateTheme ────────────────────────────────────────────────────────────

  describe("updateTheme", () => {
    it("updates the theme in state", () => {
      const { result } = renderHook(() => useSettings(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.updateTheme("light");
      });

      expect(result.current.settings.theme).toBe("light");
    });

    it("persists the new theme to localStorage", () => {
      const { result } = renderHook(() => useSettings(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.updateTheme("light");
      });

      const stored = JSON.parse(localStorage.getItem("mcp-settings")!);
      expect(stored.theme).toBe("light");
    });

    it("does not change language or inputParameters when updating theme", () => {
      const { result } = renderHook(() => useSettings(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.updateTheme("light");
      });

      expect(result.current.settings.language).toBe(DEFAULT_SETTINGS.language);
      expect(result.current.settings.inputParameters).toEqual(
        DEFAULT_SETTINGS.inputParameters,
      );
    });
  });

  // ── updateInputParameters ──────────────────────────────────────────────────

  describe("updateInputParameters", () => {
    it("updates timeframe in inputParameters", () => {
      const { result } = renderHook(() => useSettings(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.updateInputParameters({ timeframe: "Q1 2025" });
      });

      expect(result.current.settings.inputParameters.timeframe).toBe(
        "Q1 2025",
      );
    });

    it("persists the updated inputParameters to localStorage", () => {
      const { result } = renderHook(() => useSettings(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.updateInputParameters({ timeframe: "Q1 2025" });
      });

      const stored = JSON.parse(localStorage.getItem("mcp-settings")!);
      expect(stored.inputParameters.timeframe).toBe("Q1 2025");
    });

    it("merges partial updates — other fields stay untouched", () => {
      // This test matters when we add more inputParameter fields later.
      // Passing only { timeframe } must not wipe out other future fields.
      const { result } = renderHook(() => useSettings(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.updateInputParameters({ timeframe: "Q2 2025" });
      });

      // Only timeframe changed — language and theme are untouched.
      expect(result.current.settings.language).toBe(DEFAULT_SETTINGS.language);
      expect(result.current.settings.theme).toBe(DEFAULT_SETTINGS.theme);
    });
  });

  // ── useSettings guard ──────────────────────────────────────────────────────
  // This test verifies that using the hook outside a Provider throws a clear
  // error message — much better than a cryptic "cannot read property of null".

  describe("useSettings guard", () => {
    it("throws when used outside a SettingsProvider", () => {
      // Suppress the expected React error boundary console output.
      const spy = vi.spyOn(console, "error").mockImplementation(() => {});

      expect(() => renderHook(() => useSettings())).toThrow(
        /SettingsProvider/,
      );

      spy.mockRestore();
    });
  });
});
