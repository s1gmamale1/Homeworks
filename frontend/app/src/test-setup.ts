// Test environment setup. Auto-extends Vitest's `expect` with the @testing-library
// custom matchers (e.g. `toBeInTheDocument`, `toHaveTextContent`). Loaded once per
// test file via the `setupFiles` entry in vite.config.ts.
import "@testing-library/jest-dom/vitest";
