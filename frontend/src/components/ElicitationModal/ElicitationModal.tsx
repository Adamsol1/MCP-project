import type { PendingElicitation } from "../../services/dialogue/dialogue";

const LOCAL_LLM_OPTION = "Bytt til lokal LLM";

interface ElicitationModalProps {
  elicitation: PendingElicitation;
  onRespond: (choice: string) => void;
}

export default function ElicitationModal({ elicitation, onRespond }: ElicitationModalProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-surface border border-border rounded-lg shadow-xl p-6 max-w-md w-full mx-4">
        <p className="text-sm font-semibold text-text-primary mb-1">
          Klassifisert innhold oppdaget
        </p>
        <p className="text-sm text-text-secondary mb-5">
          {elicitation.message}
        </p>
        <div className="flex flex-wrap gap-2 justify-end">
          {elicitation.options.map((option) => {
            const isLocalLlm = option === LOCAL_LLM_OPTION;
            return (
              <div key={option} className="relative group">
                <button
                  type="button"
                  onClick={() => !isLocalLlm && onRespond(option)}
                  disabled={isLocalLlm}
                  className={`rounded-md px-4 py-2 text-sm font-medium transition-colors ${
                    isLocalLlm
                      ? "bg-surface-elevated text-text-muted border border-border cursor-not-allowed opacity-50"
                      : "bg-primary text-text-inverse hover:bg-primary-dark"
                  }`}
                >
                  {option}
                </button>
                {isLocalLlm && (
                  <div className="absolute bottom-full mb-1 left-1/2 -translate-x-1/2 hidden group-hover:block w-48 rounded bg-surface-elevated border border-border p-2 text-xs text-text-muted text-center shadow-lg">
                    Ikke tilgjengelig i denne versjonen
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
