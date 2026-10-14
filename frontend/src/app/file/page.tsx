import type { Metadata } from "next";
import { CaseCreationForm } from "@/components/case/case-creation-form";
import { SiteHeader } from "@/components/site/site-header";

export const metadata: Metadata = { title: "File a case" };

export default function FilePage() {
  return (
    <>
      <SiteHeader />
      <main className="flex-1 px-4 pb-24 pt-10 sm:px-8">
        <CaseCreationForm />
      </main>
    </>
  );
}
