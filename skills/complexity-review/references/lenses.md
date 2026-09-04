# Complexity Review Lenses

Three lenses for reviewing PR changes. Apply each to every changed file. When a signal appears, verify it against the false-positive guards before raising a finding.

## 1. Unnecessary Complexity

Code harder to understand than the problem demands.

### Signals

- **Deep nesting:** 3+ levels of conditionals or loops where flattening (early returns, extraction) is straightforward.
- **Excessive indirection:** Call chains through multiple layers to reach simple logic. A function that delegates to a function that delegates to a function that does one thing.
- **Single-implementation abstractions:** Interfaces, abstract classes, or strategy patterns with exactly one concrete implementation.
- **Unnecessary generics:** Type parameters, parameterization, or configuration solving a single concrete case.
- **Dead configuration:** Configuration-driven behavior where the configuration never varies in practice.

### False-Positive Guards

- An abstraction with one implementation is acceptable when a second is planned and referenced in a ticket or the PR description.
- Deep nesting may be justified by genuinely complex domain logic (e.g. state machines, protocol parsing). If flattening would obscure the logic, it is not a finding.
- Indirection for dependency injection at I/O boundaries is standard practice, not excessive indirection.

## 2. Brittle Tests

Tests that break on implementation changes rather than behavior changes.

### Signals

- **Over-mocking:** Mocking classes, functions, or modules owned by the same codebase rather than external dependencies. The test knows too much about internal wiring.
- **Testing internals:** Assertions against private methods, internal state, or implementation-specific data structures rather than observable behavior.
- **Volatile snapshots:** Snapshot tests on output that changes with timestamps, random IDs, environment state, or formatting.
- **Implementation-coupled values:** Hardcoded expected values derived from how the code works rather than what it should produce. Changing an internal algorithm breaks the test even though the behavior is correct.
- **Setup-heavy tests:** Test setup that is 10x the assertion. The reader cannot tell what is being tested.

### False-Positive Guards

- Mocking external services, databases, file systems, and network I/O is correct - these are boundaries you do not own.
- Some implementation-aware tests are justified for performance-critical paths where the implementation IS the behavior (e.g. verifying an O(n) algorithm is not replaced with O(n^2)).
- Large setup is acceptable in integration tests that exercise a real subsystem.

## 3. Overengineering

Building for requirements that do not exist.

### Signals

- **Speculative features:** Code behind feature flags that are never toggled, or optional parameters that are never exercised.
- **One-consumer patterns:** Plugin systems with one plugin, event buses with one subscriber, factory patterns producing one type, registry patterns with one entry.
- **Premature optimization:** Performance optimization without profiling evidence or documented performance requirements. Caching layers, object pools, or custom data structures where the standard library suffices.
- **Framework-level abstractions:** Building reusable frameworks, SDKs, or libraries when the code serves one application-level use case.
- **Dead extension points:** Hook methods, callback registries, or middleware chains with a single user.

### False-Positive Guards

- Extension points are acceptable when a concrete near-term use case is documented (in a ticket, PR description, or code comment with a ticket reference).
- Performance-sensitive paths (hot loops, latency-critical endpoints) may justify optimization even without profiling, provided the performance requirement is documented.
- Patterns mandated by the framework or platform (e.g. a DI container requiring an interface) are not overengineering.
