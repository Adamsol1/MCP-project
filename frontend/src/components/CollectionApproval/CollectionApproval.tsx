import { useEffect, useState } from "react";
import type { ReactNode, UIEvent } from "react";

interface RejectPayload {
  keepPartialResults: boolean;
}

interface CollectionApprovalProps {
  /** Called after the user confirms approval. */
  onApproveContinue?: () => void;
  /** Called when the user rejects with structured feedback. */
  onRejectWithFeedback?: (payload: RejectPayload) => void;
  /** Disables all interactive controls while requests are in flight. */
  isLoading?: boolean;
  /** Minimum dwell time required before actions unlock. */
  minReviewSeconds?: number;
  /** Optional data preview content shown in a scrollable panel. */
  reviewContent?: ReactNode;
}

const DEFAULT_REVIEW_TEXT =
  "Review the collected intelligence below before approving the transition to Processing.";

export default function CollectionApproval({
  onApproveContinue,
  onRejectWithFeedback,
  isLoading = false,
  minReviewSeconds = 10,
  reviewContent,
}: CollectionApprovalProps) {
  const [hasReviewed, setHasReviewed] = useState(false);
  const [keepPartialResults, setKeepPartialResults] = useState(false);
  const [isApproveDialogOpen, setIsApproveDialogOpen] = useState(false);

  useEffect(() => {
    if (minReviewSeconds <= 0) {
      setHasReviewed(true);
      return;
    }

    const timer = window.setTimeout(() => {
      setHasReviewed(true);
    }, minReviewSeconds * 1000);

    return () => window.clearTimeout(timer);
  }, [minReviewSeconds]);

  const handleReviewScroll = (event: UIEvent<HTMLDivElement>) => {
    const panel = event.currentTarget;
    const reachedBottom =
      panel.scrollTop + panel.clientHeight >= panel.scrollHeight - 1;

    if (reachedBottom) {
      setHasReviewed(true);
    }
  };

  const handleReject = () => {
    onRejectWithFeedback?.({
      keepPartialResults,
    });
  };

  const canApprove = hasReviewed && !isLoading;
  const canReject = hasReviewed && !isLoading;

  return (
    <section className="rounded-xl border-2 border-gray-300 bg-white p-4">
      <h3 className="text-lg font-semibold text-gray-800">Collection Review</h3>
      <p className="mt-1 text-sm text-gray-600">
        Review all collected data before continuing to Processing.
      </p>

      <div
        data-testid="collection-review-panel"
        onScroll={handleReviewScroll}
        className="mt-4 max-h-40 overflow-y-auto rounded-lg border border-gray-200 bg-gray-50 p-3 text-sm text-gray-700"
      >
        {reviewContent ?? <p>{DEFAULT_REVIEW_TEXT}</p>}
      </div>

      {!hasReviewed && (
        <p className="mt-2 text-xs text-gray-500">
          Actions unlock after you scroll to the bottom or spend 10 seconds here.
        </p>
      )}

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
          onClick={() => setIsApproveDialogOpen(true)}
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

      {isApproveDialogOpen && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label="Confirm approval"
          className="mt-4 rounded-lg border border-gray-300 bg-gray-50 p-4"
        >
          <p className="text-sm text-gray-700">
            Confirm that you want to accept this collection result and continue.
          </p>
          <div className="mt-3 flex items-center gap-2">
            <button
              type="button"
              onClick={() => setIsApproveDialogOpen(false)}
              className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-700 hover:bg-gray-100"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={() => {
                setIsApproveDialogOpen(false);
                onApproveContinue?.();
              }}
              className="rounded-lg bg-green-600 px-3 py-2 text-sm text-white hover:bg-green-700"
            >
              Confirm Approve
            </button>
          </div>
        </div>
      )}
    </section>
  );
}
