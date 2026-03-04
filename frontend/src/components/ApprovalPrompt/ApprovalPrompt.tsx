import { useState } from "react";
import type { ReactNode } from "react";
import type { DialogueStage } from "../../types/dialogue";

interface RejectPayload {
  keepPartialResults: boolean;
}

interface ApprovalPromptProps {
  /** Called when the user approves and continues. */
  onApproveContinue?: () => void;
  /** Called when the user rejects with structured feedback. */
  onRejectWithFeedback?: (payload: RejectPayload) => void;
  /** Disables all interactive controls while requests are in flight. */
  isLoading?: boolean;
  /** Current backend dialogue stage used to tailor prompt copy. */
  stage?: DialogueStage;
  /** Optional data preview content shown in a scrollable panel. */
  reviewContent?: ReactNode;
}

interface PromptCopy {
  title: string;
  subtitle: string;
  defaultReviewText: string;
}

const DEFAULT_PROMPT_COPY: PromptCopy = {
  title: "Approval Prompt",
  subtitle: "Review the generated output before continuing.",
  defaultReviewText:
    "Review the generated output below before confirming approval.",
};

const PROMPT_COPY_BY_STAGE: Partial<Record<DialogueStage, PromptCopy>> = {
  summary_confirming: {
    title: "Summary Approval Prompt",
    subtitle: "Review the generated summary before continuing to PIR.",
    defaultReviewText:
      "Review the generated summary below before approving PIR generation.",
  },
  pir_confirming: {
    title: "PIR Approval Prompt",
    subtitle: "Review the generated PIR before completing Direction.",
    defaultReviewText:
      "Review the generated PIR below before approving Direction completion.",
  },
};

export default function ApprovalPrompt({
  onApproveContinue,
  onRejectWithFeedback,
  isLoading = false,
  stage,
  reviewContent,
}: ApprovalPromptProps) {
  const [keepPartialResults, setKeepPartialResults] = useState(false);
  const promptCopy = stage
    ? (PROMPT_COPY_BY_STAGE[stage] ?? DEFAULT_PROMPT_COPY)
    : DEFAULT_PROMPT_COPY;

  const handleReject = () => {
    onRejectWithFeedback?.({
      keepPartialResults,
    });
  };

  const canApprove = !isLoading;
  const canReject = !isLoading;

  return (
    <section className="rounded-xl border-2 border-gray-300 bg-white p-4">
      <h3 className="text-lg font-semibold text-gray-800">{promptCopy.title}</h3>
      <p className="mt-1 text-sm text-gray-600">{promptCopy.subtitle}</p>

      <div
        className="mt-4 max-h-40 overflow-y-auto rounded-lg border border-gray-200 bg-gray-50 p-3 text-sm text-gray-700"
      >
        {reviewContent ?? <p>{promptCopy.defaultReviewText}</p>}
      </div>

      <p className="mt-4 text-sm text-gray-600">
        If you reject, you can provide feedback in the chat input after this
        panel closes.
      </p>

      <label className="mt-3 inline-flex items-center gap-2 text-sm text-gray-700">
        <input
          type="checkbox"
          checked={keepPartialResults}
          onChange={(event) => setKeepPartialResults(event.target.checked)}
          disabled={isLoading}
        />
        Keep partial results
      </label>

      <div className="mt-4 flex items-center gap-3">
        <button
          type="button"
          onClick={() => onApproveContinue?.()}
          disabled={!canApprove}
          className="rounded-lg bg-green-600 px-4 py-2 text-white hover:bg-green-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          Approve & Continue
        </button>

        <button
          type="button"
          onClick={handleReject}
          disabled={!canReject}
          className="rounded-lg bg-red-600 px-4 py-2 text-white hover:bg-red-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          Reject with Feedback
        </button>
      </div>
    </section>
  );
}
