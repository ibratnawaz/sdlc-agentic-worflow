# Review checklist

## Correctness vs ACs
- Every AC implemented; every AC has a good-path **and** bad-path test that would fail without the code
- Behaviour matches the approved plan; deviations are explained in `04-implementation.md`
- No scope creep (unrelated refactors, extra features)

## Tests
- Tests assert behaviour, not implementation details (FE: by role/label; BE: by HTTP contract/result)
- No skipped/disabled tests, no weakened assertions, no sleeping/timing hacks
- New routes/endpoints: success, validation error, not found, forbidden, downstream failure covered

## Architecture (compare with the closest existing feature)
- FE: components presentational, data access in hooks/services, design-system components and tokens reused, no literal colours/spacing
- BE: controller → service → repository respected; DTOs not entities on the API; constructor injection; errors via `@ControllerAdvice`
- Naming, folder placement and patterns consistent with the repo

## Security and privacy (financial services)
- Input validated at the boundary; authorisation checked server-side
- No secrets, tokens, internal URLs or account numbers in code, tests, fixtures or logs
- No PII in logs or error messages; no stack traces returned to clients
- New dependencies justified and approved

## Accessibility (FE)
- `.github/skills/tdd-implementation/references/accessibility-checklist.md`, every item, for every new or changed interactive element

## Operability
- Errors handled, not swallowed; useful structured logs without PII
- API docs/contracts updated if shapes changed
