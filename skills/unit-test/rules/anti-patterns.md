# Anti-patterns to Avoid

## Contents

- Code coverage without assertions
- Weak matchers for element presence
- Testing implementation details
- Testing internal ordering/precedence
- Over-mocking
- Mocking data/value objects

## Code Coverage Without Assertions

High code coverage means nothing without meaningful assertions. Tests that execute code without verifying behavior create false confidence.

**Anti-pattern:**

```ts
it('processes data', () => {
  const processor = new DataProcessor();
  processor.process(testData);
  // 100% lines executed, but no assertions!
});
```

**Correct:**

```ts
it('processes data and returns formatted result', () => {
  const processor = new DataProcessor();
  const result = processor.process(testData);

  expect(result.status).toBe('complete');
  expect(result.items).toHaveLength(3);
});
```

## Weak Matchers for Element Presence

Using generic matchers like `toBeDefined` or `toBeTruthy` for element presence checks can hide bugs.

**Anti-pattern:**

```ts
// These pass even when element is not what you expect
expect(queryByText('Item')).toBeDefined();
expect(queryByText('Item')).toBeTruthy();
expect(element).not.toBeNull(); // too generic
```

**Correct:**

```ts
// Specific matchers for element presence
expect(queryByText('Item')).toBeOnTheScreen();
expect(screen.getByRole('button')).toBeEnabled();
expect(queryByTestId('modal')).toBeNull(); // for explicit absence
```

**Why weak matchers fail:**

- `toBeDefined` passes for `null` in some contexts
- `toBeTruthy` passes for any truthy value, not just the expected element
- These don't communicate intent clearly

## Testing Implementation Details

Tests coupled to implementation details break during refactoring even when behavior is unchanged.

**Anti-pattern:**

```ts
it('calls internal helper', () => {
  const spy = jest.spyOn(component, '_internalHelper');
  component.doAction();

  expect(spy).toHaveBeenCalled();
});

it('sets internal state correctly', () => {
  component.doAction();

  expect(component._internalState).toEqual({ loading: true });
});
```

**Correct:**

```ts
it('shows loading indicator during action', () => {
  component.doAction();

  expect(screen.getByText('Loading...')).toBeOnTheScreen();
});
```

## Testing Internal Ordering/Precedence

Don't test the order in which internal checks happen unless it's a documented requirement.

**Anti-pattern:**

```java
@Test
void senderDenialTakesPrecedenceOverAuthorizationDenial() {
  // Tests that sender is checked before authorization
  // But does anyone care about this order?
}

@Test
void deniedAuthorityBeforeAddress() {
  // Tests authority checked before address
  // Will break if someone reorders the checks during refactoring
}
```

**Ask yourself:**
- "Does the caller/user care which check fails first?"
- "If I reorder these checks, does the observable behavior change?"
- "Will this test break during refactoring without any behavior change?"

If the answer is "no, no, yes" - don't write the test.

**When ordering DOES matter:**
- Short-circuit for performance (expensive check should come last)
- Security requirements (auth check must happen before data access)
- Documented API contract ("returns first validation error encountered")

If ordering matters, document WHY in the test name or comment.

## Over-Mocking

Mocking too much can make tests pass even when the real integration is broken.

**Anti-pattern:**

```ts
it('saves user', () => {
  const mockDb = { save: jest.fn().mockResolvedValue(true) };
  const mockValidator = { validate: jest.fn().mockReturnValue(true) };
  const mockLogger = { log: jest.fn() };
  const mockCache = { invalidate: jest.fn() };

  const service = new UserService(mockDb, mockValidator, mockLogger, mockCache);
  await service.saveUser({ name: 'Test' });

  // Testing that mocks were called, not actual behavior
  expect(mockDb.save).toHaveBeenCalled();
  expect(mockCache.invalidate).toHaveBeenCalled();
});
```

**Better approach:**

- Use real implementations when feasible
- Mock only external boundaries (APIs, databases, file system)
- Consider integration tests for complex interactions

```ts
it('saves user to database', async () => {
  const db = createTestDatabase(); // real in-memory DB
  const service = new UserService(db);

  await service.saveUser({ name: 'Test' });

  const saved = await db.findByName('Test');
  expect(saved).toEqual({ id: expect.any(Number), name: 'Test' });
});
```

## Mocking Data/Value Objects

Never mock simple data classes, value objects, or DTOs. Use real instances via constructors or builders.

**Anti-pattern:**

```java
CodeDelegation delegation = mock(CodeDelegation.class);
when(delegation.authorizer()).thenReturn(Optional.of(address));
when(delegation.address()).thenReturn(target);
```

**Correct:**

```java
CodeDelegation delegation = CodeDelegation.builder()
    .chainId(chainId)
    .address(target)
    .nonce(0)
    .signAndBuild(keyPair); // authorizer() derived from signer
```

**Why this matters:**

- Mocked value objects can return impossible combinations (e.g., values that violate invariants)
- Tests pass with mocks but fail with real objects, hiding bugs
- If production code uses `Foo.builder()`, tests should too

**When setup is complex:**

If creating real instances requires setup (signing, encryption, external state), create shared test utilities rather than mocking:

```java
// Create a test helper instead of mocking
private CodeDelegation createTestDelegation(Address authority, Address target) {
  KeyPair keyPair = getOrCreateKeyPairFor(authority);
  return CodeDelegation.builder()
      .chainId(TEST_CHAIN_ID)
      .address(target)
      .nonce(0)
      .signAndBuild(keyPair);
}
```
