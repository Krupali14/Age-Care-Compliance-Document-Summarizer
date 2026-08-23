interface ConfirmModalProps {
  title: string;
  message: string;
  confirmLabel?: string;
  onConfirm: () => void;
  onCancel: () => void;
}

export default function ConfirmModal({
  title,
  message,
  confirmLabel = "Confirm",
  onConfirm,
  onCancel,
}: ConfirmModalProps) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-ink/50 px-4 backdrop-blur-sm animate-fade-up"
      style={{ animationDuration: "0.15s" }}
      onClick={onCancel}
    >
      <div
        className="w-full max-w-sm rounded-xl border border-ink/10 bg-white p-6 shadow-stack animate-fade-up"
        style={{ animationDuration: "0.2s" }}
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="font-display text-lg font-semibold text-ink">{title}</h2>
        <p className="mt-2 text-sm text-slate-500">{message}</p>
        <div className="mt-6 flex justify-end gap-3">
          <button
            onClick={onCancel}
            className="rounded-md px-4 py-2 text-sm font-medium text-slate-500 transition hover:bg-parchment-200"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            className="rounded-md bg-coral px-4 py-2 text-sm font-semibold text-white transition hover:bg-coral/90"
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
