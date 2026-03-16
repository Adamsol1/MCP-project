import type { DialogueStage } from "../../types/dialogue";

interface ApprovalPromptProps {
  /** Called when the user approves and continues. */
  onApproveContinue?: () => void;
  /** Called when the user rejects and wants to provide feedback in chat. */
  onRejectWithFeedback?: () => void;
  /** Disables all interactive controls while requests are in flight. */
  isLoading?: boolean;
  /** Current backend dialogue stage used to tailor prompt copy. */
  stage?: DialogueStage;
}

interface PromptCopy {
  title: string;
  subtitle: string;
}

const DEFAULT_PROMPT_COPY: PromptCopy = {
  title: "Approval Prompt",
  subtitle: "Review the generated output before continuing.",
};

const PROMPT_COPY_BY_STAGE: Partial<Record<DialogueStage, PromptCopy>> = {
  summary_confirming: {
    title: "Summary Approval Prompt",
    subtitle: "Review the generated summary before continuing to PIR.",
  },
  pir_confirming: {
    title: "PIR Approval Prompt",
    subtitle: "Review the generated PIR before completing Direction.",
  },
  plan_confirming: {
    title: "Collection Plan Approval Prompt",
    subtitle: "Review the generated collection plan before selecting sources.",
  },
};

export default function ApprovalPrompt({
  onApproveContinue,
  onRejectWithFeedback,
  isLoading = false,
  stage,
}: ApprovalPromptProps) {
  const promptCopy = stage
    ? (PROMPT_COPY_BY_STAGE[stage] ?? DEFAULT_PROMPT_COPY)
    : DEFAULT_PROMPT_COPY;

  const canApprove = !isLoading;
  const canReject = !isLoading;

  return (
    <section className="rounded-xl border-2 border-gray-300 bg-white p-4">
      <h3 className="text-lg font-semibold text-gray-800">{promptCopy.title}</h3>
      <p className="mt-1 text-sm text-gray-600">{promptCopy.subtitle}</p>

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
          onClick={() => onRejectWithFeedback?.()}
          disabled={!canReject}
          className="rounded-lg bg-red-600 px-4 py-2 text-white hover:bg-red-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          Reject with Feedback
        </button>
      </div>
    </section>
  );
}
