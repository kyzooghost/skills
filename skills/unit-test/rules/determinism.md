# Test Determinism & Brittleness

## Contents

- Avoid brittle tests
- Test public behavior only
- Mock time and randomness
- Avoid global state

## Avoid Brittle Tests

Do not test internal state or UI snapshots for logic. Tests should pass or fail based on observable behavior, not implementation details.

**Brittle (avoid):**

```ts
// Testing internal state
expect(component.state.isLoading).toBe(true);

// Snapshot for logic testing
expect(component).toMatchSnapshot();
```

**Robust (prefer):**

```ts
// Testing observable behavior
expect(screen.getByText('Loading...')).toBeOnTheScreen();
```

## Test Public Behavior Only

Only test the public interface of your code, not implementation details.

**Why this matters:**

- Implementation details change frequently
- Tests coupled to internals break during refactoring
- Public behavior is what users actually experience

**Correct:**

```ts
it('calculates total price correctly', () => {
  const cart = new ShoppingCart();
  cart.addItem({ price: 10 });
  cart.addItem({ price: 20 });

  expect(cart.getTotal()).toBe(30);
});
```

**Incorrect:**

```ts
it('updates internal items array', () => {
  const cart = new ShoppingCart();
  cart.addItem({ price: 10 });

  // Testing implementation detail
  expect(cart._items.length).toBe(1);
});
```

## Mock Time and Randomness

Always mock non-deterministic values to ensure tests are repeatable.

### Mocking Time

```ts
beforeEach(() => {
  jest.useFakeTimers();
  jest.setSystemTime(new Date('2024-01-01'));
});

afterEach(() => {
  jest.useRealTimers();
});

it('formats date correctly', () => {
  expect(formatDate(new Date())).toBe('January 1, 2024');
});
```

### Mocking Randomness

```ts
beforeEach(() => {
  jest.spyOn(Math, 'random').mockReturnValue(0.5);
});

afterEach(() => {
  jest.restoreAllMocks();
});
```

### Mocking External Systems

```ts
jest.mock('./api', () => ({
  fetchUser: jest.fn().mockResolvedValue({ id: 1, name: 'Test' }),
}));
```

## Avoid Global State

Tests should not depend on or modify global state. Each test should be independent and runnable in isolation.

**Problematic:**

```ts
let globalCounter = 0;

it('increments counter', () => {
  globalCounter++;
  expect(globalCounter).toBe(1);
});

it('counter is still 1', () => {
  // Fails if tests run in different order
  expect(globalCounter).toBe(1);
});
```

**Correct:**

```ts
it('increments counter', () => {
  const counter = createCounter();
  counter.increment();
  expect(counter.getValue()).toBe(1);
});

it('starts at zero', () => {
  const counter = createCounter();
  expect(counter.getValue()).toBe(0);
});
```
