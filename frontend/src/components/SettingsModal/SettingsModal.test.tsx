import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { SettingsProvider } from "../../contexts/SettingsContext/SettingsContext";
import { SettingsModal } from "./SettingsModal";

// ─── Test helper ─────────────────────────────────────────────────────────────
// SettingsModal reads from SettingsContext, so it must live inside a Provider.
// onClose is a callback we spy on to verify the modal signals "close me".
function renderModal(props: { isOpen?: boolean; onClose?: () => void } = {}) {
  const onClose = props.onClose ?? vi.fn();
  const isOpen = props.isOpen ?? true;

  function Wrapper({ children }: { children: ReactNode }) {
    return <SettingsProvider>{children}</SettingsProvider>;
  }

  return {
    onClose,
    ...render(
      <Wrapper>
        <SettingsModal isOpen={isOpen} onClose={onClose} />
      </Wrapper>,
    ),
  };
}

// ─── SettingsModal tests ──────────────────────────────────────────────────────
describe("SettingsModal", () => {
  // Clear localStorage before each test to prevent language pollution from
  // other test files that may store "no" as the language.
  beforeEach(() => localStorage.clear());
  // ── Visibility ───────────────────────────────────────────────────────────
  // The modal must only be in the DOM when isOpen is true.
  // This is the most fundamental test — if this fails, nothing else matters.

  describe("visibility", () => {
    it("renders the modal when isOpen is true", () => {
      renderModal({ isOpen: true });
      expect(screen.getByRole("dialog")).toBeInTheDocument();
    });

    it("does not render the modal when isOpen is false", () => {
      renderModal({ isOpen: false });
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });
  });

  // ── Structure ─────────────────────────────────────────────────────────────
  // Check the two-panel layout: left nav + right content area.
  // We look for the nav category labels the user will see.

  describe("structure", () => {
    it("renders a close button", () => {
      renderModal();
      expect(
        screen.getByRole("button", { name: /close/i }),
      ).toBeInTheDocument();
    });

    it("renders all four nav categories", () => {
      renderModal();
      // The modal has two sections: "general" and "parameters"
      expect(
        screen.getByRole("button", { name: /general/i }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /parameters/i }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /council/i }),
      ).toBeInTheDocument();
    });

    it("shows General section content by default", () => {
      renderModal();
      // Default section is "general" which contains Language and Theme settings
      expect(screen.getByText(/^language$/i)).toBeInTheDocument();
      expect(screen.getByText(/theme/i)).toBeInTheDocument();
    });
  });

  // ── Close button ──────────────────────────────────────────────────────────

  describe("close button", () => {
    it("calls onClose when the close button is clicked", async () => {
      const onClose = vi.fn();
      const user = userEvent.setup();

      renderModal({ onClose });

      await user.click(screen.getByRole("button", { name: /close/i }));

      expect(onClose).toHaveBeenCalledOnce();
    });
  });

  // ── Navigation ────────────────────────────────────────────────────────────
  // Clicking a nav item switches the right panel content.

  describe("navigation", () => {
    it("shows Parameters content when Parameters nav item is clicked", async () => {
      const user = userEvent.setup();
      renderModal();

      await user.click(screen.getByRole("button", { name: /parameters/i }));

      expect(screen.getByText(/timeframe/i)).toBeInTheDocument();
    });

    it("shows General content when switching back from Parameters", async () => {
      const user = userEvent.setup();
      renderModal();

      await user.click(screen.getByRole("button", { name: /parameters/i }));
      await user.click(screen.getByRole("button", { name: /^general$/i }));

      expect(screen.getByText(/^language$/i)).toBeInTheDocument();
    });

    it("shows Council content when Council nav item is clicked", async () => {
      const user = userEvent.setup();
      renderModal();

      await user.click(screen.getByRole("button", { name: /council/i }));

      expect(screen.getByText(/^mode$/i)).toBeInTheDocument();
      expect(screen.getByRole("combobox", { name: /rounds/i })).toBeInTheDocument();
    });
  });

  // ── Language section ──────────────────────────────────────────────────────
  // The Language panel must show the two language options and save the choice.

  describe("Language section", () => {
    it("renders English and Norwegian options", () => {
      renderModal();
      expect(
        screen.getByRole("option", { name: /english/i }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("option", { name: /norwegian/i }),
      ).toBeInTheDocument();
    });

    it("selecting Norwegian updates the dropdown value", async () => {
      const user = userEvent.setup();
      renderModal();

      const select = screen.getByRole("combobox");
      await user.selectOptions(select, "no");

      expect(select).toHaveValue("no");
    });
  });

  // ── General section (theme) ───────────────────────────────────────────────
  // Theme buttons live in the "general" section which is shown by default.

  describe("General section (theme)", () => {
    it("renders Light and Dark theme buttons", () => {
      renderModal();

      expect(
        screen.getByRole("button", { name: /^light$/i }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /^dark$/i }),
      ).toBeInTheDocument();
    });

    it("clicking Light theme button selects it", async () => {
      const user = userEvent.setup();
      renderModal();

      await user.click(screen.getByRole("button", { name: /^light$/i }));

      expect(screen.getByRole("button", { name: /^light$/i })).toHaveAttribute(
        "aria-pressed",
        "true",
      );
    });
  });

  // ── Parameters section ────────────────────────────────────────────────────

  describe("Parameters section", () => {
    it("renders the Timeframe input field", async () => {
      const user = userEvent.setup();
      renderModal();

      await user.click(screen.getByRole("button", { name: /parameters/i }));

      expect(
        screen.getByRole("textbox", { name: /timeframe/i }),
      ).toBeInTheDocument();
    });

    it("typing in the Timeframe field updates its value", async () => {
      const user = userEvent.setup();
      renderModal();

      await user.click(screen.getByRole("button", { name: /parameters/i }));
      const input = screen.getByRole("textbox", { name: /timeframe/i });
      await user.type(input, "Q1 2025");

      expect(input).toHaveValue("Q1 2025");
    });
  });

  describe("Council section", () => {
    it("renders council runtime controls", async () => {
      const user = userEvent.setup();
      renderModal();

      await user.click(screen.getByRole("button", { name: /council/i }));

      expect(screen.getByRole("combobox", { name: /mode/i })).toHaveValue(
        "conference",
      );
      expect(screen.getByRole("combobox", { name: /rounds/i })).toHaveValue("2");
      expect(screen.getByRole("combobox", { name: /round timeout/i })).toHaveValue(
        "180",
      );
      expect(screen.getByRole("button", { name: /^on$/i })).toHaveAttribute(
        "aria-pressed",
        "true",
      );
      expect(
        screen.getByRole("combobox", { name: /vote retry attempts/i }),
      ).toHaveValue("1");
    });

    it("updates council settings controls", async () => {
      const user = userEvent.setup();
      renderModal();

      await user.click(screen.getByRole("button", { name: /council/i }));
      await user.selectOptions(
        screen.getByRole("combobox", { name: /mode/i }),
        screen.getByRole("option", { name: /quick/i }),
      );
      await user.selectOptions(
        screen.getByRole("combobox", { name: /rounds/i }),
        screen.getByRole("option", { name: "4" }),
      );
      await user.click(screen.getByRole("button", { name: /^off$/i }));

      expect(screen.getByRole("combobox", { name: /mode/i })).toHaveValue(
        "quick",
      );
      expect(screen.getByRole("combobox", { name: /rounds/i })).toHaveValue("4");
      expect(screen.getByRole("button", { name: /^off$/i })).toHaveAttribute(
        "aria-pressed",
        "true",
      );
    });
  });
});
