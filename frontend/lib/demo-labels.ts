import type { DemoReleaseMeta } from "@/lib/types";

export function demoLabel(meta: DemoReleaseMeta): string {
  return `${meta.display_name} — ${meta.classification_hint}`;
}

export function groupByHint(metas: DemoReleaseMeta[]): Record<string, DemoReleaseMeta[]> {
  const groups: Record<string, DemoReleaseMeta[]> = {};
  for (const m of metas) {
    const key = m.classification_hint;
    if (!groups[key]) groups[key] = [];
    groups[key].push(m);
  }
  return groups;
}
