"""Offline line library: what each agent says when no LLM is available, or when
live generation fails. Lines are templates over the case profile, picked with a
seeded RNG so a case always replays identically.
"""

from __future__ import annotations

import random
from typing import Any

# Each variant: (text, emotion, delivery, intensity, pause_before_ms)
V = tuple[str, str, str, int, int]

LINES: dict[str, list[V]] = {
    # ── opening ──────────────────────────────────────────────────────────
    "intro": [
        ("Good evening, and welcome to The Court of Absolute Nonsense, where nothing is too small to sue. [pause] Tonight: The People versus {D}. Please silence your phones. They may be called as witnesses.", "deadpan", "crisp late-night broadcast voice, dry and amused", 2, 0),
        ("You're listening to The Court of Absolute Nonsense. [pause] Tonight's defendant: {d}. Tonight's charge: {crime}. Tonight's judge: deeply tired. Let's go to the courtroom.", "deadpan", "crisp late-night broadcast voice, dry and amused", 2, 0),
    ],
    "open_court": [
        ("[clears throat] Order. This court is now in session. Case number {case_number}: The People versus {D}. The charge: {crime}. [pause] I have read the file. Twice. I would like those hours back.", "stern", "slow, grave, utterly unamused", 3, 0),
        ("Be seated. We are here today because {D} stands accused of {crime}. [pause] I have presided over this court for thirty-one years, and I have never been more prepared to be disappointed.", "deadpan", "measured, bone-dry, every word a sigh", 3, 0),
    ],
    "opening_statement:prosecutor": [
        ("Your Honor, members of the jury. [pause] What you are about to hear is not a story. It is a *tragedy*. {D} is charged with {crime}, and the People will prove it was not an accident. It was a *lifestyle*.", "dramatic", "building, theatrical, as if addressing a stadium", 4, 300),
        ("Ladies and gentlemen, picture an ordinary day. Birds singing. Hope in the air. And then — [pause] {D}. The People will show, beyond any reasonable doubt, that the defendant is guilty of {crime}. Every. Single. Time.", "dramatic", "starts soft, ends at a roar", 5, 300),
    ],
    "opening_statement:defense": [
        ("[chuckle] Bold words from my colleague. Your Honor, my client is not a villain. My client is *misunderstood*. And frankly, if we start prosecuting everything that ruins someone's day, we will need a bigger courthouse.", "smug", "smooth, unhurried, a velvet sneer", 3, 200),
        ("Your Honor, the prosecution wants a villain. What they have is a scapegoat. My client, {d}, has been blamed for everything since the day it arrived, and today, [pause] that ends.", "smug", "silky, confident, leaning on the railing", 3, 200),
    ],
    "introduce_self": [
        ("{excuse}", "sad", "{defendant_voice}, wounded", 3, 400),
        ("[sigh] I would like it on the record that I was only doing my job. {alibi}", "proud", "{defendant_voice}", 3, 400),
    ],
    "react_to_defendant": [
        ("[long pause] Noted. The record will reflect that the defendant said that out loud, in a court of law, on purpose.", "deadpan", "flat, glacial, a long blink before speaking", 2, 900),
        ("[pause] The defendant will refrain from making this court feel things. Proceed.", "stern", "clipped and cold, with the faintest crack of sympathy", 2, 800),
    ],
    # ── evidence ─────────────────────────────────────────────────────────
    "present_evidence": [
        ("The People submit Exhibit {ev_id}: {ev_title}. [pause] {ev_desc} I'll give the jury a moment to *process* that.", "triumphant", "slow reveal, savouring every syllable", 4, 300),
        ("Exhibit {ev_id}, Your Honor. {ev_title}. {ev_desc} [pause] I rest my case. [pause] I don't, actually, but I wanted to see how it felt.", "smug", "showy, holding the exhibit aloft", 4, 300),
        ("If it please the court: Exhibit {ev_id}. {ev_title}. {ev_desc} [pause] I have had this framed.", "triumphant", "reverent, like unveiling a painting", 4, 300),
        ("Exhibit {ev_id}. {ev_title}. [pause] {ev_desc} Read it again. Slowly. Let it *hurt*.", "dramatic", "low and intense, tapping the exhibit", 5, 300),
    ],
    "excuse": [
        ("That is taken out of context! {alibi}", "desperate", "{defendant_voice}, voice cracking", 4, 0),
        ("[scoff] Okay, but nobody mentions the times I *didn't* do it. Where's the exhibit for those?", "nervous", "{defendant_voice}, defensive and fast", 3, 0),
    ],
    "object_to_evidence": [
        ("Objection! Your Honor, Exhibit {ev_id} is pure speculation. My client was never read its rights. Mostly because it doesn't have ears.", "angry", "sharp, sudden, slamming the desk", 4, 0),
        ("Objection! Relevance! Also hearsay. Also, and I cannot stress this enough, *rude*.", "angry", "sharp interruption, rising pitch", 4, 0),
    ],
    "rule_on_objection": [
        ("Overruled. [pause] But emotionally, Counsel, I understand.", "deadpan", "dry, a beat of hidden sympathy at the end", 2, 600),
        ("Overruled. Rudeness is not a legal standard. If it were, this entire courtroom would be in contempt.", "stern", "brisk, bored, gavel-ready", 3, 500),
    ],
    "reveal_twist": [
        ("Then perhaps the People can explain Exhibit {ev_id}: {ev_title}. [pause] Because it proves something very interesting. {twist}", "triumphant", "quiet, deliberate, enjoying the silence that follows", 4, 400),
    ],
    "react_to_twist": [
        ("That — [pause] that is irrelevant! And also, how did you get that?", "shocked", "flustered, losing composure, voice climbing", 5, 300),
        ("Your Honor, I — [pause] the People would like a moment. A long one. Possibly a weekend.", "shocked", "stammering, deflated", 4, 300),
    ],
    "restore_order": [
        ("Order! [pause] Order in this court. Nobody gasps in my courtroom without permission, and nobody has permission.", "angry", "booming, gavel-adjacent", 4, 0),
        ("Order. I will have silence. [pause] Thank you. That twist was very upsetting and I would like everyone to be normal now.", "stern", "firm, then oddly tender", 3, 0),
    ],
    # ── witness examination ──────────────────────────────────────────────
    "call_witness": [
        ("The People call {w}. [pause] {W_voc}, in your own words, what did you witness?", "serious", "crisp, professional, suspiciously gentle", 3, 0),
        ("The People call {w} to the stand. [pause] Tell the court what you saw. Take your time. Not too much time.", "serious", "formal, efficient", 2, 0),
    ],
    "testify": [
        ("{w_knows} [pause] I remember it like it was yesterday. It was yesterday.", "nervous", "{witness_voice}", 3, 200),
        ("[sigh] I was there. {w_knows} I haven't been the same since.", "sad", "{witness_voice}, haunted", 3, 300),
    ],
    "leading_question": [
        ("And would you say, under oath, that {d} is the worst thing that has ever happened to anyone?", "dramatic", "leaning in, wide-eyed, almost whispering", 4, 0),
        ("So you're telling this court that {d} knew exactly what it was doing. Yes or yes?", "dramatic", "rapid-fire, pacing", 4, 0),
    ],
    "overshare": [
        ("I mean — yes? And also, since we're here, I have *feelings* about the whole household and I've been holding them in.", "nervous", "{witness_voice}, words tumbling out", 3, 300),
        ("Absolutely. Can I also say something unrelated? [pause] No? Okay. It's about the toaster. Another time.", "confused", "{witness_voice}", 3, 300),
    ],
    # ── cross-examination ────────────────────────────────────────────────
    "cross_examine": [
        ("{W_voc}. [pause] Isn't it true that you weren't exactly innocent yourself? Think carefully. You are under oath, and I have a highlighter.", "smug", "slow circling, silky menace", 4, 200),
        ("Just one question, {W_voc}. Where were *you* on the night in question?", "smug", "casual, deadly, almost bored", 4, 200),
    ],
    "contradict_self": [
        ("I — [pause] okay, fine. {w_slip} But that's not the point!", "shocked", "{witness_voice}, cracking under pressure", 5, 500),
        ("[gasp] How did you — [pause] alright! {w_slip} Are you happy now?", "desperate", "{witness_voice}, collapsing", 5, 400),
    ],
    "outraged_objection": [
        ("Objection! Counsel is badgering my witness! With *facts*!", "angry", "shrill, outraged", 5, 0),
        ("Objection! That answer was not helpful to my case, Your Honor!", "angry", "indignant, too loud", 4, 0),
    ],
    "overrule_and_scold": [
        ("Overruled. Facts are allowed in this courtroom. Rarely, but they are allowed.", "deadpan", "bone-dry, unblinking", 2, 600),
        ("Overruled. Sit down, Counsel. You can be upset quietly, like the rest of us.", "stern", "weary authority", 3, 500),
    ],
    # ── surprise witness ─────────────────────────────────────────────────
    "call_surprise_witness": [
        ("Your Honor, the defense calls a surprise witness. [pause] {S}.", "triumphant", "theatrical, savouring the reveal", 4, 300),
    ],
    "allow_surprise": [
        ("[pause] This is highly irregular. [pause] I'll allow it, because I want to see what happens.", "deadpan", "stern, with suppressed curiosity", 3, 500),
    ],
    "surprise_testimony": [
        ("[clears throat] I have waited a long time to say this. {s_knows} [pause] {s_slip}", "dramatic", "{surprise_voice}", 4, 300),
    ],
    "react_to_surprise": [
        ("[gasp] I knew it. I always knew it. {Gag0}!", "triumphant", "{defendant_voice}, vindicated", 4, 200),
        ("You see? *You see?* Nobody ever believes me. {Gag0}, Your Honor. {Gag0}!", "dramatic", "{defendant_voice}, emotional", 4, 200),
    ],
    # ── closing ──────────────────────────────────────────────────────────
    "closing_argument:prosecutor": [
        ("Members of the jury, you've heard the evidence. You've seen Exhibit {ev_id}. You've heard the words '{gag0}' spoken under oath. [pause] Do the right thing. Find {d} guilty of {crime}.", "dramatic", "slow build to a thunderous finish", 5, 300),
    ],
    "closing_argument:defense": [
        ("My colleague wants a villain. But the evidence shows something else: {twist_short} [pause] My client is many things. But guilty? [pause] Only of being *convenient to blame*.", "smug", "quiet, intimate, then a soft knockout punch", 4, 300),
    ],
    "last_words": [
        ("[long pause] I just want everyone to know: {excuse}", "sad", "{defendant_voice}, small and sincere", 3, 1200),
        ("[pause] I'd like to say something. [pause] {Gag1}. That's it. That's my statement.", "deadpan", "{defendant_voice}", 2, 1200),
    ],
    # ── deliberation ─────────────────────────────────────────────────────
    "recap": [
        ("For those just tuning in: {d} has been accused of {crime}, the prosecution has wept twice, and {w} has said things under oath that cannot be unsaid. The jury is now deliberating. Snacks have not been provided.", "deadpan", "dry broadcast voice, crisp and amused", 2, 300),
    ],
    "deliberate": [
        ("[long pause] The court has weighed the evidence. The court has weighed the testimony. [pause] The court has also weighed whether to retire early. Let's proceed.", "deadpan", "slow, ceremonial, faintly exhausted", 3, 800),
    ],
    # ── verdict ──────────────────────────────────────────────────────────
    "verdict_guilty": [
        ("Will the defendant please rise. [pause] On the charge of {crime}, this court finds {d}: [long pause] *guilty*.", "stern", "slow, enormous, each word a gavel strike", 5, 600),
    ],
    "verdict_not_guilty": [
        ("Will the defendant please rise. [pause] On the charge of {crime}, this court finds {d}: [long pause] *not guilty*. [pause] Reluctantly.", "stern", "slow, enormous, with a final grudging sigh", 5, 600),
    ],
    "sentence": [
        ("{D} is hereby {sentence_lower} [pause] Court is adjourned. Somebody please open a window.", "deadpan", "formal, unhurried, then abruptly done", 3, 400),
    ],
    "dismissal": [
        ("{acquittal} [pause] The defendant is free to go. Do not make me regret this. I already do.", "deadpan", "dry, tired, faintly fond", 3, 400),
    ],
    "react_guilty": [
        ("[gasp] This is a miscarriage of justice! [pause] ...Can I at least keep my dignity? [pause] No? Okay.", "desperate", "{defendant_voice}, crumbling", 5, 300),
    ],
    "react_acquitted": [
        ("[laugh] I'm free! I'm *free*! [pause] I'd like to thank my lawyer, my witnesses, and everyone who said '{gag0}'.", "triumphant", "{defendant_voice}, giddy", 5, 300),
    ],
    "outro": [
        ("And that's the ruling. Justice has been served, mostly. This has been The Court of Absolute Nonsense. [pause] Please exit through the gift shop.", "deadpan", "warm sign-off, crisp and wry", 2, 400),
    ],
}

