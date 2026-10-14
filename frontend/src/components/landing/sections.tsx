"use client";

import { useQuery } from "@tanstack/react-query";
import { motion } from "motion/react";
import Link from "next/link";
import { CharacterPortrait } from "@/components/characters/character-portrait";
import { api } from "@/lib/api";
import { DEMO_CAST } from "@/lib/demo-cast";
import type { CaseSummary } from "@/lib/types";
import { cn, PHASE_LABEL } from "@/lib/utils";

const ACCUSATIONS = [
  "My alarm clock, for destroying my dreams",
  "JavaScript, for causing emotional damage",
  "My friend who is always “five minutes away”",
  "The office Wi-Fi, for vanishing during meetings",
  "Monday mornings, for crimes against humanity",
  "The semicolon, for making developers suffer",
  "My laptop fan, for preparing to launch into space",
  "Whoever invented group projects",
  "My phone battery, for betraying me at 1%",
  "The snooze button, for ruining my career",
];

export function Marquee() {
  const row = [...ACCUSATIONS, ...ACCUSATIONS];
  return (
    <section className="relative border-y hairline py-14">
      <div className="mx-auto max-w-[1400px] px-4 sm:px-8">
        <h2 className="font-display text-[clamp(2.4rem,5.6vw,5.2rem)] leading-[0.9] text-balance">
          Everything is guilty <span className="italic text-gold">until proven ridiculous.</span>
        </h2>
      </div>
      <div className="relative mt-10 overflow-hidden [mask-image:linear-gradient(90deg,transparent,black_8%,black_92%,transparent)]">
        <div className="flex w-max animate-marquee gap-10 whitespace-nowrap">
          {row.map((a, i) => (
            <span key={i} className="flex items-center gap-10 font-display text-3xl italic text-ivory-dim sm:text-4xl">
              {a}
              <span className="not-italic text-gold/70 text-xl">§</span>
            </span>
          ))}
        </div>
      </div>
    </section>
  );
}

const STEPS = [
  { n: "I", title: "File the case", body: "Name the accused and the crime. A dramatic case file is drafted: charges, witnesses, exhibits that probably shouldn’t exist." },
  { n: "II", title: "Watch them argue", body: "Separate AI agents — judge, prosecutor, defense, defendant, witnesses — each with their own motives, voice, and secrets." },
  { n: "III", title: "The jury decides", body: "That’s you. Object, question the witness, vote. The verdict follows the record — and your vote weighs heavily." },
];

export function HowItWorks() {
  return (
    <section className="mx-auto w-full max-w-[1400px] px-4 py-24 sm:px-8">
      <div className="eyebrow">Rules of procedure</div>
      <div className="mt-8 grid gap-px overflow-hidden rounded-2xl border hairline bg-line md:grid-cols-3">
        {STEPS.map((s, i) => (
          <motion.div
            key={s.n}
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-80px" }}
            transition={{ delay: i * 0.08, duration: 0.6 }}
            className="bg-ink p-8 sm:p-10"
          >
            <div className="font-display text-6xl italic text-gold/80">{s.n}</div>
            <h3 className="mt-8 text-xl font-medium">{s.title}</h3>
            <p className="mt-3 leading-relaxed text-mute">{s.body}</p>
          </motion.div>
        ))}
      </div>
    </section>
  );
}

function tilt(e: React.PointerEvent<HTMLAnchorElement>) {
  const el = e.currentTarget;
  const r = el.getBoundingClientRect();
  const px = (e.clientX - r.left) / r.width - 0.5;
  const py = (e.clientY - r.top) / r.height - 0.5;
  el.style.transform = `perspective(900px) rotateY(${px * 7}deg) rotateX(${-py * 7}deg) translateZ(0)`;
  el.style.setProperty("--gx", `${(px + 0.5) * 100}%`);
  el.style.setProperty("--gy", `${(py + 0.5) * 100}%`);
}

export function CaseFileCard({ c, large = false }: { c: CaseSummary; large?: boolean }) {
  return (
    <Link
      onPointerMove={tilt}
      onPointerLeave={(e) => { e.currentTarget.style.transform = ""; }}
      style={{ backgroundImage: "radial-gradient(400px circle at var(--gx,50%) var(--gy,0%), rgb(214 174 98 / 0.10), transparent 60%)" }}
      href={`/case/${c.slug}`}
      className={cn(
        "group relative flex flex-col justify-between overflow-hidden rounded-2xl border hairline bg-ink-2 p-6 transition-[border-color,transform] duration-300 ease-out will-change-transform hover:border-gold/40",
        large ? "min-h-[300px] sm:p-8" : "min-h-[220px]",
      )}
    >
      <div className="flex items-start justify-between gap-4">
        <span className="font-mono text-[10px] tracking-[0.2em] text-mute">{c.case_number}</span>
        <span className={cn("rounded-full border px-2.5 py-1 font-mono text-[9px] uppercase tracking-[0.18em]",
          c.is_showcase ? "border-gold/50 text-gold" : "border-line-strong text-mute")}>
          {c.is_showcase ? "Showcase" : PHASE_LABEL[c.status] ?? c.status}
        </span>
      </div>
      <div>
        <h3 className={cn("font-display leading-[0.95] text-balance", large ? "text-5xl sm:text-6xl" : "text-3xl")}>
          {c.title || `The People vs. ${c.defendant}`}
        </h3>
        <p className="mt-3 line-clamp-2 text-sm text-mute">Charged with {c.accusation.replace(/\.$/, "").toLowerCase()}.</p>
      </div>
      <div className="mt-6 flex items-center justify-between font-mono text-[10px] uppercase tracking-[0.18em] text-ivory-dim">
        <span>{c.trial_length} trial · {c.comedy_intensity}</span>
        <span className="text-gold transition-transform group-hover:translate-x-1">Enter →</span>
      </div>
    </Link>
  );
}

