# docs/screenshots capture checklist

Real screenshots only — never fabricate, mock up, or commit failure-shot
artifacts. Capture against the local app (backend + `npm run dev`), then
verify each image by viewing it before keeping it.

- [ ] `demo-decision-hero.png`: Demo scenarios, fragile fixture analyzed,
  decision hero visible.
- [ ] `public-evidence-view.png`: Public GitHub evidence assessed, hero +
  evidence completeness visible.
- [ ] `ai-unavailable-state.png`: AI review Generate clicked with no provider
  configured, safe unavailable message visible.
- [ ] `ai-evidence-review.png`: cited AI review rendered (requires a
  configured provider or the documented E2E test provider locally).
- [ ] `ai-blocked-state.png`: blocked message with no rejected text visible.

Rules: no secrets, tokens, or private data in frame; keep images small;
reference kept images from the README "Screenshots and demo" section.
