# Review: Spring Boot specifics

Used by the `code-review` skill on top of the generic checklist. Compare against the closest existing feature in the repo.

## Architecture
- Layers respected: `controller` → `service` → `repository`. No business logic in controllers, and no business rules in repositories.
- DTOs on the API, never JPA entities. Input validated with Bean Validation (`@Valid`, `@NotNull`, …).
- Constructor injection only (no field `@Autowired`).
- Errors mapped in the shared `@ControllerAdvice`. No stack traces or internal messages returned to clients.

## Spring pitfalls
- `@Transactional` sits on the service method that needs it (not on the controller), with the right read-only flag.
- No N+1 queries introduced (check new `@OneToMany` access in loops).
- Config and secrets come from properties / the secrets manager, never literals.
- Logging uses the structured logger. No request bodies, account numbers or other PII.

## Tests
- Controller slice tests (`@WebMvcTest`) cover status codes, validation errors and JSON shape for every new endpoint.
- Service unit tests cover business rules, including failure paths (downstream timeout, not found, forbidden).
- Integration tests only where DB/transaction behaviour matters, and they use the repo's existing setup (e.g. Testcontainers).
