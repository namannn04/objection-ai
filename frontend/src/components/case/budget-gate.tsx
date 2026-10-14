"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "@/lib/api";
import type { Estimate } from "@/lib/types";
import { cn } from "@/lib/utils";

export function CreditUsageIndicator({ e }: { e: Estimate }) {
  const l = e.limits;
  const used = l.projected_spend_so_far_usd;
  const after = used + e.estimated_cost_usd;
  const pct = (v: number) => `${Math.min(100, (v / Math.max(l.max_projected_spend_usd, 0.0001)) * 100)}%`;
  return (
    <div>
      <div className="flex justify-between font-mono text-[10px] uppercase tracking-[0.18em] text-mute">
        <span>Projected spend vs. app ceiling</span>
        <span>${after.toFixed(4)} / ${l.max_projected_spend_usd.toFixed(2)}</span>
      </div>
      <div className="relative mt-2 h-2 overflow-hidden rounded-full bg-ink-4">
        <div className="absolute inset-y-0 left-0 bg-gold/40" style={{ width: pct(after) }} />
        <div className="absolute inset-y-0 left-0 bg-gold" style={{ width: pct(used) }} />
      </div>
      <div className="mt-2 flex justify-between text-xs text-mute">
        <span>Case: {(l.case_characters_spent + e.characters_to_generate).toLocaleString()} / {l.max_characters_per_case.toLocaleString()} chars</span>
        <span>
          {e.verified_balance_usd !== null ? `Verified balance $${e.verified_balance_usd.toFixed(2)}` : "Balance not verified"} · reserve ${l.demo_reserve_usd.toFixed(2)}
        </span>
      </div>
    </div>
  );
}

export function BudgetGate({ caseRef, detail }: { caseRef: string; detail: string }) {
  const qc = useQueryClient();
  const est = useQuery({ queryKey: ["estimate", caseRef, "drama3"], queryFn: () => api.estimate(caseRef, "drama3") });
  const [typed, setTyped] = useState("");
  const authorize = useMutation({
    mutationFn: (cost: number) => api.authorizeAudio(caseRef, cost),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["status", caseRef] }),
  });
  const useFree = useMutation({
    mutationFn: () => api.prepareAudio(caseRef, "mock"),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["status", caseRef] }),
  });
  const e = est.data;
  const blocked = detail.startsWith("blocked") || detail.startsWith("failed");

  return (
    <div className="mx-auto max-w-3xl rounded-3xl border border-gold/30 bg-ink-2 p-6 sm:p-10">
      <div className="eyebrow text-gold">Paid voices · explicit authorisation required</div>
      <h2 className="mt-4 font-display text-5xl leading-none">The script is ready. <span className="italic text-gold">Voices cost money.</span></h2>
      {blocked && <p className="mt-4 rounded-xl border border-burgundy/60 bg-burgundy/15 p-4 text-sm text-ivory-dim">{detail}</p>}
      {est.isLoading && <div className="mt-8 h-32 animate-pulse rounded-xl bg-ink-3" />}
      {est.isError && <p className="mt-6 text-burgundy-bright">{(est.error as Error).message}</p>}
      {e && (
        <>
          <dl className="mt-8 grid grid-cols-2 gap-px overflow-hidden rounded-xl border hairline bg-line sm:grid-cols-4">
            {[
              ["Lines", `${e.lines - e.cached_lines} new · ${e.cached_lines} cached`],
              ["Characters", e.characters_to_generate.toLocaleString()],
              ["Estimate", `$${e.estimated_cost_usd.toFixed(4)}`],
              ["Model", e.model],
            ].map(([k, v]) => (
              <div key={k} className="bg-ink p-4">
                <dt className="eyebrow">{k}</dt>
                <dd className="mt-2 font-mono text-sm text-ivory">{v}</dd>
              </div>
            ))}
          </dl>
          <p className="mt-3 text-xs text-mute">{e.price_basis}. {e.note}</p>
          <div className="mt-8"><CreditUsageIndicator e={e} /></div>
          {!e.provider_available && <p className="mt-6 text-sm text-burgundy-bright">{e.provider_reason}</p>}
          <div className="mt-8 grid gap-3 sm:grid-cols-[1fr_auto]">
            <input
              value={typed}
              onChange={(ev) => setTyped(ev.target.value)}
              placeholder="Type SPEND CREDITS to confirm"
              className="rounded-xl border border-line-strong bg-ink px-4 py-3 font-mono text-sm tracking-wider text-ivory placeholder:text-mute focus:border-gold focus:outline-none"
              aria-label="Type SPEND CREDITS to confirm"
            />
            <button
              disabled={typed !== "SPEND CREDITS" || !e.provider_available || authorize.isPending}
              onClick={() => authorize.mutate(e.estimated_cost_usd)}
              className={cn("rounded-xl px-6 py-3 font-semibold transition-colors",
                typed === "SPEND CREDITS" && e.provider_available ? "bg-gold text-ink" : "bg-ink-4 text-mute")}
            >
              {authorize.isPending ? "Authorising…" : `Generate with Drama 3 · $${e.estimated_cost_usd.toFixed(4)}`}
            </button>
          </div>
          {authorize.isError && <p className="mt-3 text-sm text-burgundy-bright">{(authorize.error as Error).message}</p>}
        </>
      )}
      <div className="mt-10 border-t hairline pt-6">
        <button onClick={() => useFree.mutate()} disabled={useFree.isPending}
          className="font-mono text-[11px] uppercase tracking-[0.18em] text-mute underline-offset-4 hover:text-ivory hover:underline">
          {useFree.isPending ? "Switching…" : "Use free mock voices instead →"}
        </button>
      </div>
    </div>
  );
}
