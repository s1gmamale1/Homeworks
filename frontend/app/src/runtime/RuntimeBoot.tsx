import { useEffect, useState } from "react";
import { readContext } from "../shared/context";
import { hydrate, getGateState, ApiError } from "../shared/api";
import { useRuntimeStore } from "./store";
import { V2FlowController } from "./V2FlowController";
import { Pill, Eyebrow, Title, Lead, Button } from "../shared/ui/primitives";
import s from "./RuntimeBoot.module.css";

type BootStatus = "loading" | "ready" | "notFound" | "error";

// On mount: resolve context, fetch hydrate + gate-state, then render the flow.
// Shows a tasteful skeleton while loading and a calm error frame on failure.
export function RuntimeBoot() {
  const [status, setStatus] = useState<BootStatus>("loading");
  const [errorMsg, setErrorMsg] = useState<string>("");

  const initSession = useRuntimeStore((st) => st.initSession);
  const setPayload = useRuntimeStore((st) => st.setPayload);
  const setGateState = useRuntimeStore((st) => st.setGateState);
  const hwId = useRuntimeStore((st) => st.hwId);
  const sessionId = useRuntimeStore((st) => st.sessionId);

  useEffect(() => {
    const ctx = readContext();
    if (!ctx.hwId) {
      setStatus("notFound");
      return;
    }
    initSession(ctx.hwId, ctx.sessionId);
  }, [initSession]);

  useEffect(() => {
    if (!hwId || !sessionId) return;
    let cancelled = false;

    (async () => {
      try {
        const payload = await hydrate(hwId);
        if (cancelled) return;
        setPayload(payload);

        // Gate state is best-effort: a brand-new session may have none yet.
        try {
          const gate = await getGateState(hwId, sessionId);
          if (!cancelled) setGateState(gate);
        } catch {
          if (!cancelled) {
            setGateState({
              cbp: { passed: false, checkpoints_correct: 0, checkpoints_total: 3 },
              mc: { passed: false, score_pct: 0, threshold_pct: 60 },
              practice_arc_unlocked: false,
            });
          }
        }

        if (!cancelled) setStatus("ready");
      } catch (err) {
        if (cancelled) return;
        if (err instanceof ApiError && err.status === 404) {
          setStatus("notFound");
        } else {
          setErrorMsg((err as Error).message || "Something went wrong.");
          setStatus("error");
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [hwId, sessionId, setPayload, setGateState]);

  if (status === "loading") return <BootSkeleton />;
  if (status === "notFound") return <BootNotFound />;
  if (status === "error") return <BootError message={errorMsg} />;
  return <V2FlowController />;
}

function BootSkeleton() {
  return (
    <main className="v2-shell" data-testid="boot-skeleton" aria-busy="true">
      <div className={s.skelPill} />
      <div className={`${s.skel} ${s.skelTitle}`} />
      <div className={`${s.skel} ${s.skelLead}`} />
      <div className={`${s.skel} ${s.skelLeadShort}`} />
      <div className={s.skelGrid}>
        <div className={`${s.skel} ${s.skelTile}`} />
        <div className={`${s.skel} ${s.skelTile}`} />
      </div>
      <span className="sr-only">Loading homework…</span>
    </main>
  );
}

function BootNotFound() {
  return (
    <main className="v2-shell" data-testid="boot-not-found">
      <Eyebrow>404</Eyebrow>
      <Title size="hero">Homework not found.</Title>
      <Lead>
        This link may have expired or the homework was removed. Check the URL
        and try again.
      </Lead>
    </main>
  );
}

function BootError({ message }: { message: string }) {
  return (
    <main className="v2-shell" data-testid="boot-error">
      <Pill tone="warn">Connection issue</Pill>
      <Title size="hero" className={s.errTitle}>
        We couldn’t load this homework.
      </Title>
      <Lead>{message}</Lead>
      <div style={{ marginTop: 24 }}>
        <Button variant="blue" onClick={() => window.location.reload()}>
          Try again
        </Button>
      </div>
    </main>
  );
}
