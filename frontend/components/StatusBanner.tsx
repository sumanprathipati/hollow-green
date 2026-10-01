interface Props {
  kind: "empty" | "loading" | "error" | "api-unavailable";
  message: string;
  detail?: string;
  onRetry?: () => void;
}

export default function StatusBanner({ kind, message, detail, onRetry }: Props) {
  if (kind === "empty") {
    return <p className="rounded border p-3 text-sm">{message}</p>;
  }
  if (kind === "loading") {
    return (
      <p role="status" aria-live="polite" className="rounded border p-3 text-sm">
        {message}
      </p>
    );
  }
  return (
    <div role="alert" className="rounded border border-red-300 p-3 text-sm">
      <p className="font-medium">{message}</p>
      {detail ? <pre className="mt-2 overflow-auto whitespace-pre-wrap text-xs">{detail}</pre> : null}
      {onRetry ? (
        <button
          type="button"
          onClick={onRetry}
          className="mt-2 rounded border px-3 py-1 text-sm"
        >
          Retry
        </button>
      ) : null}
    </div>
  );
}
