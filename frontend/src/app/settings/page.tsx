import type { Metadata } from "next";
import { SettingsPanel } from "@/components/settings/settings-panel";
import { SiteFooter, SiteHeader } from "@/components/site/site-header";

export const metadata: Metadata = { title: "Settings" };

export default function SettingsPage() {
  return (
    <>
      <SiteHeader />
      <main className="flex-1 px-4 pb-24 pt-8 sm:px-8"><SettingsPanel /></main>
      <SiteFooter />
    </>
  );
}
