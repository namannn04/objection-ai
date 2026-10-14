"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { CaseFileCard } from "@/components/landing/sections";
import { SiteFooter, SiteHeader } from "@/components/site/site-header";
import { api } from "@/lib/api";

/** CaseHistory: every case filed on this machine, saved and reopenable. */
export default function DocketPage() {
  const q = useQuery({ queryKey: ["cases", "all"], queryFn: () => api.listCases({ limit: 100 }) });
  const cases = q.data ?? [];
  return (
    <>
      <SiteHeader />
      <main className="mx-auto w-full max-w-[1400px] flex-1 px-4 pb-24 pt-8 sm:px-8">
        <div className="flex flex-wrap items-end justify-between gap-6">
          <div>
            <div className="eyebrow">The docket</div>
            <h1 className="mt-4 font-display text-6xl leading-none sm:text-7xl">Every case on record</h1>
          </div>
          <Link href="/file" className="rounded-full bg-gold px-6 py-3 font-semibold text-ink">File a new case</Link>
        </div>
        {q.isLoading && <div className="mt-12 grid gap-4 md:grid-cols-3">{[0, 1, 2, 3, 4, 5].map((i) => <div key={i} className="h-[220px] animate-pulse rounded-2xl bg-ink-2" />)}</div>}
        {q.isError && <p className="mt-12 text-burgundy-bright">{(q.error as Error).message}</p>}
        {!q.isLoading && !cases.length && !q.isError && <p className="mt-12 text-mute">The docket is empty. Suspiciously empty.</p>}
        <div className="mt-12 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {cases.map((c) => <CaseFileCard key={c.id} c={c} />)}
        </div>
      </main>
      <SiteFooter />
    </>
  );
}
