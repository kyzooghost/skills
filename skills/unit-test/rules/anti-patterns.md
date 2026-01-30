# Anti-patterns to Avoid

## Contents

- Code coverage without assertions
- Weak matchers for element presence
- Testing implementation details
- Over-mocking

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
