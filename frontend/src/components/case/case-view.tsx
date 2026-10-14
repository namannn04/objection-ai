"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { BudgetGate } from "./budget-gate";
import { CaseHub } from "./case-hub";
import { GenerationProgress, usePrepEvents } from "./preparation";

const PREPARING = new Set(["CASE_CREATED", "CASE_PREPARATION", "SCRIPT_PLANNING", "SCRIPT_VALIDATION", "AUDIO_PREPARATION"]);

export function CaseView({ caseRef }: { caseRef: string }) {
  const qc = useQueryClient();
  const status = useQuery({
    queryKey: ["status", caseRef],
    queryFn: () => api.status(caseRef),
    refetchInterval: (q) => (q.state.data && !PREPARING.has(q.state.data.status) ? false : 1200),
  });
  const s = status.data;
  const awaiting = s?.status === "AUDIO_PREPARATION" && (s.detail === "awaiting_authorization" || /^(blocked|failed)/.test(s.detail));
  const preparing = !!s && PREPARING.has(s.status) && !awaiting;
  const progress = usePrepEvents(caseRef, preparing);
  const retry = useMutation({ mutationFn: () => api.regenerate(caseRef), onSuccess: () => qc.invalidateQueries({ queryKey: ["status", caseRef] }) });
  const caseInfo = useQuery({ queryKey: ["case-lite", caseRef], queryFn: () => api.getCase(caseRef), enabled: preparing });

  if (status.isError) {
    return <p className="mx-auto max-w-xl rounded-2xl border border-burgundy/60 bg-burgundy/10 p-8 text-center text-ivory-dim">{(status.error as Error).message}</p>;
  }
  if (!s) return <div className="mx-auto h-[60vh] w-full max-w-[1300px] animate-pulse rounded-3xl bg-ink-2" />;
  if (s.status === "FAILED") {
    return (
      <div className="mx-auto max-w-2xl text-center">
        <div className="eyebrow text-burgundy-bright">Mistrial</div>
        <h1 className="mt-4 font-display text-6xl">The court could not proceed.</h1>
        <p className="mt-4 text-ivory-dim">{s.detail}</p>
        <button onClick={() => retry.mutate()} className="mt-8 rounded-full bg-gold px-6 py-3 font-semibold text-ink">Retry the preparation</button>
      </div>
    );
  }
  if (awaiting) return <BudgetGate caseRef={caseRef} detail={s.detail} />;
  if (preparing) {
    return (
      <GenerationProgress
        status={s.status}
        caseNumber={caseInfo.data?.case.case_number ?? ""}
        defendant={caseInfo.data?.case.defendant ?? "…"}
        progress={{ ...progress, title: progress.title ?? (s.title || undefined) }}
        running={s.job?.status === "running" || s.job?.status === "queued"}
      />
    );
  }
  return <CaseHub caseRef={caseRef} />;
}
