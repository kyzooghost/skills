---
name: unit-test
description: Guidelines for writing and reviewing unit tests. Covers AAA pattern, test naming, determinism, mocking strategies, and reviewer responsibilities. Use when creating or updating *.test.* files, reviewing test PRs, or refactoring tests to improve clarity and coverage.
---

# Unit Testing Guidelines

Best practices for writing and reviewing unit tests. Contains rules covering test structure, naming, determinism, and code review.

Reference: [MetaMask Unit Testing Guidelines](https://github.com/MetaMask/contributor-docs/blob/main/docs/testing/unit-testing.md)

## When to Apply

Reference these guidelines when:

- Writing new unit tests
- Reviewing test code in PRs
- Refactoring existing tests
- Debugging flaky or brittle tests
- Improving test coverage

## Rule Categories by Priority

| Priority | Category        | Impact   | Rule File                    |
| -------- | --------------- | -------- | ---------------------------- |
| 1        | Best Practices  | CRITICAL | `rules/best-practices.md`    |
| 2        | Determinism     | HIGH     | `rules/determinism.md`       |
| 3        | Reviewer Guide  | MEDIUM   | `rules/reviewer-guide.md`    |
| 4        | Anti-patterns   | MEDIUM   | `rules/anti-patterns.md`     |

## Quick Reference

### 1. Best Practices (CRITICAL)

**Use the AAA pattern** (Arrange, Act, Assert):

```ts
it('indicates expired milk when past due date', () => {
  // Arrange
  const today = new Date('2025-06-01');
  const milk = { expiration: new Date('2025-05-30') };

  // Act
  const result = isMilkGood(today, milk);

  // Assert
  expect(result).toBe(false);
});
```

**Meaningful test names** - describe purpose, not implementation:

```ts
it('displays an error when input is invalid', () => { ... });
```

**One behavior per test**, isolated from others.

See [rules/best-practices.md](rules/best-practices.md) for complete guidance.

### 2. Determinism (HIGH)

**Mock time, randomness, and external systems:**

```ts
jest.useFakeTimers();
jest.setSystemTime(new Date('2024-01-01'));
```

- Avoid relying on global state or hardcoded values
- Only test public behavior, not implementation details

See [rules/determinism.md](rules/determinism.md) for details.

### 3. Reviewer Guide (MEDIUM)

**Test the test** - validate tests fail when code is broken:

```ts
// Break the SuT and make sure this test fails
expect(result).toBe(false);
```

- Ensure proper matchers (`toBeOnTheScreen` vs `toBeDefined`)
- Reject complex test names with multiple conditions

See [rules/reviewer-guide.md](rules/reviewer-guide.md) for details.

### 4. Anti-patterns (MEDIUM)

Avoid:
- Code coverage without real assertions
- Weak matchers (`toBeDefined`, `toBeTruthy`) for element presence

See [rules/anti-patterns.md](rules/anti-patterns.md) for examples.

## Workflow

1. Run unit tests after code changes: `yarn test:unit`
2. Confirm all tests pass before commit

## PR Checklist

Before submitting a PR with tests:

- [ ] Tests use AAA pattern (Arrange, Act, Assert)
- [ ] Test names describe the expected behavior
- [ ] One behavior per test
- [ ] No reliance on global state or implementation details
- [ ] Time/randomness mocked where needed
- [ ] Proper matchers used for assertions
- [ ] All tests pass locally

## Resources

- [MetaMask Contributor Docs](https://github.com/MetaMask/contributor-docs/blob/main/docs/testing/unit-testing.md)
- [Jest Matchers](https://jestjs.io/docs/using-matchers)
- [React Native Testing Library](https://testing-library.com/docs/react-native-testing-library/intro/)
