import { describe, expect, it } from "vitest";
import { getWorkspacePhaseForDialogueStage } from "./workspacePhase";

describe("getWorkspacePhaseForDialogueStage", () => {
  it("maps collection-related stages to the collection workspace", () => {
    expect(getWorkspacePhaseForDialogueStage("source_selecting")).toBe(
      "collection",
    );
    expect(getWorkspacePhaseForDialogueStage("collecting")).toBe("collection");
    expect(getWorkspacePhaseForDialogueStage("reviewing")).toBe("collection");
  });

  it("maps the complete stage to the analysis workspace", () => {
    expect(getWorkspacePhaseForDialogueStage("complete")).toBe("analysis");
  });

  it("maps earlier dialogue stages to the direction workspace", () => {
    expect(getWorkspacePhaseForDialogueStage("initial")).toBe("direction");
    expect(getWorkspacePhaseForDialogueStage("gathering")).toBe("direction");
    expect(getWorkspacePhaseForDialogueStage("pir_confirming")).toBe(
      "direction",
    );
  });
});
