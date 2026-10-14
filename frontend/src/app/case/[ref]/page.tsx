import { CaseView } from "@/components/case/case-view";
import { SiteFooter, SiteHeader } from "@/components/site/site-header";

export default async function CasePage({ params }: { params: Promise<{ ref: string }> }) {
  const { ref } = await params;
  return (
    <>
      <SiteHeader />
      <main className="flex-1 px-4 pb-24 pt-8 sm:px-8">
        <CaseView caseRef={ref} />
      </main>
      <SiteFooter />
    </>
  );
}
