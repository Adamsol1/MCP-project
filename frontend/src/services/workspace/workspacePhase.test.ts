import { describe, expect, it } from "vitest";
import { getWorkspacePhaseForDialogueStage } from "./workspacePhase";

describe("getWorkspacePhaseForDialogueStage", () => {
  it("maps collection-related stages to the collection workspace", () => {
    expect(getWorkspacePhaseForDialogueStage("planning")).toBe("collection");
    expect(getWorkspacePhaseForDialogueStage("plan_confirming")).toBe(
      "collection",
    );
    expect(getWorkspacePhaseForDialogueStage("source_selecting")).toBe(
      "collection",
    );
    expect(getWorkspacePhaseForDialogueStage("collecting")).toBe("collection");
  });

  it("maps processing-related stages to the processing workspace", () => {
    expect(getWorkspacePhaseForDialogueStage("reviewing")).toBe("processing");
    expect(getWorkspacePhaseForDialogueStage("processing")).toBe("processing");
    expect(getWorkspacePhaseForDialogueStage("complete")).toBe("processing");
  });

  it("maps earlier dialogue stages to the direction workspace", () => {
    expect(getWorkspacePhaseForDialogueStage("initial")).toBe("direction");
    expect(getWorkspacePhaseForDialogueStage("gathering")).toBe("direction");
    expect(getWorkspacePhaseForDialogueStage("pir_confirming")).toBe(
      "direction",
    );
  });
});
