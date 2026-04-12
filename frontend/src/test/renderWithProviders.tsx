/**
 * Shared render helpers for tests that need context providers.
 *
 * Components that call useSettings() must be rendered inside a SettingsProvider.
 * Import renderWithSettings instead of render from @testing-library/react
 * whenever the component under test (or any of its children) calls useSettings().
 *
 * Usage:
 *   import { renderWithSettings } from "../../test/renderWithProviders";
 *   renderWithSettings(<MyComponent />);
 *
 * For components that also need WorkspaceProvider, just nest it inside:
 *   renderWithSettings(
 *     <WorkspaceProvider>
 *       <MyComponent />
 *     </WorkspaceProvider>
 *   );
 */

import { render, type RenderOptions } from "@testing-library/react";
import { SettingsProvider } from "../contexts/SettingsContext/SettingsContext";
import type { ReactElement, ReactNode } from "react";

function SettingsWrapper({ children }: { children: ReactNode }) {
  return <SettingsProvider>{children}</SettingsProvider>;
}

/**
 * Renders ui inside a SettingsProvider so components that call useSettings()
 * don't throw. All other render options are forwarded unchanged.
 */
export function renderWithSettings(
  ui: ReactElement,
  options?: Omit<RenderOptions, "wrapper">,
) {
  return render(ui, { wrapper: SettingsWrapper, ...options });
}
