/**
 * CitationText — renders pir_text with inline [N] citation markers and
 * bidirectional hover highlighting.
 *
 * Props:
 *   pirText       — full text string, may contain [1], [2] … markers
 *   claims        — list of Claim objects (text + source_ref + source_id)
 *   highlightedRef — the ref currently hovered elsewhere (e.g. "[1]"), or null
 *   onRefHover    — called with a ref string on enter, null on leave
 *
 * Run with: cd frontend && npx vitest CitationText.test
 */

import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import userEvent from "@testing-library/user-event";
import CitationText from "./CitationText";
import type { Claim } from "../../types/conversation";

// ── Fixtures ─────────────────────────────────────────────────────────────────

const claimNorway: Claim = {
  id: "claim_1",
  text: "Norway faces elevated risk",
  source_ref: "[1]",
  source_id: "geopolitical/norway_russia",
};

const claimEnergy: Claim = {
  id: "claim_2",
  text: "Energy infrastructure is vulnerable",
  source_ref: "[2]",
  source_id: "sectors/energy",
};

// ── Group 1: Plain text (no markers) ─────────────────────────────────────────

describe("CitationText — plain text", () => {
  it("renders prose with no claims as a single text node", () => {
    render(
      <CitationText
        text="No sources here, just analysis."
        claims={[]}
        highlightedRef={null}
        onRefHover={vi.fn()}
      />
    );

    expect(
      screen.getByText("No sources here, just analysis.")
    ).toBeInTheDocument();
    expect(document.querySelectorAll("sup")).toHaveLength(0);
  });

  it("renders text that has no matching claim marker as plain prose", () => {
    render(
      <CitationText
        text="Some analytic sentence without a marker."
        claims={[claimNorway]}
        highlightedRef={null}
        onRefHover={vi.fn()}
      />
    );

    expect(
      screen.getByText(/Some analytic sentence without a marker\./)
    ).toBeInTheDocument();
    expect(document.querySelectorAll("sup")).toHaveLength(0);
  });
});

// ── Group 2: Marker rendering ─────────────────────────────────────────────────

describe("CitationText — marker rendering", () => {
  it("renders [N] marker as a superscript element", () => {
    render(
      <CitationText
        text="Norway faces elevated risk[1]"
        claims={[claimNorway]}
        highlightedRef={null}
        onRefHover={vi.fn()}
      />
    );

    const sup = document.querySelector("sup");
    expect(sup).toBeInTheDocument();
    expect(sup).toHaveTextContent("[1]");
  });

  it("renders multiple [N] markers as separate superscript elements", () => {
    render(
      <CitationText
        text="Norway faces elevated risk[1] and Energy infrastructure is vulnerable[2]"
        claims={[claimNorway, claimEnergy]}
        highlightedRef={null}
        onRefHover={vi.fn()}
      />
    );

    const sups = document.querySelectorAll("sup");
    expect(sups).toHaveLength(2);
    expect(sups[0]).toHaveTextContent("[1]");
    expect(sups[1]).toHaveTextContent("[2]");
  });
});

// ── Group 3: Hover on [N] marker ──────────────────────────────────────────────

describe("CitationText — marker hover", () => {
  it("hovering [N] calls onRefHover with that ref", async () => {
    const user = userEvent.setup();
    const onRefHover = vi.fn();

    render(
      <CitationText
        text="Norway faces elevated risk[1]"
        claims={[claimNorway]}
        highlightedRef={null}
        onRefHover={onRefHover}
      />
    );

    const sup = document.querySelector("sup")!;
    await user.hover(sup);

    expect(onRefHover).toHaveBeenCalledWith("[1]");
  });

  it("mouse leave on [N] calls onRefHover(null)", async () => {
    const user = userEvent.setup();
    const onRefHover = vi.fn();

    render(
      <CitationText
        text="Norway faces elevated risk[1]"
        claims={[claimNorway]}
        highlightedRef={null}
        onRefHover={onRefHover}
      />
    );

    const sup = document.querySelector("sup")!;
    await user.hover(sup);
    await user.unhover(sup);

    expect(onRefHover).toHaveBeenLastCalledWith(null);
  });
});

// ── Group 4: Hover on claim text span ────────────────────────────────────────

describe("CitationText — claim text hover", () => {
  it("hovering a claim text span calls onRefHover with its source_ref", async () => {
    const user = userEvent.setup();
    const onRefHover = vi.fn();

    render(
      <CitationText
        text="Norway faces elevated risk[1]"
        claims={[claimNorway]}
        highlightedRef={null}
        onRefHover={onRefHover}
      />
    );

    const claimSpan = screen.getByText("Norway faces elevated risk");
    await user.hover(claimSpan);

    expect(onRefHover).toHaveBeenCalledWith("[1]");
  });

  it("mouse leave on claim text span calls onRefHover(null)", async () => {
    const user = userEvent.setup();
    const onRefHover = vi.fn();

    render(
      <CitationText
        text="Norway faces elevated risk[1]"
        claims={[claimNorway]}
        highlightedRef={null}
        onRefHover={onRefHover}
      />
    );

    const claimSpan = screen.getByText("Norway faces elevated risk");
    await user.hover(claimSpan);
    await user.unhover(claimSpan);

    expect(onRefHover).toHaveBeenLastCalledWith(null);
  });
});

// ── Group 5: Highlight state ──────────────────────────────────────────────────

describe("CitationText — highlight state", () => {
  it("claim text span is highlighted when highlightedRef matches its source_ref", () => {
    render(
      <CitationText
        text="Norway faces elevated risk[1]"
        claims={[claimNorway]}
        highlightedRef="[1]"
        onRefHover={vi.fn()}
      />
    );

    const claimSpan = screen.getByText("Norway faces elevated risk");
    expect(claimSpan).toHaveClass("bg-primary-subtle");
  });

  it("claim text span is not highlighted when highlightedRef is null", () => {
    render(
      <CitationText
        text="Norway faces elevated risk[1]"
        claims={[claimNorway]}
        highlightedRef={null}
        onRefHover={vi.fn()}
      />
    );

    const claimSpan = screen.getByText("Norway faces elevated risk");
    expect(claimSpan).not.toHaveClass("bg-primary-subtle");
  });

  it("only the matching claim is highlighted when multiple claims exist", () => {
    render(
      <CitationText
        text="Norway faces elevated risk[1] Energy infrastructure is vulnerable[2]"
        claims={[claimNorway, claimEnergy]}
        highlightedRef="[1]"
        onRefHover={vi.fn()}
      />
    );

    expect(screen.getByText("Norway faces elevated risk")).toHaveClass(
      "bg-primary-subtle"
    );
    expect(
      screen.getByText("Energy infrastructure is vulnerable")
    ).not.toHaveClass("bg-primary-subtle");
  });
});
