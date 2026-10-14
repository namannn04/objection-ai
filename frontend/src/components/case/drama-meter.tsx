"use client";

const LABELS: [number, string, string][] = [
  [20, "Restrained", "A raised eyebrow is a scandal."],
  [45, "Measured", "Occasional gasps. Polite outrage."],
  [70, "Theatrical", "Pauses you could park a car in."],
  [90, "Operatic", "Every objection is a season finale."],
  [101, "Unhinged", "Someone will faint. Possibly the gavel."],
];

/** DramaMeter: steers script direction and performance instructions — not a precise emotion parameter. */
export function DramaMeter({ value, onChange }: { value: number; onChange: (v: number) => void }) {
  const [, label, hint] = LABELS.find(([max]) => value < max) ?? LABELS[LABELS.length - 1];
  return (
    <div>
      <div className="flex items-baseline justify-between">
        <span className="eyebrow">Drama meter</span>
        <span className="font-mono text-xs text-mute">{value}/100</span>
      </div>
      <div className="mt-3 flex items-baseline gap-3">
        <span className="font-display text-3xl italic text-gold">{label}</span>
        <span className="text-sm text-mute">{hint}</span>
      </div>
      <input
        type="range"
        min={1}
        max={100}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        aria-label="Drama meter"
        className="drama-range mt-4 w-full"
        style={{ "--fill": `${value}%` } as React.CSSProperties}
      />
      <p className="mt-2 text-xs text-mute">Shapes how theatrical the script and the voice direction get.</p>
    </div>
  );
}
