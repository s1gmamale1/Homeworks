import { lazy, Suspense } from "react";
import { RuntimeBoot } from "./runtime/RuntimeBoot";

// The v2 Builder is a separate, lazily-loaded surface. It only mounts when the
// URL opts in (path `/app/builder` or a `?builder=1` flag) — every other URL,
// including the runtime share link `/h/{id}` (served as the SPA shell), boots
// the student runtime exactly as before.
const BuilderApp = lazy(() =>
  import("./builder/BuilderApp").then((m) => ({ default: m.BuilderApp }))
);

function isBuilderRoute(): boolean {
  const url = new URL(window.location.href);
  return (
    /\/builder(\/|$)/.test(url.pathname) ||
    url.searchParams.get("builder") === "1"
  );
}

export function App() {
  if (isBuilderRoute()) {
    return (
      <Suspense fallback={<main className="v2-shell" aria-busy="true" />}>
        <BuilderApp />
      </Suspense>
    );
  }
  return <RuntimeBoot />;
}
