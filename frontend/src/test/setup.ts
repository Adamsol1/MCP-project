import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";

// jsdom does not implement scrollIntoView — stub it globally so components
// that call messagesEndRef.current?.scrollIntoView() don't throw in tests.
window.HTMLElement.prototype.scrollIntoView = function () {};

afterEach(() => {
  cleanup();
});
