import type { Metadata } from "next";
import { PodcastStudio } from "@/components/podcast/podcast-player";
import { SiteFooter, SiteHeader } from "@/components/site/site-header";

export const metadata: Metadata = { title: "Podcast" };

export default async function PodcastPage({ params }: { params: Promise<{ ref: string }> }) {
  const { ref } = await params;
  return (
    <>
      <SiteHeader />
      <main className="flex-1 px-4 pb-24 pt-6 sm:px-8"><PodcastStudio caseRef={ref} /></main>
      <SiteFooter />
    </>
  );
}
