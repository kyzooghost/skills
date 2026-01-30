# Reviewer Responsibilities

## Contents

- Test the test
- Ensure proper matchers
- Review snapshot diffs
- Reject complex test names

## Test the Test

Validate that tests actually fail when the code is broken. A test that never fails provides no value.

**How to verify:**

1. Temporarily break the System under Test (SuT)
2. Run the test
3. Confirm the test fails
4. Restore the original code

**Example:**

```ts
it('hides selector when disabled', () => {
  const { queryByTestId } = render(<Selector enabled={false} />);
  expect(queryByTestId('IPFS_GATEWAY_SELECTED')).toBeNull();

  // To test the test: change enabled={false} to enabled={true}
  // and verify this test fails
});
```

**Why this matters:**

- Tests with always-true assertions waste CI time
- False confidence in code correctness
- Bugs slip through that tests should have caught

## Ensure Proper Matchers

Use the most specific matcher for the assertion.

**For element presence:**

```ts
// Correct - specific to element presence
expect(queryByText('Item')).toBeOnTheScreen();
expect(queryByText('Item')).toBeNull(); // for absence

// Incorrect - too generic
expect(queryByText('Item')).toBeDefined();
expect(queryByText('Item')).toBeTruthy();
```

**For values:**

```ts
// Correct
expect(result).toBe(42);
expect(array).toHaveLength(3);
expect(object).toEqual({ id: 1, name: 'Test' });

// Incorrect - loses specificity
expect(result).toBeTruthy();
expect(array.length > 0).toBe(true);
```

**For async operations:**

```ts
// Correct
await expect(promise).resolves.toBe('success');
await expect(promise).rejects.toThrow('error');

// Incorrect
expect(await promise).toBe('success');
```

## Review Snapshot Diffs

When reviewing PRs with snapshot changes:

1. **Verify the diff is intentional** - Changes should relate to the PR's purpose
2. **Check for unintended changes** - Look for unexpected modifications
3. **Ensure snapshots are focused** - Large snapshots are hard to review and maintain

**Warning signs:**

- Snapshot changes unrelated to the PR
- Very large snapshot diffs
- Snapshots testing implementation details instead of output

## Reject Complex Test Names

Test names should describe a single behavior. Reject names with multiple conditions.

**Acceptable:**

```ts
it('renders button when enabled');
it('disables button when input is empty');
it('shows error for invalid input');
```

**Reject:**

```ts
// Multiple conditions - split into separate tests
it('renders and disables button when input is empty or invalid');
it('shows loading state and then success message after API call');
```

**Why this matters:**

- Complex names indicate the test covers too much
- Harder to understand what broke when test fails
- Violates "one behavior per test" principle
