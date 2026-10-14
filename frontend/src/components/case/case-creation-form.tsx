"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery } from "@tanstack/react-query";
import { AnimatePresence, motion } from "motion/react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm, useWatch } from "react-hook-form";
import { z } from "zod";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { DramaMeter } from "./drama-meter";

const schema = z.object({
  defendant: z.string().trim().min(2, "Name the accused.").max(120),
  accusation: z.string().trim().min(4, "Tell the court what they did.").max(500),
  context: z.string().max(1000).optional(),
  language: z.string(),
  comedy_intensity: z.enum(["mild", "unserious", "chaos"]),
  drama_level: z.number().min(1).max(100),
  trial_length: z.enum(["quick", "standard", "full"]),
  participation_mode: z.enum(["spectator", "jury", "chaos"]),
});
type FormValues = z.infer<typeof schema>;

const SUSPECTS = ["Monday mornings", "My Wi-Fi", "JavaScript", "My alarm clock", "The printer", "My phone battery", "Group projects", "The snooze button"];
const CRIMES: Record<string, string> = {
  "Monday mornings": "Crimes against humanity, fifty-two times a year",
  "My Wi-Fi": "Disappearing during every important meeting",
  JavaScript: "Causing emotional damage through undefined behavior",
  "My alarm clock": "Destroying my dreams every single morning",
  "The printer": "Jamming only when I'm already late",
  "My phone battery": "Betraying me at 1% during navigation",
  "Group projects": "Making me do everyone's part, again",
  "The snooze button": "Ruining my career, nine minutes at a time",
};

const INTENSITY = [
  { v: "mild", t: "Mildly ridiculous", d: "Dry, deadpan, quietly absurd." },
  { v: "unserious", t: "Completely unserious", d: "Silly, escalating, theatrical." },
  { v: "chaos", t: "Maximum courtroom chaos", d: "Everyone objects to everything." },
] as const;
const LENGTH = [
  { v: "quick", t: "Quick hearing", d: "≈ 3 min · one witness" },
  { v: "standard", t: "Standard trial", d: "≈ 5 min · twist + surprise witness" },
  { v: "full", t: "Full dramatic episode", d: "≈ 7 min · two witnesses" },
] as const;
const MODES = [
  { v: "spectator", t: "Spectator", d: "Sit back. Watch justice happen." },
  { v: "jury", t: "Jury member", d: "Vote, object, question witnesses." },
  { v: "chaos", t: "Chaos mode", d: "Type your own objections. Live." },
] as const;
// Typical script size per length (all lines incl. pre-generated branches), for a pre-script projection.
const TYPICAL_CHARS = { quick: 4600, standard: 6600, full: 8800 };

const STEP_TITLES = ["Who are we suing today?", "Tell the court what this menace has done.", "How much nonsense can you handle?"];

