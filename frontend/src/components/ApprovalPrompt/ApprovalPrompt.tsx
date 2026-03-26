import type { DialogueStage } from "../../types/dialogue";
import { useT } from "../../i18n/useT";

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

export default function ApprovalPrompt({
  onApproveContinue,
  onRejectWithFeedback,
  isLoading = false,
  stage,
}: ApprovalPromptProps) {
  const t = useT();

  const DEFAULT_PROMPT_COPY: PromptCopy = {
    title: t.approvalDefault,
    subtitle: t.approvalDefaultSubtitle,
  };

  const PROMPT_COPY_BY_STAGE: Partial<Record<DialogueStage, PromptCopy>> = {
    summary_confirming: {
      title: t.approvalSummary,
      subtitle: t.approvalSummarySubtitle,
    },
    pir_confirming: {
      title: t.approvalPir,
      subtitle: t.approvalPirSubtitle,
    },
    plan_confirming: {
      title: t.approvalPlan,
      subtitle: t.approvalPlanSubtitle,
    },
  };

  const promptCopy = stage
    ? (PROMPT_COPY_BY_STAGE[stage] ?? DEFAULT_PROMPT_COPY)
    : DEFAULT_PROMPT_COPY;

  const canApprove = !isLoading;
  const canReject = !isLoading;

  return (
    <section className="rounded-lg border border-border bg-surface p-4 flex items-center gap-4">
      <div className="flex-1 min-w-0">
        <h3 className="text-sm font-semibold text-text-primary">{promptCopy.title}</h3>
        <p className="text-sm text-text-secondary">{promptCopy.subtitle}</p>
      </div>

      <div className="shrink-0 flex items-center gap-2">
        <button
          type="button"
          onClick={() => onApproveContinue?.()}
          disabled={!canApprove}
          className="rounded-md bg-success px-4 py-2 text-sm font-medium text-text-inverse hover:bg-success-dark disabled:cursor-not-allowed disabled:opacity-50"
        >
          {t.approveContinue}
        </button>

        <button
          type="button"
          onClick={() => onRejectWithFeedback?.()}
          disabled={!canReject}
          className="rounded-md bg-error px-4 py-2 text-sm font-medium text-text-inverse hover:bg-error-dark disabled:cursor-not-allowed disabled:opacity-50"
        >
          {t.rejectWithFeedback}
        </button>
      </div>
    </section>
  );
}
