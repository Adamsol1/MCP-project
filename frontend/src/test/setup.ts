import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import * as axeMatchers from "vitest-axe/matchers";
import { expect } from "vitest";
expect.extend(axeMatchers);

// jsdom does not implement scrollIntoView — stub it globally so components
// that call messagesEndRef.current?.scrollIntoView() don't throw in tests.
window.HTMLElement.prototype.scrollIntoView = function () {};

// jsdom does not implement ResizeObserver — stub it globally so components
// that use ResizeObserver (e.g. ChatWindow bottom panel tracking) don't throw.
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
window.ResizeObserver = ResizeObserverStub as unknown as typeof ResizeObserver;

afterEach(() => {
  cleanup();
});
