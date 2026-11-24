---
applyTo: "**/*.java"
---

# Spring Boot conventions

<!-- Loaded only when Copilot works on Java files. Replace the examples with your team's real rules. -->

- Layers: `controller` → `service` → `repository`. Controllers hold no business logic; repositories hold no business rules.
- Constructor injection only (no field `@Autowired`).
- Request/response DTOs are separate from JPA entities; validate input with Bean Validation (`@Valid`, `@NotNull`…).
- Errors go through the shared `@ControllerAdvice`; never return stack traces to clients.
- Use the project's structured logger. Never log request bodies, account numbers or other PII.
- Config and secrets come from properties / the secrets manager, never literals.

## Tests
- Unit: JUnit 5 + Mockito for services.
- Slice: `@WebMvcTest` + MockMvc for controllers (status codes, validation errors, JSON shape).
- Integration: `@SpringBootTest` (and Testcontainers if the repo already uses it) for repository/DB behaviour.
- Name tests by behaviour: `shouldReturn404WhenAccountMissing()`.
