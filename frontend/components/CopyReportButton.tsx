"use client";

import { useState } from "react";

async function copyText(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    try {
      const ta = document.createElement("textarea");
      ta.value = text;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
      return true;
    } catch {
      return false;
    }
  }
}

export default function CopyReportButton({ briefText }: { briefText: string }) {
  const [copied, setCopied] = useState(false);
  const [failed, setFailed] = useState(false);

  async function onCopy() {
    const ok = await copyText(briefText);
    setCopied(ok);
    setFailed(!ok);
  }

  return (
    <div className="flex items-center gap-2">
      <button
        type="button"
        onClick={onCopy}
        className="rounded-md border border-slate-700 px-3 py-1.5 text-sm font-medium text-slate-200 hover:bg-slate-800"
        aria-live="polite"
      >
        Copy decision brief
      </button>
      {copied ? <span className="text-sm text-emerald-300">Copied</span> : null}
      {failed ? <span className="text-sm text-red-300">Copy failed</span> : null}
    </div>
  );
}
