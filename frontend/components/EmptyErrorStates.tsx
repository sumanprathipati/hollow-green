export function EmptyState({ message }: { message: string }) {
  return (
    <div className="rounded-lg border border-dashed border-slate-700 bg-slate-900 p-6 text-center">
      <p className="text-sm font-medium text-slate-100">No analysis yet</p>
      <p className="mt-1 text-sm text-slate-300">{message}</p>
    </div>
  );
}

export function ErrorState({
  title,
  message,
  detail,
  onRetry,
  retryLabel,
}: {
  title: string;
  message: string;
  detail?: string;
  onRetry?: () => void;
  retryLabel?: string;
}) {
  return (
    <div role="alert" className="rounded-lg border border-red-300/40 bg-red-400/10 p-4">
      <p className="text-sm font-semibold text-red-100">{title}</p>
      <p className="mt-1 text-sm text-red-100/90">{message}</p>
      {detail ? (
        <pre className="mt-2 max-h-48 overflow-auto whitespace-pre-wrap rounded bg-slate-950 p-2 text-xs text-slate-200">
          {detail}
        </pre>
      ) : null}
      {onRetry ? (
        <button
          type="button"
          onClick={onRetry}
          className="mt-3 rounded border border-red-200/40 px-3 py-1.5 text-sm font-medium text-red-100 hover:bg-red-400/20"
        >
          {retryLabel ?? "Retry"}
        </button>
      ) : null}
    </div>
  );
}