# Responses to pre-generated intervention options
RESPONSES: dict[str, list[V]] = {
    "sustained": [
        ("Sustained. [pause] The jury will disregard that. The jury will not, but they've been told.", "deadpan", "dry, faintly pleased", 2, 400),
        ("Sustained. Finally, someone in this room with standards.", "stern", "approving, crisp", 3, 400),
    ],
    "overruled": [
        ("Overruled. Nice try, though. I mean that. I don't.", "deadpan", "flat, unbothered", 2, 400),
        ("Overruled. The objection is creative, but this is a courtroom, not a writing workshop.", "stern", "brisk, unimpressed", 3, 400),
    ],
    "retort_prosecutor": [
        ("Your Honor, the jury is clearly *emotionally compromised* by the truth.", "angry", "indignant, sputtering", 4, 0),
    ],
    "retort_defense": [
        ("[chuckle] The jury has excellent taste, Your Honor.", "smug", "smooth, delighted", 3, 0),
    ],
    "vote_ack:prosecution": [
        ("The jury leans toward the prosecution. [pause] The defense will try to look less smug.", "deadpan", "dry aside", 2, 200),
    ],
    "vote_ack:defense": [
        ("The jury leans toward the defense. [pause] The prosecution will stop sulking. Immediately.", "deadpan", "dry aside", 2, 200),
    ],
}


def _norm(text: str) -> str:
    import re

    return re.sub(r"[^a-z]+", " ", re.sub(r"\{[^}]*\}|\[[^\]]*\]", " ", text.lower())).strip()


class _SafeDict(dict):
    def __missing__(self, key: str) -> str:
        return ""


def pick(
    table: dict[str, list[V]], intent: str, who: str, ctx: dict[str, Any], rnd: random.Random,
    used: set[str] | None = None,
) -> V:
    variants = table.get(f"{intent}:{who}") or table.get(intent)
    if not variants:
        variants = [("[pause] The court notes the moment.", "deadpan", "dry", 2, 0)]
    order = list(variants)
    rnd.shuffle(order)
    if used:
        # Prefer a variant whose template hasn't been performed yet in this trial.
        fresh = [v for v in order if _norm(v[0])[:40] not in used]
        order = fresh or order
    text, emotion, delivery, intensity, pause = order[0]
    if used is not None:
        used.add(_norm(text)[:40])
    fmt = _SafeDict(ctx)
    return (
        text.format_map(fmt).replace("  ", " ").strip(),
        emotion,
        delivery.format_map(fmt)[:160],
        intensity,
        pause,
    )
