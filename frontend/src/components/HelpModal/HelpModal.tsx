interface HelpSection {
  heading?: string;
  body: string;
}

interface HelpModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  sections: HelpSection[];
}

export function HelpModal({ isOpen, onClose, title, sections }: HelpModalProps) {
  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        className="flex w-full max-w-2xl flex-col overflow-hidden rounded-xl border border-border bg-surface shadow-2xl max-h-[85vh]"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="sticky top-0 flex shrink-0 items-center justify-between border-b border-border bg-surface px-6 py-4">
          <h2 className="text-base font-semibold text-text-primary">{title}</h2>
          <button
            aria-label="Close help"
            onClick={onClose}
            className="rounded p-1.5 text-text-muted transition-colors hover:bg-surface-elevated hover:text-text-primary"
          >
            ✕
          </button>
        </div>

        <div className="overflow-y-auto px-6 py-5 space-y-5">
          {sections.map((section, i) => (
            <div key={i}>
              {section.heading && (
                <p className="mb-2 text-xs font-bold uppercase tracking-widest text-text-primary">
                  {section.heading}
                </p>
              )}
              <p className="text-sm leading-7 text-text-secondary">{section.body}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

interface HelpButtonProps {
  onClick: () => void;
  label?: string;
}

export function HelpButton({ onClick, label = "Help" }: HelpButtonProps) {
  return (
    <button
      type="button"
      aria-label={label}
      onClick={onClick}
      className="inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full border border-text-muted text-[11px] font-bold text-text-primary transition-colors hover:border-primary hover:bg-primary-subtle hover:text-primary"
    >
      ?
    </button>
  );
}
