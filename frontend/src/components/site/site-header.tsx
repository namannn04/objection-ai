"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const LINKS = [
  { href: "/docket", label: "Docket" },
  { href: "/case/the-people-vs-javascript", label: "Showcase" },
  { href: "/settings", label: "Settings" },
];

export function SiteHeader({ className }: { className?: string }) {
  const path = usePathname();
  return (
    <header className={cn("relative z-40 mx-auto flex w-full max-w-[1400px] items-center justify-between px-4 py-5 sm:px-8", className)}>
      <Link href="/" className="group flex items-baseline gap-2" aria-label="Objection AI home">
        <span className="font-display text-[28px] italic leading-none tracking-tight text-ivory">Objection</span>
        <span className="rounded-sm border border-gold/50 px-1 font-mono text-[10px] font-semibold tracking-[0.2em] text-gold">AI</span>
      </Link>
      <nav className="flex items-center gap-1 sm:gap-2">
        {LINKS.map((l) => (
          <Link
            key={l.href}
            href={l.href}
            className={cn(
              "hidden rounded-full px-3 py-2 font-mono text-[11px] uppercase tracking-[0.16em] text-mute transition-colors hover:text-ivory sm:block",
              path?.startsWith(l.href) && "text-ivory",
            )}
          >
            {l.label}
          </Link>
        ))}
        <Link
          href="/file"
          className="ml-2 rounded-full bg-ivory px-4 py-2 text-[13px] font-medium text-ink transition-transform hover:-translate-y-px hover:bg-white"
        >
          File a case
        </Link>
      </nav>
    </header>
  );
}

export function SiteFooter() {
  return (
    <footer className="mx-auto mt-auto w-full max-w-[1400px] border-t hairline px-4 py-10 sm:px-8">
      <div className="flex flex-col justify-between gap-6 sm:flex-row sm:items-end">
        <div>
          <div className="font-display text-3xl italic">Objection AI</div>
          <p className="mt-2 max-w-md text-sm text-mute">
            The Court of Absolute Nonsense. All cases, evidence and testimony are fictional. No Wi-Fi was harmed.
          </p>
        </div>
        <div className="eyebrow leading-6 sm:text-right">
          Voices performed with Fish Audio Drama 3
          <br />
          Multi-agent trials orchestrated with LangGraph
        </div>
      </div>
    </footer>
  );
}
