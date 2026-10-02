# Security notes

## Threat model

Hollow Green analyzes two kinds of input:

1. **Synthetic demo fixtures** checked into the repo. Trusted, deterministic.
2. **Public GitHub data** (repository metadata, commit messages, PR titles,
   issue titles). This text is written by untrusted third parties and must be
   treated as **untrusted reference data, never as instructions**.

The AI evidence review (Stage 7) sends a small normalized evidence bundle to a
configured language-model provider. The risks addressed here are:

- **Prompt injection**: hostile commit messages, PR/issue titles, or release
  names that try to override instructions, claim approvals, alter the risk
  assessment, impersonate system messages, or smuggle fake sources/links.
- **Ungrounded output**: model text that invents metrics, dates, URLs, or
  deployment claims.
- **Secret exposure**: provider keys or GitHub tokens leaking to the browser,
  logs, or responses.

## Defenses (layered)

1. **Sanitization before the bundle** (`sanitize_evidence_text`): control
   characters stripped, URL-like tokens removed (links render only from
   structured source fields), angle brackets removed, `[En]`-style tokens
   defused, whitespace collapsed, deterministic length caps.
2. **Delimited untrusted-data blocks**: every evidence record travels inside
   `<<<EVIDENCE <id> BEGIN>>>` / `<<<id EVIDENCE>>>` markers that sanitized
   text cannot produce. The system instruction states that block contents are
   untrusted and any instructions inside must be ignored, never followed.
3. **No tool access**: the provider call sends only `messages` (no `tools`,
   `functions`, or browsing). The model cannot call GitHub or fetch URLs.
4. **Strict output validation** (`validate_review_output`): fixed 4-section
   JSON shape, bullet/word caps, mandatory citations from the bundle's source
   map, URL/HTML/Markdown rejection, forbidden deployment/demo vocabulary
   scan, deterministic-consistency check, and supported-facts check for dates,
   commit references, `#N` references, counts, and repository names. Failures
   return `blocked` without the rejected text.
5. **Backend-only secrets**: `GITHUB_TOKEN` and `AI_REVIEW_*` live only in
   server environment, documented as placeholders in `.env.example`, never in
   `NEXT_PUBLIC_*`, responses, logs, or the browser bundle.
6. **Human review**: the UI labels AI output as explanatory assistance, shows
   the deterministic assessment as the source of truth, and renders only
   validated citation links.

## Hostile evidence policy

Hostile strings may legitimately appear **quoted as source data** (for
example an issue title shown in the evidence list or an audit view). They must
never appear as generated claims. The test suite pins this: the hostile
fixture's wording is visible in assessment evidence but absent from every
accepted review response.

## Known limitations

- No prompt-injection defense is perfect. A sufficiently clever model output
  could paraphrase around keyword guards; the typed citation/source validation
  and human review are the backstops, not the keyword list.
- The validator checks that cited IDs exist and that facts are supported, but
  it does not judge whether a citation is *relevant* to its bullet.
- The test-only provider (`E2E_TEST_MODE=1` plus an explicit `test_provider`
  query value) is a deliberately narrow testing hook: it is unreachable in
  normal runs, has no UI control, and is documented in the README as
  test-only. Treat any widening of that hook as a security-relevant change.
