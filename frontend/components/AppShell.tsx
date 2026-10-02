import type { ReactNode } from "react";

export default function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <header className="border-b border-slate-800 bg-slate-900">
        <div className="mx-auto flex w-full max-w-6xl flex-col gap-2 px-4 py-4 md:flex-row md:items-center md:justify-between md:px-6">
          <div>
            <p className="text-xs font-semibold uppercase tracking-widest text-slate-400">
              Hollow Green
            </p>
            <h1 className="text-xl font-semibold text-slate-50">
              Release Confidence Command Center
            </h1>
            <p className="mt-1 text-sm text-slate-300">
              Should this release proceed? Scores are computed in Python; this console only
              displays backend results.
            </p>
          </div>
          <span className="inline-flex w-fit items-center gap-2 rounded-full border border-amber-300/40 bg-amber-400/10 px-3 py-1 text-xs font-medium text-amber-200">
            <span aria-hidden="true">●</span> Synthetic demo environment
          </span>
        </div>
      </header>
      <main className="mx-auto w-full max-w-6xl px-4 py-6 md:px-6">{children}</main>
      <footer className="border-t border-slate-800">
        <p className="mx-auto w-full max-w-6xl px-4 py-4 text-xs text-slate-400 md:px-6">
          Synthetic demo data only. No real releases. Reserve Level is the only numeric score;
          Recovery Load is derived from it.
        </p>
      </footer>
    </div>
  );
}
