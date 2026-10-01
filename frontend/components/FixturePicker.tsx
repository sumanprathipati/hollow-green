import type { DemoReleaseMeta } from "@/lib/types";

interface Props {
  metas: DemoReleaseMeta[];
  selectedId: string | null;
  disabled: boolean;
  onChange: (id: string) => void;
}

export default function FixturePicker({ metas, selectedId, disabled, onChange }: Props) {
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor="fixture-select" className="text-sm font-medium">
        Demo release
      </label>
      <select
        id="fixture-select"
        className="rounded border border-zinc-300 bg-white px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900"
        value={selectedId ?? ""}
        disabled={disabled || metas.length === 0}
        onChange={(e) => onChange(e.target.value)}
      >
        <option value="">Select a demo release</option>
        {metas.map((m) => (
          <option key={m.release_id} value={m.release_id}>
            {m.display_name} — {m.classification_hint}
          </option>
        ))}
      </select>
    </div>
  );
}
