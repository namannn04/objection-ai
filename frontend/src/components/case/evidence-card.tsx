"use client";

import { FileText, Image as ImageIcon, LineChart, Package, ScrollText, Waves } from "lucide-react";
import type { Evidence } from "@/lib/types";
import { cn } from "@/lib/utils";

const ICONS: Record<string, typeof FileText> = {
  document: FileText, photo: ImageIcon, log: ScrollText, object: Package, recording: Waves, chart: LineChart,
};

export function EvidenceCard({ e, active = false, revealed = true, compact = false }: {
  e: Evidence; active?: boolean; revealed?: boolean; compact?: boolean;
}) {
  const Icon = ICONS[e.kind] ?? FileText;
  return (
    <article
      className={cn(
        "relative overflow-hidden rounded-xl border bg-[linear-gradient(160deg,#1d1a16,#141312)] transition-all duration-500",
        active ? "border-gold shadow-[0_0_0_1px_rgb(214_174_98/0.4),0_20px_50px_-20px_rgb(214_174_98/0.35)]" : "border-line",
        !revealed && "opacity-45",
        compact ? "p-4" : "p-5",
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="font-mono text-[10px] uppercase tracking-[0.22em] text-gold">Exhibit {e.id}</div>
        <Icon className="h-4 w-4 text-mute" aria-hidden />
      </div>
      <h4 className={cn("mt-3 font-display leading-tight", compact ? "text-xl" : "text-2xl")}>{revealed ? e.title : "Sealed until presented"}</h4>
      {revealed && <p className="mt-2 text-sm leading-relaxed text-ivory-dim">{e.description}</p>}
      {revealed && !compact && e.details.length > 0 && (
        <ul className="mt-3 space-y-1 border-t hairline pt-3">
          {e.details.map((d) => <li key={d} className="font-mono text-[11px] text-mute">— {d}</li>)}
        </ul>
      )}
      <div className="mt-4 flex items-center justify-between font-mono text-[9px] uppercase tracking-[0.2em]">
        <span className={e.favours === "defense" ? "text-[#5aa39c]" : "text-[#c4515f]"}>Favours the {e.favours}</span>
        <span className="-rotate-3 rounded border border-burgundy-bright/50 px-1.5 py-0.5 text-burgundy-bright/80">Fictional</span>
      </div>
    </article>
  );
}
