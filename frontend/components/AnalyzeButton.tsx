interface Props {
  disabled: boolean;
  loading: boolean;
  onClick: () => void;
}

export default function AnalyzeButton({ disabled, loading, onClick }: Props) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className="rounded-md bg-slate-100 px-5 py-2.5 text-sm font-semibold text-slate-900 disabled:opacity-50 hover:bg-white"
    >
      {loading ? "Analyzing…" : "Analyze release"}
    </button>
  );
}
