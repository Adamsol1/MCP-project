import { useContext } from "react";
import { WorkspaceContext } from "../../contexts/WorkspaceContext/WorkspaceContext";

/**
 * Custom React hook that provides access to the workspace context, which includes state and functions related to the analysis workspace such as highlighted references, PIR data, collection data, and review activity. This hook ensures that it is used within a WorkspaceProvider and throws an error if it is accessed outside of the provider context.
 * @returns The value of the workspace context, including state and updater functions for highlighted references, PIR data, collection data, and review activity. This allows components to access and manipulate workspace-related state in a consistent manner across the application.
 * @throws An error if the hook is used outside of a WorkspaceProvider, ensuring that components have the necessary context to function properly.
 */
export function useWorkspace() {
  const context = useContext(WorkspaceContext);
  if (!context) {
    throw new Error("useWorkspace must be used within a WorkspaceProvider");
  }
  return context;
}
