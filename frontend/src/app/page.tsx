import { Hero } from "@/components/landing/hero";
import { Docket, Ensemble, HowItWorks, Marquee } from "@/components/landing/sections";
import { CourtIntro } from "@/components/site/intro";
import { SiteFooter, SiteHeader } from "@/components/site/site-header";

export default function Home() {
  return (
    <>
      <CourtIntro />
      <SiteHeader className="absolute inset-x-0 top-0" />
      <main className="flex flex-col">
        <Hero />
        <Marquee />
        <HowItWorks />
        <Docket />
        <Ensemble />
      </main>
      <SiteFooter />
    </>
  );
}
