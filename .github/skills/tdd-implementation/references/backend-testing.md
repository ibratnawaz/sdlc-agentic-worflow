# Backend testing patterns (Spring Boot)

Match the repo's existing style (JUnit 5, AssertJ/Hamcrest, Mockito, Testcontainers if already present).

| What you're proving | Test type | Typical setup |
|---|---|---|
| Business rule in a service | Unit | `@ExtendWith(MockitoExtension.class)`, mock the repository/clients |
| HTTP contract: status, validation, JSON shape | Slice | `@WebMvcTest(XController.class)` + `MockMvc`, `@MockBean` the service |
| Query / mapping / transaction | Integration | `@DataJpaTest` or `@SpringBootTest` (+ Testcontainers if used) |

```java
@Test
void shouldReturn400WhenAmountIsNegative() throws Exception {
    mockMvc.perform(post("/api/transfers")
            .contentType(APPLICATION_JSON)
            .content("""
                {"amount": -5, "toAccountId": "A1"}
                """))
        .andExpect(status().isBadRequest())
        .andExpect(jsonPath("$.errors[0].field").value("amount"));
    verifyNoInteractions(transferService);   // bad input never reaches the service
}
```

Bad paths to consider for every endpoint: invalid/missing input (400), not found (404), not allowed (403),
conflict/duplicate (409), downstream timeout/failure (graceful error, no stack trace), and no PII in logs.
