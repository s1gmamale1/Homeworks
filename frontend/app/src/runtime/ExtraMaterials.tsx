import { useRuntimeStore } from "./store";
import {
  ExtraMaterialsView,
  type ExtraMaterialsViewData,
} from "../shared/ExtraMaterialsView";
import { Eyebrow, Title, Button } from "../shared/ui/primitives";
import LivingBackdrop from "./LivingBackdrop";
import s from "./ExtraMaterials.module.css";

// End-of-flow Extra Materials screen — shown after the Reflection when the
// homework has any authored items. Ungraded; the student reads/watches and taps
// Done to return to the Hub. Reuses the shared renderer (YouTube iframe /
// inline image / link), so authoring preview and student view stay identical.
export function ExtraMaterials() {
  const payload = useRuntimeStore((st) => st.payload);
  const goto = useRuntimeStore((st) => st.goto);
  const data =
    (payload?.content_json as { extra_materials?: ExtraMaterialsViewData } | null)
      ?.extra_materials ?? {};

  return (
    <main className="v2-shell" data-testid="extra-materials-screen">
      {/* Same living backdrop DNA as the Hub/other surfaces — purple to match
          the violet Extra Materials node the student tapped to get here. */}
      <LivingBackdrop variant="purple" />
      <div className={s.stage}>
        <div className={s.head}>
          <Eyebrow cyan>Extra materials</Eyebrow>
          <Title size="section">{data.title || "Go further"}</Title>
        </div>
        <ExtraMaterialsView value={data} />
        <div className={s.actions}>
          <Button variant="blue" onClick={() => goto("hub")} data-testid="extra-materials-done">
            Done →
          </Button>
        </div>
      </div>
    </main>
  );
}
