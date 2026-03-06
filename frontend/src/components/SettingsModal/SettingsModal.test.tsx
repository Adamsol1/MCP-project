import { describe, it, expect, vi } from "vitest";
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

    it("renders all three nav categories", () => {
      renderModal();
      expect(
        screen.getByRole("button", { name: /language/i }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /appearance/i }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /parameters/i }),
      ).toBeInTheDocument();
    });

    it("shows Language section content by default", () => {
      renderModal();
      // The right panel should start on Language
      expect(screen.getByText(/ai output language/i)).toBeInTheDocument();
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
    it("shows Appearance content when Appearance nav item is clicked", async () => {
      const user = userEvent.setup();
      renderModal();

      await user.click(screen.getByRole("button", { name: /appearance/i }));

      expect(screen.getByText(/theme/i)).toBeInTheDocument();
    });

    it("shows Parameters content when Parameters nav item is clicked", async () => {
      const user = userEvent.setup();
      renderModal();

      await user.click(screen.getByRole("button", { name: /parameters/i }));

      expect(screen.getByText(/timeframe/i)).toBeInTheDocument();
    });

    it("shows Language content when Language nav item is clicked after switching away", async () => {
      const user = userEvent.setup();
      renderModal();

      await user.click(screen.getByRole("button", { name: /appearance/i }));
      await user.click(screen.getByRole("button", { name: /language/i }));

      expect(screen.getByText(/ai output language/i)).toBeInTheDocument();
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

      await user.selectOptions(
        screen.getByRole("combobox"),
        screen.getByRole("option", { name: /norwegian/i }),
      );

      expect(
        (
          screen.getByRole("option", {
            name: /norwegian/i,
          }) as HTMLOptionElement
        ).selected,
      ).toBe(true);
    });
  });

  // ── Appearance section ────────────────────────────────────────────────────

  describe("Appearance section", () => {
    it("renders Light and Dark theme buttons", async () => {
      const user = userEvent.setup();
      renderModal();

      await user.click(screen.getByRole("button", { name: /appearance/i }));

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

      await user.click(screen.getByRole("button", { name: /appearance/i }));
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
});
