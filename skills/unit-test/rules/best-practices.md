# Developer Best Practices

## Contents

- Meaningful test names
- AAA pattern (Arrange, Act, Assert)
- One behavior per test
- Focused assertions
- Avoid duplicated or polluted tests
- Mock only when necessary
- Parameterized tests
- Given / When / Then comments

## Meaningful Test Names

Describe the expected behavior, not implementation details.

**Correct:**

```ts
it('displays an error when input is invalid', () => { ... });
it('returns true for valid email', () => { ... });
it('hides selector when disabled', () => { ... });
```

**Incorrect:**

```ts
it('test validation', () => { ... });
it('should work', () => { ... });
```

## AAA Pattern (Arrange, Act, Assert)

Structure every test with three distinct phases:

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

## One Behavior Per Test

Each test should verify exactly one behavior, isolated from others.

**Correct:**

```ts
it('returns true for valid email', () => {
  expect(isEmail('a@b.com')).toBe(true);
});

it('returns false for invalid email', () => {
  expect(isEmail('invalid')).toBe(false);
});
```

**Incorrect:**

```ts
it('validates email correctly', () => {
  expect(isEmail('a@b.com')).toBe(true);
  expect(isEmail('invalid')).toBe(false);
  expect(isEmail('')).toBe(false);
});
```

## Focused Assertions

Keep assertions targeted and clear.

```ts
expect(screen.getByText('Welcome')).toBeOnTheScreen();
```

## Avoid Duplicated or Polluted Tests

Apply DRY to test infrastructure, not just production code.

**Share setup:**

```ts
beforeEach(() => mockReset());
```

**Share assertion helpers** when verification logic repeats across tests:

```java
// Before: repeated in 5 tests
assertThat(result).isPresent();
assertThat(result.get()).isEqualTo(expectedMessage);

// After: extract helper
private void assertDeniedWith(String expectedMessage) {
  Optional<String> result = validator.validateTransaction(transaction, false, false);
  assertThat(result).isPresent();
  assertThat(result.get()).isEqualTo(expectedMessage);
}
```

**When to extract:**
- Same assertion sequence appears 3+ times
- Verification involves multiple chained assertions
- Domain-specific validation (e.g., "is denied", "is valid", "contains error")

**When NOT to extract:**
- Single assertions (`assertThat(x).isTrue()`)
- Helper would hide what's being tested

## Mock Only When Necessary

Only mock when calling the real implementation is not feasible.

```ts
jest.mock('api'); // mock only when calling real API is not feasible
```

## Parameterized Tests

Use `it.each` for type-safe iteration over test cases:

```ts
it.each(['small', 'medium', 'large'] as const)('renders %s size', (size) => {
  expect(renderComponent(size)).toBeOnTheScreen();
});
```

## Given / When / Then Comments

Use these comments for additional clarity in complex tests:

```ts
it('redirects logged out user from dashboard to login', () => {
  // Given a logged out user
  const user = createLoggedOutUser();

  // When they visit the dashboard
  const result = visitDashboard(user);

  // Then they should be redirected to login
  expect(result.redirectTo).toBe('/login');
});
```
