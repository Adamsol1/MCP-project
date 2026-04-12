/**
 * SourceList — renders a list of sources in APA7th format with type badges
 * and bidirectional hover highlighting.
 *
 * Props:
 *   sources         — list of Source objects with citation metadata
 *   highlightedRefs — the refs currently hovered elsewhere (e.g. ["[1]"]), or []
 *   onSourceHover   — called with [source.ref] on enter, [] on leave
 *
 * Run with: cd frontend && npx vitest SourceList.test
 */

import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import userEvent from "@testing-library/user-event";
import SourceList from "./SourceList";
import type { Source } from "../../types/conversation";

// ── Fixtures ─────────────────────────────────────────────────────────────────

const sourceNorway: Source = {
  id: "geopolitical/norway_russia",
  ref: "[1]",
  source_type: "kb",
  citation: {
    author: "Threat Intelligence System",
    year: "2025",
    title: "Norwegian-Russian Geopolitical Relations",
    publisher: "Internal Knowledge Bank",
  },
};

const sourceEnergy: Source = {
  id: "sectors/energy",
  ref: "[2]",
  source_type: "kb",
  citation: {
    author: "Threat Intelligence System",
    year: "2025",
    title: "Energy Sector Threat Landscape",
    publisher: "Internal Knowledge Bank",
  },
};

// ── Group 1: APA7th formatting ────────────────────────────────────────────────

describe("SourceList — APA7th formatting", () => {
  it("renders author, year and publisher as plain text", () => {
    render(
      <SourceList
        sources={[sourceNorway]}
        highlightedRefs={[]}
        onSourceHover={vi.fn()}
      />,
    );

    expect(
      screen.getByText(/Threat Intelligence System\. \(2025\)\./)
    ).toBeInTheDocument();
    expect(screen.getByText(/Internal Knowledge Bank\./)).toBeInTheDocument();
  });

  it("renders the title in italics", () => {
    render(
      <SourceList
        sources={[sourceNorway]}
        highlightedRefs={[]}
        onSourceHover={vi.fn()}
      />,
    );

    const em = document.querySelector("em");
    expect(em).toBeInTheDocument();
    expect(em).toHaveTextContent("Norwegian-Russian Geopolitical Relations");
  });

  it("renders one card per source", () => {
    render(
      <SourceList
        sources={[sourceNorway, sourceEnergy]}
        highlightedRefs={[]}
        onSourceHover={vi.fn()}
      />,
    );

    expect(
      screen.getByText(/Norwegian-Russian Geopolitical Relations/)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Energy Sector Threat Landscape/)
    ).toBeInTheDocument();
  });

  it("renders nothing when sources list is empty", () => {
    const { container } = render(
      <SourceList
        sources={[]}
        highlightedRefs={[]}
        onSourceHover={vi.fn()}
      />,
    );

    expect(container.firstChild).toBeEmptyDOMElement();
  });
});

// ── Group 2: Type badge ───────────────────────────────────────────────────────

describe("SourceList — type badge", () => {
  it("renders the source_type as a badge", () => {
    render(
      <SourceList
        sources={[sourceNorway]}
        highlightedRefs={[]}
        onSourceHover={vi.fn()}
      />,
    );

    expect(screen.getByText("[kb]")).toBeInTheDocument();
  });

  it("renders the ref marker alongside the source", () => {
    render(
      <SourceList
        sources={[sourceNorway]}
        highlightedRefs={[]}
        onSourceHover={vi.fn()}
      />,
    );

    expect(screen.getByText("[1]")).toBeInTheDocument();
  });
});

// ── Group 3: Hover interactions ───────────────────────────────────────────────

describe("SourceList — hover", () => {
  it("hovering a source card calls onSourceHover with [ref]", async () => {
    const user = userEvent.setup();
    const onSourceHover = vi.fn();

    render(
      <SourceList
        sources={[sourceNorway]}
        highlightedRefs={[]}
        onSourceHover={onSourceHover}
      />,
    );

    const card = screen.getByRole("listitem");
    await user.hover(card);

    expect(onSourceHover).toHaveBeenCalledWith("[1]");
  });

  it("mouse leave on a source card calls onSourceHover with null", async () => {
    const user = userEvent.setup();
    const onSourceHover = vi.fn();

    render(
      <SourceList
        sources={[sourceNorway]}
        highlightedRefs={[]}
        onSourceHover={onSourceHover}
      />,
    );

    const card = screen.getByRole("listitem");
    await user.hover(card);
    await user.unhover(card);

    expect(onSourceHover).toHaveBeenLastCalledWith(null);
  });
});

// ── Group 4: Highlight state ──────────────────────────────────────────────────

describe("SourceList — highlight state", () => {
  it("source card is highlighted when highlightedRefs includes its ref", () => {
    render(
      <SourceList
        sources={[sourceNorway]}
        highlightedRefs={["[1]"]}
        onSourceHover={vi.fn()}
      />,
    );

    const card = screen.getByRole("listitem");
    expect(card).toHaveClass("text-primary");
  });

  it("source card is not highlighted when highlightedRefs is empty", () => {
    render(
      <SourceList
        sources={[sourceNorway]}
        highlightedRefs={[]}
        onSourceHover={vi.fn()}
      />,
    );

    const card = screen.getByRole("listitem");
    expect(card).not.toHaveClass("text-primary");
  });

  it("only the matching card is highlighted when multiple sources exist", () => {
    render(
      <SourceList
        sources={[sourceNorway, sourceEnergy]}
        highlightedRefs={["[1]"]}
        onSourceHover={vi.fn()}
      />,
    );

    const cards = screen.getAllByRole("listitem");
    expect(cards[0]).toHaveClass("text-primary");
    expect(cards[1]).not.toHaveClass("text-primary");
  });
});
