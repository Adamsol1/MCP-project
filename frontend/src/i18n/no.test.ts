import { describe, it, expect } from "vitest";
import { no } from "./no";
import { en } from "./en";

describe("no translation — function keys", () => {
  it("collectionRunLabel returns a non-empty string containing the number", () => {
    const result = no.collectionRunLabel(3);
    expect(typeof result).toBe("string");
    expect(result.length).toBeGreaterThan(0);
    expect(result).toContain("3");
  });

  it("pirSources returns a non-empty string containing the count", () => {
    const result = no.pirSources(5);
    expect(typeof result).toBe("string");
    expect(result.length).toBeGreaterThan(0);
    expect(result).toContain("5");
  });

  it("itemsAcrossSources returns a non-empty string with both numbers", () => {
    const result = no.itemsAcrossSources(10, 3);
    expect(typeof result).toBe("string");
    expect(result.length).toBeGreaterThan(0);
    expect(result).toContain("10");
    expect(result).toContain("3");
  });

  it("itemCount returns a non-empty string containing the count (singular)", () => {
    const result = no.itemCount(1);
    expect(typeof result).toBe("string");
    expect(result.length).toBeGreaterThan(0);
    expect(result).toContain("1");
  });

  it("itemCount returns a non-empty string containing the count (plural)", () => {
    const result = no.itemCount(5);
    expect(typeof result).toBe("string");
    expect(result.length).toBeGreaterThan(0);
    expect(result).toContain("5");
  });

  it("showMore returns a non-empty string containing the count", () => {
    const result = no.showMore(7);
    expect(typeof result).toBe("string");
    expect(result.length).toBeGreaterThan(0);
    expect(result).toContain("7");
  });

  it("removeFile returns a non-empty string containing the filename", () => {
    const result = no.removeFile("document.pdf");
    expect(typeof result).toBe("string");
    expect(result.length).toBeGreaterThan(0);
    expect(result).toContain("document.pdf");
  });

  it("councilSeconds returns a non-empty string containing the number", () => {
    const result = no.councilSeconds(60);
    expect(typeof result).toBe("string");
    expect(result.length).toBeGreaterThan(0);
    expect(result).toContain("60");
  });

  it("collectingFrom returns a non-empty string containing the sources", () => {
    const result = no.collectingFrom("Web Search, OTX");
    expect(typeof result).toBe("string");
    expect(result.length).toBeGreaterThan(0);
    expect(result).toContain("Web Search, OTX");
  });

  it("suggestedSourcesText returns a non-empty string containing the sources", () => {
    const result = no.suggestedSourcesText("OTX, Web");
    expect(typeof result).toBe("string");
    expect(result.length).toBeGreaterThan(0);
    expect(result).toContain("OTX, Web");
  });

  it("messageFailed returns a non-empty string containing the message", () => {
    const result = no.messageFailed("timeout");
    expect(typeof result).toBe("string");
    expect(result.length).toBeGreaterThan(0);
    expect(result).toContain("timeout");
  });

  it("approvalFailed returns a non-empty string containing the message", () => {
    const result = no.approvalFailed("network error");
    expect(typeof result).toBe("string");
    expect(result.length).toBeGreaterThan(0);
    expect(result).toContain("network error");
  });

  it("gatherMoreFailed returns a non-empty string containing the message", () => {
    const result = no.gatherMoreFailed("server error");
    expect(typeof result).toBe("string");
    expect(result.length).toBeGreaterThan(0);
    expect(result).toContain("server error");
  });

  it("startCollectionFailed returns a non-empty string containing the message", () => {
    const result = no.startCollectionFailed("connection refused");
    expect(typeof result).toBe("string");
    expect(result.length).toBeGreaterThan(0);
    expect(result).toContain("connection refused");
  });

  it("loadedPreviousRun returns a non-empty string containing the id", () => {
    const result = no.loadedPreviousRun("session-abc-123");
    expect(typeof result).toBe("string");
    expect(result.length).toBeGreaterThan(0);
    expect(result).toContain("session-abc-123");
  });

  it("restorePreviousRunFailed returns a non-empty string containing the message", () => {
    const result = no.restorePreviousRunFailed("not found");
    expect(typeof result).toBe("string");
    expect(result.length).toBeGreaterThan(0);
    expect(result).toContain("not found");
  });

  it("setDevStage returns a non-empty string containing the stage", () => {
    const result = no.setDevStage("collecting");
    expect(typeof result).toBe("string");
    expect(result.length).toBeGreaterThan(0);
    expect(result).toContain("collecting");
  });

  it("syncDevStage returns a non-empty string containing the stage", () => {
    const result = no.syncDevStage("reviewing");
    expect(typeof result).toBe("string");
    expect(result.length).toBeGreaterThan(0);
    expect(result).toContain("reviewing");
  });

  it("councilRoundsChip returns a non-empty string containing the count", () => {
    const result = no.councilRoundsChip(3);
    expect(typeof result).toBe("string");
    expect(result.length).toBeGreaterThan(0);
    expect(result).toContain("3");
  });

  it("councilRoundsSingleChip returns a non-empty string containing the count", () => {
    const result = no.councilRoundsSingleChip(1);
    expect(typeof result).toBe("string");
    expect(result.length).toBeGreaterThan(0);
    expect(result).toContain("1");
  });

  it("councilRoundsMultiChip returns a non-empty string containing the count", () => {
    const result = no.councilRoundsMultiChip(5);
    expect(typeof result).toBe("string");
    expect(result.length).toBeGreaterThan(0);
    expect(result).toContain("5");
  });

  it("councilTimeoutChip returns a non-empty string containing the count", () => {
    const result = no.councilTimeoutChip(30);
    expect(typeof result).toBe("string");
    expect(result.length).toBeGreaterThan(0);
    expect(result).toContain("30");
  });

  it("councilRetryChip returns a non-empty string containing the count", () => {
    const result = no.councilRetryChip(2);
    expect(typeof result).toBe("string");
    expect(result.length).toBeGreaterThan(0);
    expect(result).toContain("2");
  });

  it("councilConfidence returns a non-empty string containing the percentage", () => {
    const result = no.councilConfidence(85);
    expect(typeof result).toBe("string");
    expect(result.length).toBeGreaterThan(0);
    expect(result).toContain("85");
  });

  it("councilRound returns a non-empty string containing the round number", () => {
    const result = no.councilRound(2);
    expect(typeof result).toBe("string");
    expect(result.length).toBeGreaterThan(0);
    expect(result).toContain("2");
  });

  it("councilTranscriptPath returns a non-empty string containing the path", () => {
    const result = no.councilTranscriptPath("/logs/session.json");
    expect(typeof result).toBe("string");
    expect(result.length).toBeGreaterThan(0);
    expect(result).toContain("/logs/session.json");
  });
});

describe("no translation — shape parity with en", () => {
  it("has all the same keys as the English translation", () => {
    const enKeys = Object.keys(en).sort();
    const noKeys = Object.keys(no).sort();
    expect(noKeys).toEqual(enKeys);
  });
});
