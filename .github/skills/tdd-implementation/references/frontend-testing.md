# Frontend testing patterns (React + TS)

Adjust to whatever the repo already uses (Jest or Vitest, MSW or fetch mocks). Never add a new test library without asking.

```tsx
// Good path: query the way a user (or screen reader) finds things
render(<TransferForm onSubmit={onSubmit} />);
await user.type(screen.getByLabelText(/amount/i), '100');
await user.click(screen.getByRole('button', { name: /continue/i }));
expect(onSubmit).toHaveBeenCalledWith({ amount: 100 });

// Bad path: validation is announced and tied to the field
await user.click(screen.getByRole('button', { name: /continue/i }));
expect(screen.getByRole('alert')).toHaveTextContent(/amount is required/i);
expect(screen.getByLabelText(/amount/i)).toHaveAccessibleDescription(/amount is required/i);

// Keyboard-only
await user.tab();
expect(screen.getByLabelText(/amount/i)).toHaveFocus();

// Automated a11y (if jest-axe / vitest-axe is installed)
const { container } = render(<TransferForm onSubmit={jest.fn()} />);
expect(await axe(container)).toHaveNoViolations();
```

- Prefer `getByRole` → `getByLabelText` → `getByText`. Use `getByTestId` only as a last resort.
- Test hooks/services with mocked network at the boundary (MSW or the repo's mock), not by mocking internal functions.
- Cover loading, error and empty states. Figma rarely shows them, and they are most of the bugs.
- Snapshot-only tests don't count as AC coverage.
