import { render, screen, act } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { WorkspaceProvider, useWorkspace } from "./WorkspaceContext";
import type { CollectionDisplayData, PirData } from "../../types/conversation";

function HighlightedRefsDisplay() {
  const { highlightedRefs } = useWorkspace();
  return <span data-testid="refs">{highlightedRefs.join(",") || "empty"}</span>;
}

function PirDataDisplay() {
  const { pirData } = useWorkspace();
  return <span data-testid="pir">{pirData ? pirData.pir_text : "null"}</span>;
}

function CollectionDataDisplay() {
  const { collectionData } = useWorkspace();
  return (
    <span data-testid="collection">
      {collectionData ? collectionData.collected_data.length.toString() : "null"}
    </span>
  );
}

function SetHighlightedRefsButton({ refs }: { refs: string[] }) {
  const { setHighlightedRefs } = useWorkspace();
  return <button onClick={() => setHighlightedRefs(refs)}>set refs</button>;
}

function SetPirDataButton({ pirData }: { pirData: PirData }) {
  const { setPirData } = useWorkspace();
  return <button onClick={() => setPirData(pirData)}>set pir</button>;
}

function SetCollectionDataButton({ data }: { data: CollectionDisplayData }) {
  const { setCollectionData } = useWorkspace();
  return <button onClick={() => setCollectionData(data)}>set collection</button>;
}

describe("WorkspaceContext", () => {
  it("provides empty default workspace values", () => {
    render(
      <WorkspaceProvider>
        <HighlightedRefsDisplay />
        <PirDataDisplay />
        <CollectionDataDisplay />
      </WorkspaceProvider>,
    );

    expect(screen.getByTestId("refs")).toHaveTextContent("empty");
    expect(screen.getByTestId("pir")).toHaveTextContent("null");
    expect(screen.getByTestId("collection")).toHaveTextContent("null");
  });

  it("updates highlighted refs", async () => {
    render(
      <WorkspaceProvider>
        <HighlightedRefsDisplay />
        <SetHighlightedRefsButton refs={["[1]", "[2]"]} />
      </WorkspaceProvider>,
    );

    await act(async () => {
      screen.getByRole("button", { name: "set refs" }).click();
    });

    expect(screen.getByTestId("refs")).toHaveTextContent("[1],[2]");
  });

  it("updates pir data", async () => {
    render(
      <WorkspaceProvider>
        <PirDataDisplay />
        <SetPirDataButton
          pirData={{
            pir_text: "Norway threat assessment.",
            claims: [],
            sources: [],
            pirs: [],
            reasoning: "",
          }}
        />
      </WorkspaceProvider>,
    );

    await act(async () => {
      screen.getByRole("button", { name: "set pir" }).click();
    });

    expect(screen.getByTestId("pir")).toHaveTextContent(
      "Norway threat assessment.",
    );
  });

  it("updates collection data", async () => {
    render(
      <WorkspaceProvider>
        <CollectionDataDisplay />
        <SetCollectionDataButton
          data={{
            collected_data: [
              { source: "web", resource_id: null, content: "Sample content" },
            ],
            source_summary: [
              {
                display_name: "Web",
                count: 1,
                resource_ids: [],
                has_content: true,
              },
            ],
          }}
        />
      </WorkspaceProvider>,
    );

    await act(async () => {
      screen.getByRole("button", { name: "set collection" }).click();
    });

    expect(screen.getByTestId("collection")).toHaveTextContent("1");
  });
});
