"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

const AUDIO = [
  { v: "mock", t: "Mock voices", d: "Local procedural voices. Free. Default." },
  { v: "fish-free", t: "S2.1 Pro Free", d: "Fish Audio free tier, once verified for your account." },
  { v: "drama3", t: "Fish Audio Drama 3", d: "Paid. Armed only via server env; every case needs explicit approval." },
];
const LLM = [
  { v: "mock", t: "Offline comedy engine", d: "Deterministic, instant, no network." },
  { v: "ollama", t: "Ollama (local)", d: "Your local model. Falls back to scripted lines on failure." },
  { v: "anthropic", t: "Claude", d: "Needs ANTHROPIC_API_KEY on the server." },
];

/** AudioProviderSelector + LLM selector + CreditUsage: the control room. */
export function SettingsPanel() {
  const qc = useQueryClient();
  const settings = useQuery({ queryKey: ["settings"], queryFn: api.settings });
  const usage = useQuery({ queryKey: ["usage"], queryFn: api.usage });
  const patch = useMutation({ mutationFn: api.patchSettings, onSuccess: (d) => qc.setQueryData(["settings"], d) });
  const balance = useMutation({ mutationFn: api.refreshBalance, onSuccess: () => qc.invalidateQueries({ queryKey: ["usage"] }) });
  const verify = useMutation({
    mutationFn: api.verifyFree,
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["settings"] });
      void qc.invalidateQueries({ queryKey: ["usage"] });
    },
  });
  const s = settings.data;
  const u = usage.data;

  return (
    <div className="mx-auto grid w-full max-w-[1100px] gap-10">
      <div>
        <div className="eyebrow">Control room</div>
        <h1 className="mt-4 font-display text-6xl leading-none">Settings & budget</h1>
      </div>
      {settings.isError && <p className="text-burgundy-bright">{(settings.error as Error).message}</p>}
      {s && (
        <>
          <Selector title="Voices for new cases" options={AUDIO} value={s.defaults.audio} status={s.providers.audio}
            onPick={(v) => patch.mutate({ default_audio_provider: v })} />
          <Selector title="Writers' room (LLM) for new cases" options={LLM} value={s.defaults.llm} status={s.providers.llm}
            onPick={(v) => patch.mutate({ default_llm_provider: v })} />
          {patch.isError && <p className="text-sm text-burgundy-bright">{(patch.error as Error).message}</p>}
          <div className="flex flex-wrap items-center gap-3 rounded-2xl border hairline bg-ink-2 p-5">
            <div className="min-w-0 flex-1">
              <div className="eyebrow">S2.1 Pro Free verification</div>
              <p className="mt-1 text-sm text-mute">
                Checks your balance, makes one tiny free call, checks again. Free voices unlock only if the credit didn&apos;t move.
              </p>
              {verify.data && (
                <p className={cn("mt-2 text-sm", verify.data.verified ? "text-[#5aa39c]" : "text-burgundy-bright")}>
                  {verify.data.verified ? "Verified free" : "Credit changed — free tier NOT enabled"} · ${verify.data.credit_before} → ${verify.data.credit_after}
                </p>
              )}
              {verify.isError && <p className="mt-2 text-sm text-burgundy-bright">{(verify.error as Error).message}</p>}
            </div>
            <button onClick={() => verify.mutate()} disabled={verify.isPending}
              className="rounded-full border border-line-strong px-4 py-2 text-sm hover:bg-white/5 disabled:opacity-50">
              {verify.isPending ? "Verifying…" : "Verify free tier"}
            </button>
          </div>
        </>
      )}
      {u && (
        <section className="rounded-3xl border hairline bg-ink-2 p-6 sm:p-8">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <div className="eyebrow">Drama 3 credit protection</div>
              <p className="mt-2 max-w-xl text-sm text-mute">{u.note}</p>
            </div>
            <button onClick={() => balance.mutate()} disabled={balance.isPending}
              className="rounded-full border border-line-strong px-4 py-2 text-sm hover:bg-white/5 disabled:opacity-50">
              {balance.isPending ? "Checking…" : "Refresh verified balance"}
            </button>
          </div>
          {balance.isError && <p className="mt-3 text-sm text-burgundy-bright">{(balance.error as Error).message}</p>}
          <dl className="mt-6 grid grid-cols-2 gap-px overflow-hidden rounded-xl border hairline bg-line md:grid-cols-4">
            {[
              ["Estimated spend", `$${u.estimated_spend_usd.toFixed(4)}`],
              ["App ceiling", `$${u.ceiling_usd.toFixed(2)}`],
              ["Demo reserve", `$${u.demo_reserve_usd.toFixed(2)}`],
              ["Verified balance", u.verified_balance_usd === null ? "not checked" : `$${u.verified_balance_usd.toFixed(2)}`],
            ].map(([k, v]) => (
              <div key={k} className="bg-ink p-4"><dt className="eyebrow">{k}</dt><dd className="mt-2 font-display text-3xl">{v}</dd></div>
            ))}
          </dl>
          <div className="mt-8 eyebrow">Generation audit log</div>
          <div className="mt-3 max-h-[360px] overflow-auto rounded-xl border hairline">
            <table className="w-full text-left text-sm">
              <thead className="sticky top-0 bg-ink-3 font-mono text-[10px] uppercase tracking-[0.16em] text-mute">
                <tr><th className="p-3">When</th><th className="p-3">Provider</th><th className="p-3">Chars</th><th className="p-3">Est. $</th><th className="p-3">Outcome</th></tr>
              </thead>
              <tbody>
                {u.records.map((r, i) => (
                  <tr key={i} className="border-t hairline">
                    <td className="p-3 font-mono text-xs text-mute">{new Date(r.at).toLocaleString()}</td>
                    <td className="p-3">{r.provider} <span className="text-mute">{r.model}</span></td>
                    <td className="p-3 font-mono text-xs">{r.characters}</td>
                    <td className="p-3 font-mono text-xs">{r.estimated_cost_usd.toFixed(5)}</td>
                    <td className={cn("p-3 font-mono text-xs", r.outcome === "blocked" || r.outcome === "uncertain" ? "text-burgundy-bright" : r.outcome === "cache_hit" ? "text-[#5aa39c]" : "")}>
                      {r.outcome}{r.detail && <span className="text-mute"> · {r.detail.slice(0, 40)}</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
}

function Selector({ title, options, value, status, onPick }: {
  title: string; options: { v: string; t: string; d: string }[]; value: string;
  status: Record<string, { available: boolean; reason?: string }>; onPick: (v: string) => void;
}) {
  return (
    <section>
      <div className="eyebrow">{title}</div>
      <div className="mt-3 grid gap-3 md:grid-cols-3">
        {options.map((o) => {
          const st = status[o.v];
          const on = value === o.v;
          return (
            <button key={o.v} disabled={!st?.available} onClick={() => onPick(o.v)} aria-pressed={on}
              className={cn("rounded-2xl border p-5 text-left transition-colors disabled:cursor-not-allowed",
                on ? "border-gold bg-gold/[0.07]" : "border-line hover:border-line-strong", !st?.available && "opacity-55")}>
              <div className="flex items-center justify-between">
                <span className={cn("font-medium", on && "text-gold")}>{o.t}</span>
                <span className={cn("h-2 w-2 rounded-full", st?.available ? "bg-[#5aa39c]" : "bg-ink-4")} />
              </div>
              <p className="mt-2 text-sm text-mute">{o.d}</p>
              {!st?.available && st?.reason && <p className="mt-2 text-xs text-burgundy-bright/90">{st.reason}</p>}
            </button>
          );
        })}
      </div>
    </section>
  );
}
