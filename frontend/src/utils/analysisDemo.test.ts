import { describe, expect, it } from "vitest";
import type { Conversation } from "../types/conversation";
import { canReuseConversationForAnalysisDemo } from "./analysisDemo";

function makeConversation(
  overrides: Partial<Conversation> = {},
): Conversation {
  return {
    id: "conv-1",
    title: "New conversation",
    messages: [],
    perspectives: ["NEUTRAL"],
    sessionId: "session-1",
    isConfirming: false,
    stage: "initial",
    subState: null,
    createdAt: 1000,
    updatedAt: 1000,
    ...overrides,
  };
}

describe("canReuseConversationForAnalysisDemo", () => {
  it("returns true for an empty new conversation", () => {
    expect(canReuseConversationForAnalysisDemo(makeConversation())).toBe(true);
  });

  it("returns false after the conversation has content", () => {
    expect(
      canReuseConversationForAnalysisDemo(
        makeConversation({
          messages: [{ id: "m1", text: "hello", sender: "user" }],
        }),
      ),
    ).toBe(false);
  });

  it("returns false for renamed or progressed conversations", () => {
    expect(
      canReuseConversationForAnalysisDemo(
        makeConversation({ title: "Existing work" }),
      ),
    ).toBe(false);
    expect(
      canReuseConversationForAnalysisDemo(
        makeConversation({ stage: "gathering" }),
      ),
    ).toBe(false);
  });
});
