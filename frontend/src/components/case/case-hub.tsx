"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";
import { api } from "@/lib/api";
import type { Mode } from "@/lib/types";
import { cn, formatMs } from "@/lib/utils";
import { BudgetGate } from "./budget-gate";
import { EvidenceCard } from "./evidence-card";
import { WitnessCard } from "./witness-card";

const MODES: { v: Mode; t: string; d: string }[] = [
  { v: "spectator", t: "Spectator", d: "Watch & listen" },
  { v: "jury", t: "Jury", d: "Vote & object" },
  { v: "chaos", t: "Chaos", d: "Type your own" },
];

const PROVIDER_LABEL: Record<string, string> = {
  mock: "Local mock voices (procedural, free)",
  drama3: "Fish Audio Drama 3",
  "fish-free": "Fish Audio S2.1 Pro Free",
};

export function CaseHub({ caseRef }: { caseRef: string }) {
  const detail = useQuery({ queryKey: ["case", caseRef], queryFn: () => api.getCase(caseRef) });
  const manifest = useQuery({ queryKey: ["manifest", caseRef], queryFn: () => api.manifest(caseRef) });
  const [mode, setMode] = useState<Mode | null>(null);
  const [paid, setPaid] = useState(false);
  const qc = useQueryClient();
  const settings = useQuery({ queryKey: ["settings"], queryFn: api.settings });
  const rerecord = useMutation({
    mutationFn: (provider: "mock" | "fish-free") => api.prepareAudio(caseRef, provider),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["status", caseRef] }),
  });
  const free = settings.data?.providers.audio["fish-free"];
  const drama = settings.data?.providers.audio.drama3;
  const d = detail.data;
  const m = manifest.data;
  if (!d || !m) return <div className="mx-auto h-[60vh] w-full max-w-[1300px] animate-pulse rounded-3xl bg-ink-2" />;
  const chosen = mode ?? d.case.participation_mode;
  const people = m.characters
    .filter((c) => (c.role === "defendant" || c.role === "witness") && !c.surprise)
    .sort((a, b) => (a.role === "defendant" ? -1 : b.role === "defendant" ? 1 : a.key.localeCompare(b.key)));
  const hasSurprise = m.characters.some((c) => c.surprise);

  return (
    <div className="mx-auto w-full max-w-[1300px]">
      <div className="grid gap-10 lg:grid-cols-[1.4fr_1fr] lg:items-end">
        <div>
          <div className="font-mono text-[11px] tracking-[0.2em] text-mute">
            {d.case.case_number} · {d.case.trial_length.toUpperCase()} TRIAL{d.case.is_showcase && " · SHOWCASE"}
          </div>
          <h1 className="mt-5 font-display text-[clamp(3rem,7vw,6.4rem)] leading-[0.9] text-balance">{d.case.title}</h1>
          <p className="mt-6 max-w-2xl text-lg leading-relaxed text-ivory-dim">{d.plan?.accusation_summary}</p>
          <ul className="mt-6 flex flex-wrap gap-2">
            {d.plan?.charges.map((c) => (
              <li key={c} className="rounded-full border border-burgundy-bright/40 px-3 py-1 font-mono text-[10px] uppercase tracking-[0.16em] text-[#d77b87]">{c}</li>
            ))}
          </ul>
        </div>
        <div className="rounded-3xl border hairline bg-ink-2 p-6">
          <div className="eyebrow">Your seat in the courtroom</div>
          <div className="mt-4 grid grid-cols-3 gap-2" role="radiogroup">
            {MODES.map((o) => (
              <button key={o.v} role="radio" aria-checked={chosen === o.v} onClick={() => setMode(o.v)}
                className={cn("rounded-xl border p-3 text-left transition-colors", chosen === o.v ? "border-gold bg-gold/[0.07]" : "border-line hover:border-line-strong")}>
                <div className={cn("text-sm font-medium", chosen === o.v && "text-gold")}>{o.t}</div>
                <div className="mt-0.5 text-xs text-mute">{o.d}</div>
              </button>
            ))}
          </div>
          <Link href={`/case/${d.case.slug}/court?mode=${chosen}`}
            className="mt-5 flex items-center justify-center gap-3 rounded-full bg-gold py-4 font-semibold text-ink shadow-[0_10px_40px_-12px_rgb(214_174_98/0.7)] transition-transform hover:-translate-y-0.5">
            Enter the courtroom →
          </Link>
          <div className="mt-4 flex justify-between font-mono text-[10px] uppercase tracking-[0.16em] text-mute">
            <span>≈ {formatMs(m.audio.estimated_main_duration_ms)} runtime</span>
            <Link href={`/podcast/${d.case.slug}`} className="hover:text-ivory">Podcast mode →</Link>
          </div>
          <div className="mt-3 text-xs text-mute">Voices: {m.audio.providers.map((p) => PROVIDER_LABEL[p] ?? p).join(" + ") || "not recorded"}</div>
        </div>
      </div>

      <section className="mt-20">
        <div className="eyebrow">The accused & the witnesses</div>
        <div className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {people.map((c, i) => <WitnessCard key={c.key} c={c} i={i} />)}
          {hasSurprise && (
            <div className="grid place-items-center rounded-2xl border border-dashed border-line-strong p-4 text-center">
              <div>
                <div className="font-display text-4xl italic text-gold/70">?</div>
                <div className="mt-1 font-mono text-[10px] uppercase tracking-[0.18em] text-mute">A surprise witness may appear</div>
              </div>
            </div>
          )}
        </div>
      </section>

      <section className="mt-16">
        <div className="eyebrow">Evidence board</div>
        <div className="mt-5 grid gap-4 md:grid-cols-3">
          {m.evidence.map((e) => <EvidenceCard key={e.id} e={e} revealed={!e.is_twist} />)}
        </div>
        <p className="mt-3 text-xs text-mute">One exhibit stays sealed until it is presented in court.</p>
      </section>

      <section className="mt-16 rounded-2xl border hairline bg-ink-2 p-6">
        <div className="eyebrow">Voices</div>
        <p className="mt-2 text-sm text-mute">
          Re-record this trial with another voice provider. Unchanged lines are reused from the cache.
        </p>
        <div className="mt-4 flex flex-wrap gap-3">
          <button disabled={rerecord.isPending} onClick={() => rerecord.mutate("mock")}
            className="rounded-full border border-line-strong px-4 py-2 text-sm hover:bg-white/5 disabled:opacity-50">Mock voices (free)</button>
          <button disabled={rerecord.isPending || !free?.available} onClick={() => rerecord.mutate("fish-free")}
            title={free?.reason} className="rounded-full border border-line-strong px-4 py-2 text-sm hover:bg-white/5 disabled:opacity-40">
            Fish S2.1 Pro Free
          </button>
          <button disabled={!drama?.available} onClick={() => setPaid((v) => !v)} title={drama?.reason}
            className="rounded-full border border-gold/50 px-4 py-2 text-sm text-gold hover:bg-gold/10 disabled:opacity-40">
            Fish Drama 3 (paid)…
          </button>
        </div>
        {!free?.available && free?.reason && <p className="mt-2 text-xs text-mute">S2.1 Free: {free.reason}</p>}
        {!drama?.available && drama?.reason && <p className="mt-1 text-xs text-mute">Drama 3: {drama.reason}</p>}
        {rerecord.isError && <p className="mt-2 text-sm text-burgundy-bright">{(rerecord.error as Error).message}</p>}
        {paid && drama?.available && <div className="mt-6"><BudgetGate caseRef={caseRef} detail="" /></div>}
      </section>

      <details className="group mt-16 rounded-2xl border hairline bg-ink-2 p-6">
        <summary className="cursor-pointer list-none font-mono text-[11px] uppercase tracking-[0.18em] text-mute group-open:text-ivory">
          Behind the bench · how this trial was made
        </summary>
        <div className="mt-6 grid gap-8 md:grid-cols-2">
          <div>
            <div className="eyebrow">Generator</div>
            <p className="mt-2 font-mono text-xs text-ivory-dim break-all">{d.generator}</p>
            <div className="eyebrow mt-6">Validation</div>
            <p className="mt-2 text-sm text-ivory-dim">
              {d.validation?.valid ? "Passed" : "Failed"} · {String(d.validation?.stats?.turns ?? "?")} lines · {String(d.validation?.stats?.characters ?? "?")} characters
            </p>
            <div className="eyebrow mt-6">Private strategies (spoilers)</div>
            <p className="mt-2 text-sm text-ivory-dim"><span className="text-[#d77b87]">Prosecution:</span> {d.plan?.prosecutor_strategy}</p>
            <p className="mt-2 text-sm text-ivory-dim"><span className="text-[#5aa39c]">Defense:</span> {d.plan?.defense_strategy}</p>
          </div>
          <div>
            <div className="eyebrow">Humor evaluation (heuristic rubric scores, not laugh predictions)</div>
            <ul className="mt-3 space-y-2">
              {(d.humor_report?.scenes ?? []).map((s) => (
                <li key={s.scene_id} className="flex items-center gap-3 text-sm">
                  <span className="w-20 font-mono text-xs text-mute">{s.scene_id}</span>
                  <span className="h-1.5 flex-1 overflow-hidden rounded-full bg-ink-4">
                    <span className="block h-full bg-gold" style={{ width: `${s.overall * 10}%` }} />
                  </span>
                  <span className="w-10 text-right font-mono text-xs">{s.overall.toFixed(1)}</span>
                </li>
              ))}
              {!d.humor_report?.scenes?.length && <li className="text-sm text-mute">Hand-authored — not machine scored.</li>}
            </ul>
          </div>
        </div>
      </details>
    </div>
  );
}
