export default function ReserveMeter({ reserve, load }: { reserve: number; load: string }) {
  return (
    <section aria-label="Reserve Level meter" className="rounded border p-3">
      <h2 className="text-sm font-medium">Reserve Level</h2>
      <div
        role="progressbar"
        aria-valuenow={reserve}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label="Reserve Level"
        className="mt-2 h-3 w-full overflow-hidden rounded bg-zinc-200 dark:bg-zinc-800"
      >
        <div className="h-full bg-zinc-900 dark:bg-zinc-100" style={{ width: `${reserve}%` }} />
      </div>
      <p className="mt-2 text-sm">
        Reserve Level {reserve} / 100 — {load}
      </p>
    </section>
  );
}