export function Docket() {
  const { data, isError, isLoading } = useQuery({ queryKey: ["cases", "featured"], queryFn: () => api.listCases({ limit: 8 }) });
  const featured = (data ?? [])
    .filter((c) => c.is_featured || c.is_showcase)
    .sort((a, b) => Number(b.is_showcase) - Number(a.is_showcase));
  const [lead, ...rest] = featured;
  return (
    <section className="mx-auto w-full max-w-[1400px] px-4 pb-24 sm:px-8">
      <div className="flex items-end justify-between gap-6">
        <div>
          <div className="eyebrow">On the docket</div>
          <h2 className="mt-4 font-display text-5xl leading-none sm:text-6xl">Case of the day</h2>
        </div>
        <Link href="/docket" className="font-mono text-[11px] uppercase tracking-[0.18em] text-mute hover:text-ivory">All cases →</Link>
      </div>
      {isLoading && <div className="mt-10 grid gap-4 md:grid-cols-3">{[0, 1, 2].map((i) => <div key={i} className="h-[220px] animate-pulse rounded-2xl bg-ink-2" />)}</div>}
      {isError && (
        <p className="mt-10 rounded-2xl border border-burgundy/60 bg-burgundy/10 p-6 text-sm text-ivory-dim">
          The docket is unavailable — the backend isn’t reachable. Start it with <code className="font-mono text-gold">make dev</code>.
        </p>
      )}
      {lead && (
        <div className="mt-10 grid gap-4 lg:grid-cols-[1.4fr_1fr]">
          <CaseFileCard c={lead} large />
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-1">
            {rest.slice(0, 2).map((c) => <CaseFileCard key={c.id} c={c} />)}
          </div>
          {rest.length > 2 && (
            <div className="grid gap-4 sm:grid-cols-2 lg:col-span-2 lg:grid-cols-3">
              {rest.slice(2, 5).map((c) => <CaseFileCard key={c.id} c={c} />)}
            </div>
          )}
        </div>
      )}
    </section>
  );
}

export function Ensemble() {
  const crew = DEMO_CAST.filter((c) => ["judge", "prosecutor", "defense", "reporter"].includes(c.key));
  const lines: Record<string, string> = {
    judge: "“Overruled. But emotionally, I understand.”",
    prosecutor: "“Objection! The defendant has been going through something since 2019!”",
    defense: "“My client is not a villain. My client is misunderstood.”",
    reporter: "“The jury is deliberating. Snacks have not been provided.”",
  };
  return (
    <section className="border-t hairline">
      <div className="mx-auto w-full max-w-[1400px] px-4 py-24 sm:px-8">
        <div className="grid gap-10 lg:grid-cols-[1fr_2fr]">
          <div>
            <div className="eyebrow">The ensemble</div>
            <h2 className="mt-4 font-display text-5xl leading-[0.95] sm:text-6xl">
              A permanent cast. <span className="italic text-gold">Permanently exhausted.</span>
            </h2>
            <p className="mt-6 max-w-sm leading-relaxed text-mute">
              Four regulars with stable voices and long memories. Every case brings a new defendant and new witnesses —
              cast on the spot to fit the crime.
            </p>
          </div>
          <div className="grid grid-cols-2 gap-4 xl:grid-cols-4">
            {crew.map((c, i) => (
              <motion.div
                key={c.key}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-60px" }}
                transition={{ delay: i * 0.08, duration: 0.6 }}
                className="flex flex-col rounded-2xl border hairline bg-ink-2 p-4"
              >
                <div className="relative aspect-square overflow-hidden rounded-xl bg-[radial-gradient(circle_at_50%_30%,#2a2420,#121110)]">
                  <div className="absolute inset-x-[10%] bottom-0 top-[8%]">
                    <CharacterPortrait character={c} blinkDelay={i * 1.3} className="h-full w-full" />
                  </div>
                </div>
                <div className="mt-4 font-mono text-[10px] uppercase tracking-[0.18em] text-gold">{c.title}</div>
                <div className="mt-1 text-lg font-medium leading-tight">{c.name}</div>
                <p className="mt-3 font-display text-lg italic leading-snug text-ivory-dim">{lines[c.key]}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
