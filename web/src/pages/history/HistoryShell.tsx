import { useState } from "react";
import { HistoryNav } from "./HistoryNav";
import { type SectionId } from "./types";
import { OrdersSection } from "./sections/OrdersSection";
import { RunsSection } from "./sections/RunsSection";

function SectionContent({ id }: { id: SectionId }) {
  switch (id) {
    case "runs":   return <RunsSection />;
    case "orders": return <OrdersSection />;
  }
}

export function HistoryShell() {
  const [selected, setSelected] = useState<SectionId>("runs");

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold text-primary">History</h1>
      <HistoryNav selected={selected} onSelect={setSelected} />
      <SectionContent id={selected} />
    </div>
  );
}
