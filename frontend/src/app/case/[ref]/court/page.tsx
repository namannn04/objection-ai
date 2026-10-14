import type { Metadata } from "next";
import { Courtroom } from "@/components/court/courtroom";
import { SiteHeader } from "@/components/site/site-header";
import type { Mode } from "@/lib/types";

export const metadata: Metadata = { title: "In session" };

export default async function CourtPage({ params, searchParams }: {
  params: Promise<{ ref: string }>; searchParams: Promise<{ mode?: string }>;
}) {
  const { ref } = await params;
  const { mode } = await searchParams;
  const m: Mode = mode === "spectator" || mode === "chaos" ? mode : "jury";
  return (
    <>
      <SiteHeader className="py-3" />
      <main className="flex-1 px-3 pb-10 sm:px-6">
        <Courtroom caseRef={ref} mode={m} />
      </main>
    </>
  );
}