export function CaseCreationForm() {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const settings = useQuery({ queryKey: ["settings"], queryFn: api.settings });
  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      defendant: "", accusation: "", context: "", language: "en", comedy_intensity: "unserious",
      drama_level: 65, trial_length: "quick", participation_mode: "jury",
    },
  });
  const values = useWatch({ control: form.control });
  const create = useMutation({
    mutationFn: api.createCase,
    onSuccess: (r) => router.push(`/case/${r.case.slug}`),
  });

  const next = async () => {
    const fields: (keyof FormValues)[][] = [["defendant"], ["accusation", "context"], []];
    if (await form.trigger(fields[step])) setStep((s) => Math.min(2, s + 1));
  };
  const submit = form.handleSubmit((v) => create.mutate({ ...v, context: v.context || "" }));

  const audio = settings.data?.defaults.audio ?? "mock";
  const paid = audio === "drama3";
  const projectedChars = TYPICAL_CHARS[values.trial_length ?? "quick"];

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        if (step < 2) void next();
        else void submit();
      }}
      className="mx-auto w-full max-w-[1100px]"
    >
      <div className="flex items-center gap-3">
        {STEP_TITLES.map((_, i) => (
          <button
            type="button"
            key={i}
            onClick={() => i < step && setStep(i)}
            className={cn("h-1 flex-1 rounded-full transition-colors duration-500", i <= step ? "bg-gold" : "bg-ink-4")}
            aria-label={`Step ${i + 1}`}
          />
        ))}
      </div>
      <div className="mt-4 flex justify-between font-mono text-[10px] uppercase tracking-[0.2em] text-mute">
        <span>Form CR-1 · Complaint of absolute nonsense</span>
        <span>Step {step + 1} of 3</span>
      </div>

      <AnimatePresence mode="wait">
        <motion.div
          key={step}
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -12 }}
          transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
          className="mt-12"
        >
          <h1 className="font-display text-[clamp(2.6rem,6vw,5.6rem)] leading-[0.92] text-balance">
            {step === 0 ? <>Who are we <span className="italic text-gold">suing</span> today?</> : step === 1 ? <>Tell the court what this <span className="italic text-gold">menace</span> has done.</> : <>How much <span className="italic text-gold">nonsense</span> can you handle?</>}
          </h1>

          {step === 0 && (
            <div className="mt-12">
              <input
                {...form.register("defendant")}
                autoFocus
                autoComplete="off"
                placeholder="Monday mornings, my Wi-Fi, JavaScript, my alarm clock…"
                className="w-full border-b border-line-strong bg-transparent pb-4 font-display text-3xl text-ivory placeholder:text-ink-4 focus:border-gold focus:outline-none sm:text-5xl"
                aria-label="Who or what is being accused"
              />
              <FieldError msg={form.formState.errors.defendant?.message} />
              <div className="mt-8 flex flex-wrap gap-2">
                {SUSPECTS.map((s) => (
                  <button
                    type="button"
                    key={s}
                    onClick={() => {
                      form.setValue("defendant", s, { shouldValidate: true });
                      if (!form.getValues("accusation")) form.setValue("accusation", CRIMES[s]);
                    }}
                    className={cn(
                      "rounded-full border px-4 py-2 text-sm transition-colors",
                      values.defendant === s ? "border-gold bg-gold/10 text-gold" : "border-line-strong text-ivory-dim hover:border-ivory/40",
                    )}
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          {step === 1 && (
            <div className="mt-12 grid gap-8">
              <div>
                <label className="eyebrow">The accusation</label>
                <textarea
                  {...form.register("accusation")}
                  autoFocus
                  rows={2}
                  placeholder="Destroying my dreams every single morning."
                  className="mt-3 w-full resize-none border-b border-line-strong bg-transparent pb-3 font-display text-3xl leading-tight text-ivory placeholder:text-ink-4 focus:border-gold focus:outline-none sm:text-4xl"
                />
                <FieldError msg={form.formState.errors.accusation?.message} />
              </div>
              <div>
                <label className="eyebrow">Additional context for the court (optional)</label>
                <textarea
                  {...form.register("context")}
                  rows={2}
                  placeholder="It rang during my only good dream this year."
                  className="mt-3 w-full resize-none rounded-xl border border-line bg-ink-2 p-4 text-ivory placeholder:text-mute/50 focus:border-gold focus:outline-none"
                />
                <p className="mt-2 text-xs text-mute">Everything is fictional. Please keep real private people out of it — the court only tries things, concepts and archetypes.</p>
              </div>
            </div>
          )}

          {step === 2 && (
            <div className="mt-12 grid gap-10">
              <ChoiceRow label="Comedy intensity" options={INTENSITY} value={values.comedy_intensity} onChange={(v) => form.setValue("comedy_intensity", v as FormValues["comedy_intensity"])} />
              <DramaMeter value={values.drama_level ?? 65} onChange={(v) => form.setValue("drama_level", v)} />
              <ChoiceRow label="Trial length" options={LENGTH} value={values.trial_length} onChange={(v) => form.setValue("trial_length", v as FormValues["trial_length"])} />
              <ChoiceRow label="Your role" options={MODES} value={values.participation_mode} onChange={(v) => form.setValue("participation_mode", v as FormValues["participation_mode"])} />
              <div className="grid gap-4 rounded-2xl border hairline bg-ink-2 p-5 sm:grid-cols-[1fr_auto] sm:items-center">
                <div>
                  <div className="eyebrow">Voices & budget</div>
                  {paid ? (
                    <p className="mt-2 text-sm text-ivory-dim">
                      Drama 3 voices. A {values.trial_length} trial is typically ~{projectedChars.toLocaleString()} characters ≈{" "}
                      <span className="text-gold">${((projectedChars * 50) / 1e6).toFixed(2)}</span> at list price. Nothing is
                      spent until you review the exact estimate and confirm.
                    </p>
                  ) : (
                    <p className="mt-2 text-sm text-ivory-dim">
                      {audio === "fish-free" ? "Fish Audio S2.1 Pro Free voices" : "Local mock voices"} — <span className="text-gold">$0.00</span>. No paid credits are used.
                    </p>
                  )}
                </div>
                <div className="flex flex-col items-end gap-1">
                <select
                  {...form.register("language")}
                  className="rounded-lg border border-line-strong bg-ink px-3 py-2 text-sm text-ivory"
                  aria-label="Language"
                >
                  <option value="en">English</option>
                  <option value="es">Español</option>
                  <option value="fr">Français</option>
                  <option value="de">Deutsch</option>
                  <option value="hi">हिन्दी</option>
                  <option value="ja">日本語</option>
                </select>
                {values.language !== "en" && settings.data?.defaults.llm === "mock" && (
                  <span className="max-w-[220px] text-right text-[11px] text-mute">The offline engine writes in English. Pick Ollama or Claude in Settings for other languages.</span>
                )}
                </div>
              </div>
            </div>
          )}
        </motion.div>
      </AnimatePresence>

      <div className="mt-14 flex items-center justify-between gap-4">
        <button
          type="button"
          onClick={() => setStep((s) => Math.max(0, s - 1))}
          className={cn("font-mono text-[11px] uppercase tracking-[0.2em] text-mute hover:text-ivory", step === 0 && "invisible")}
        >
          ← Back
        </button>
        <div className="flex items-center gap-4">
          {create.isError && <span className="text-sm text-burgundy-bright">{(create.error as Error).message}</span>}
          <button
            type="submit"
            disabled={create.isPending}
            className="rounded-full bg-gold px-8 py-4 text-[15px] font-semibold text-ink transition-transform hover:-translate-y-0.5 disabled:opacity-60"
          >
            {step < 2 ? "Continue →" : create.isPending ? "Filing…" : "File the case"}
          </button>
        </div>
      </div>
    </form>
  );
}

function FieldError({ msg }: { msg?: string }) {
  return msg ? <p className="mt-2 text-sm text-burgundy-bright">{msg}</p> : null;
}

function ChoiceRow({ label, options, value, onChange }: {
  label: string; options: readonly { v: string; t: string; d: string }[]; value?: string; onChange: (v: string) => void;
}) {
  return (
    <fieldset>
      <legend className="eyebrow">{label}</legend>
      <div className="mt-3 grid gap-3 sm:grid-cols-3">
        {options.map((o) => (
          <button
            type="button"
            key={o.v}
            onClick={() => onChange(o.v)}
            aria-pressed={value === o.v}
            className={cn(
              "rounded-xl border p-4 text-left transition-colors",
              value === o.v ? "border-gold bg-gold/[0.07]" : "border-line hover:border-line-strong",
            )}
          >
            <div className={cn("font-medium", value === o.v ? "text-gold" : "text-ivory")}>{o.t}</div>
            <div className="mt-1 text-sm text-mute">{o.d}</div>
          </button>
        ))}
      </div>
    </fieldset>
  );
}
