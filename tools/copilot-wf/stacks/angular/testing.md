# Testing: Angular + TypeScript

Angular projects use one of three runners: **Karma + Jasmine** (the classic default), **Jest**, or **Vitest** (the default for
new projects in recent Angular versions). **Use whatever the repo has.** Never add or switch a test runner without asking.
The examples below avoid runner-specific APIs (no `jasmine.createSpy` / `vi.fn`), so they work with all three.

## Commands (confirm in `package.json` scripts and `angular.json` → `test` / `lint` targets; don't guess)
| Purpose | Typical command |
|---|---|
| Whole suite, once | `npx ng test --watch=false` (Karma also needs `--browsers=ChromeHeadless`) |
| One spec | Karma: `--include='**/transfer-form.component.spec.ts'` · Jest/Vitest: pass the file path |
| Type-check app + specs | `npx tsc -p tsconfig.app.json --noEmit` and `npx tsc -p tsconfig.spec.json --noEmit` |
| Lint | `npx ng lint` (only if angular-eslint is configured) |
| Build (catches template errors) | `npx ng build` |

## Test levels
| What you're proving | Level | Typical setup |
|---|---|---|
| Validator, pipe, pure function | unit | plain test, no TestBed |
| Service with HTTP | unit | `TestBed` + `provideHttpClient()` + `provideHttpClientTesting()` + `HttpTestingController` |
| Component behaviour + a11y | component | Angular Testing Library, or `TestBed` + `ComponentFixture` (+ Material harnesses) |
| Routing / guards | component | `provideRouter([...])` + `RouterTestingHarness` |

## Patterns

### Validator (pure, fastest feedback: test the rules here exhaustively)
```ts
import { FormControl } from '@angular/forms';
import { amountValidator } from './amount.validator';

it('rejects more than 2 decimal places', () => {
  const control = new FormControl('10.123', { nonNullable: true, validators: [amountValidator(2450)] });
  expect(control.errors).toEqual({ amount: 'Enter a valid amount' });
});
```

### Component with TestBed (standalone component, signal input, `output()`)
```ts
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { TransferFormComponent } from './transfer-form.component';

let fixture: ComponentFixture<TransferFormComponent>;
let el: HTMLElement;
const submitted: unknown[] = [];

beforeEach(async () => {
  await TestBed.configureTestingModule({ imports: [TransferFormComponent] }).compileComponents();
  fixture = TestBed.createComponent(TransferFormComponent);
  fixture.componentRef.setInput('accounts', [{ id: 'chk', name: 'Checking', availableBalance: 2450 }]);
  fixture.componentInstance.submitted.subscribe((v) => submitted.push(v));   // output() / EventEmitter
  fixture.detectChanges();
  el = fixture.nativeElement;
});

// Find inputs the way assistive tech does: via the label text, not a CSS class or test id.
function inputByLabel(text: string): HTMLInputElement {
  const label = [...el.querySelectorAll('label')].find((l) => l.textContent?.trim().startsWith(text));
  return el.querySelector(`#${label!.htmlFor}`) as HTMLInputElement;
}

it('shows an announced, linked error and does not submit when empty', () => {
  (el.querySelector('button[type="submit"]') as HTMLButtonElement).click();
  fixture.detectChanges();

  const input = inputByLabel('Amount');
  const alert = el.querySelector('[role="alert"]');
  expect(alert?.textContent?.trim()).toBe('Enter an amount');
  expect(input.getAttribute('aria-invalid')).toBe('true');
  expect(input.getAttribute('aria-describedby')).toContain(alert!.id);
  expect(document.activeElement).toBe(input);           // focus moved to the invalid field
  expect(submitted).toEqual([]);
});
```

### Component with Angular Testing Library (if `@testing-library/angular` is installed)
```ts
import { render, screen } from '@testing-library/angular';
import userEvent from '@testing-library/user-event';

it('submits a valid amount', async () => {
  const submitted: unknown[] = [];
  await render(TransferFormComponent, {
    inputs: { accounts: [{ id: 'chk', name: 'Checking', availableBalance: 2450 }] },  // older ATL: componentInputs
    on: { submitted: (v: unknown) => submitted.push(v) },
  });
  await userEvent.type(screen.getByLabelText(/amount/i), '100');
  await userEvent.click(screen.getByRole('button', { name: /continue/i }));
  expect(submitted).toEqual([{ fromAccountId: 'chk', amount: 100 }]);
});
```

### Service with HTTP
```ts
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';

beforeEach(() => TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] }));
afterEach(() => TestBed.inject(HttpTestingController).verify());       // no unexpected requests

it('maps a 422 into field errors', () => {
  const service = TestBed.inject(TransferService);
  let error: unknown;
  service.create({ amount: -1 }).subscribe({ error: (e) => (error = e) });
  TestBed.inject(HttpTestingController).expectOne('/api/transfers')
    .flush({ errors: [{ field: 'amount' }] }, { status: 422, statusText: 'Unprocessable Entity' });
  expect(error).toEqual({ amount: 'Enter a valid amount' });
});
```

### Automated accessibility check (if `axe-core` is installed)
```ts
import axe from 'axe-core';

it('has no axe violations in the error state', async () => {
  // …trigger the error state first, then:
  const results = await axe.run(fixture.nativeElement);
  expect(results.violations).toEqual([]);
});
```
Note: under jsdom (Jest/Vitest), axe can't check colour contrast. Under Karma it runs in a real browser and can.

## Bad paths to cover for every component/service
Invalid input · required missing · server error (4xx/5xx) · slow/failed request (loading and error states) ·
empty list · disabled/readonly state · keyboard-only use.
