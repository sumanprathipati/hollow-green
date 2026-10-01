"use client";

import { useState } from "react";
import type { ReleaseReport } from "@/lib/types";

export default function CopyReportButton({ report }: { report: ReleaseReport }) {
  const [copied, setCopied] = useState(false);
  const [failed, setFailed] = useState(false);

  async function onCopy() {
    const text = JSON.stringify(report, null, 2);
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setFailed(false);
    } catch {
      try {
        const ta = document.createElement("textarea");
        ta.value = text;
        document.body.appendChild(ta);
        ta.select();
        document.execCommand("copy");
        document.body.removeChild(ta);
        setCopied(true);
        setFailed(false);
      } catch {
        setFailed(true);
        setCopied(false);
      }
    }
  }

  return (
    <div>
      <button
        type="button"
        onClick={onCopy}
        className="rounded border px-3 py-1 text-sm"
        aria-live="polite"
      >
        Copy raw JSON report
      </button>
      {copied ? <span className="ml-2 text-sm">Copied</span> : null}
      {failed ? <span className="ml-2 text-sm">Copy failed</span> : null}
    </div>
  );
}
