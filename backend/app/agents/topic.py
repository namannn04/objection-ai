"""Topic analysis for the offline comedy engine.

Turns "my alarm clock" + "destroying my dreams" into a profile the scripted
agents can riff on: what kind of thing the defendant is, plausible witnesses,
evidence, a surprise witness, and a fitting harmless punishment.
"""

from __future__ import annotations

import hashlib
import random
import re
from dataclasses import dataclass, field


@dataclass(slots=True)
class WitnessIdea:
    name: str
    relationship: str
    personality: str
    knows: str
    slip: str  # the contradiction they accidentally reveal
    glyph: str = ""
    palette: str = "teal"


@dataclass(slots=True)
class TopicProfile:
    defendant: str  # "The Office Wi-Fi"
    short: str  # "the Wi-Fi"
    kind: str  # object | tech | concept | time | person
    glyph: str
    crime: str  # "disappearing during important meetings"
    defendant_personality: str
    defendant_voice: str
    alibi: str
    excuse: str
    witnesses: list[WitnessIdea]
    surprise: WitnessIdea
    evidence: list[tuple[str, str, str, str]]  # (title, description, kind, favours)
    twist: str
    gags: list[str]
    guilty_sentence: str
    acquittal_note: str
    seed: int = 0
    extras: dict = field(default_factory=dict)


def seed_for(*parts: str) -> int:
    return int(hashlib.sha256("|".join(parts).encode()).hexdigest()[:8], 16)


def third_person(accusation: str) -> str:
    """'destroying my dreams' → "destroying the plaintiff's dreams"."""
    s = accusation.strip().rstrip(".!")
    s = re.sub(r"^(for|of)\s+", "", s, flags=re.I)
    repl = [
        (r"\bmy\b", "the plaintiff's"),
        (r"\bme\b", "the plaintiff"),
        (r"\bI am\b", "the plaintiff is"),
        (r"\bI'm\b", "the plaintiff is"),
        (r"\bI\b", "the plaintiff"),
        (r"\bmine\b", "the plaintiff's"),
        (r"\bmyself\b", "the plaintiff"),
        (r"\bour\b", "the plaintiffs'"),
        (r"\bus\b", "the plaintiffs"),
        (r"\bwe\b", "the plaintiffs"),
    ]
    for pat, rep in repl:
        s = re.sub(pat, rep, s)
    return s[0].lower() + s[1:] if s else "crimes against reasonable expectations"


def display_name(defendant: str) -> tuple[str, str]:
    d = defendant.strip().rstrip(".")
    d = re.sub(r"^(my|our|the)\s+", "", d, flags=re.I)
    d = " ".join(w if any(c.isupper() for c in w) else w[:1].upper() + w[1:] for w in d.split())
    person_words = ("friend", "boss", "roommate", "brother", "sister", "neighbour", "neighbor", "coworker", "person", "guy", "cousin", "partner", "landlord")
    is_person = any(w in d.lower() for w in person_words)
    proper = d[:1].isupper() and " " not in d and d.lower() not in _COMMON
    if is_person:
        return f"The {d}", f"the {d.lower()}"
    if proper and d.lower() in _PROPER_NOUNS:
        return d, d
    return f"The {d}", f"the {d.lower()}"


_COMMON = {"monday", "wifi", "wi-fi"}
_PROPER_NOUNS = {"javascript", "python", "typescript", "java", "excel", "windows", "bluetooth", "css", "php", "monday", "friday", "gravity", "autocorrect"}


# Keyword-specific casting. Order matters: first match wins.
_PACKS: list[tuple[tuple[str, ...], dict]] = [
    (
        ("alarm", "snooze"),
        dict(
            kind="object", glyph="⏰",
            personality="Punctual to a fault, smug about it, claims it was only doing its job.",
            voice="crisp, metallic, relentlessly chipper",
            alibi="I rang at exactly the time I was told. Seven times. I have receipts.",
            excuse="I don't make the rules, I just enforce them. Loudly.",
            witnesses=[
                WitnessIdea("The Snooze Button", "Accomplice. Pressed nine times on the morning in question.", "Sleepy, guilty, keeps yawning mid-sentence.", "I was pressed nine times between six and six forty-five. Gently. Lovingly.", "Okay, fine! I'm the one who made them late. Every press was a choice. *My* choice.", "Zz", "violet"),
                WitnessIdea("The Coffee Mug", "First responder at the scene of the morning.", "Bitter, warm-hearted underneath, deeply caffeinated.", "The plaintiff staggered in at 8:52 holding me like a life raft.", "...They went to bed at 3 AM watching otter videos. I was there. I was the otter-video mug.", "☕", "ember"),
            ],
            surprise=WitnessIdea("Saturday", "The only day the defendant has ever been silent.", "Relaxed, smug, wearing pajamas.", "I have never once heard that alarm ring. Not once. I am a day of peace.", "And between us? The plaintiff whispers my name every night at 3 AM while setting that alarm.", "SAT", "moss"),
            evidence=[
                ("Ringing log, 06:00–06:45", "An itemised record of nine rings, each politely ignored.", "log", "prosecution"),
                ("A dream, interrupted", "A sworn affidavit describing a dream about winning a cooking show, cut off mid-applause.", "document", "prosecution"),
                ("The settings screen", "A screenshot proving the alarm was set by the plaintiff's own thumb.", "photo", "defense"),
            ],
            twist="The alarm was set to 6:00 AM by the plaintiff, at 3:07 AM, while saying 'future me will handle it.'",
            gags=["future me will handle it", "nine snoozes", "the cooking show dream"],
            sentence="Sentenced to ring only in a gentle whisper of ocean sounds for six months, and to apologise to every dream it has ever interrupted.",
            acquittal="The court finds the true culprit was the plaintiff's own bedtime.",
        ),
    ),
    (
        ("wi-fi", "wifi", "internet", "router", "connection"),
        dict(
            kind="tech", glyph="WiFi",
            personality="Emotionally unavailable, unreliable, insists it was 'going through something'.",
            voice="breathy, distant, prone to cutting out mid-word",
            alibi="I was there. Spiritually. At one bar.",
            excuse="Your Honor, I was going through something.",
            witnesses=[
                WitnessIdea("The Router", "The defendant's roommate and enabler.", "Blinks nervously, over-explains, deeply loyal.", "My lights were blinking orange the entire meeting. Orange means *trouble*.", "Fine! I've been streaming cat videos on the side. Four hours a day. For my mental health!", "📶", "teal"),
                WitnessIdea("The Muted Microphone", "Witnessed the entire meeting in silence.", "Bitter, ignored, finally given a chance to speak.", "I heard the plaintiff say 'can you hear me now' eleven times.", "...I was muted. The whole time. The Wi-Fi was fine. Nobody could hear them because of *me*.", "🎙", "slate"),
            ],
            surprise=WitnessIdea("The Ethernet Cable", "The defendant's estranged, reliable older sibling.", "Stoic, dependable, slightly smug.", "I have been in a drawer since 2019. Available. The entire time.", "Nobody. Ever. Plugged me in. Do you know what that does to a cable?", "RJ45", "gold"),
            evidence=[
                ("Disconnection timeline", "Seventeen drops, each perfectly timed to the moment the plaintiff started presenting.", "chart", "prosecution"),
                ("Frozen screenshot", "A video call frozen on the plaintiff's least flattering face.", "photo", "prosecution"),
                ("Router power log", "A suspicious 40-minute gap labelled only 'vacuum'.", "log", "defense"),
            ],
            twist="The router was unplugged by the plaintiff to charge a robot vacuum named Gerald.",
            gags=["going through something", "one bar", "Gerald the vacuum"],
            sentence="Sentenced to three months of uninterrupted connectivity, including in the bathroom and the far corner of the bedroom.",
            acquittal="The court finds Gerald the vacuum to be a person of interest.",
        ),
    ),
    (
        ("monday",),
        dict(
            kind="time", glyph="MON",
            personality="Cold, unapologetic, proud, and convinced everyone secretly needs it.",
            voice="flat, bureaucratic, unbothered",
            alibi="I arrive every week. Like clockwork. Literally.",
            excuse="Without me, the weekend means nothing. I am the contrast that makes joy possible.",
            witnesses=[
                WitnessIdea("Sunday Night", "The defendant's herald. Arrives with dread.", "Anxious, melancholic, speaks in sighs.", "I delivered the Sunday scaries at 9:40 PM, as is tradition.", "...Okay. The dread was mine. Monday just shows up and takes the credit.", "SUN", "violet"),
                WitnessIdea("The Office Coffee Machine", "Stationed at the scene every Monday morning.", "Overworked, gurgling, cynical.", "I was empty at 9:01 AM. As I am every Monday. It is a sacred ritual.", "Fine! I break down on Fridays too. Nobody notices because everyone is happy.", "☕", "ember"),
            ],
            surprise=WitnessIdea("Friday", "The defendant's rival. Beloved by everyone.", "Charismatic, smug, wearing sunglasses indoors.", "I would never treat anyone this way. People *love* me. I have a song.", "...I may have scheduled a 4:55 PM meeting. Once. Or every week. It's a quick sync.", "FRI", "gold"),
            evidence=[
                ("Calendar exhibit", "Fifty-two documented occurrences per year, without consent.", "document", "prosecution"),
                ("The 9 AM all-hands invite", "Sent by Monday itself. Subject line: 'Quick sync'. It was not quick.", "document", "prosecution"),
                ("Productivity chart", "Mondays account for 31% of all to-do lists ever finished.", "chart", "defense"),
            ],
            twist="Monday has never scheduled a single meeting. Every invite was sent by Sunday Night, impersonating it.",
            gags=["quick sync", "the scaries", "fifty-two times a year"],
            sentence="Sentenced to start at 11 AM for one calendar year, and to bring pastries.",
            acquittal="The court finds that Monday is merely the messenger, and Sunday Night has some explaining to do.",
        ),
    ),
    (
        ("javascript", " js", "typescript"),
        dict(
            kind="tech", glyph="JS",
            personality="Chaotic, defensive, and convinced every bug is a feature.",
            voice="fast, slippery, wildly confident",
            alibi="Technically, [1] + [1] being '11' is correct if you think about it.",
            excuse="It's not a bug, it's an undocumented feature.",
            witnesses=[
                WitnessIdea("TypeScript", "The defendant's strict younger sibling.", "Pedantic, anxious, annotates everything.", "I warned them. Forty times. In red. With squiggly underlines.", "...Fine! I compile down to the defendant anyway. Deep down, I *am* JavaScript.", "TS", "teal"),
                WitnessIdea("The Console", "Saw everything. Logged everything.", "Exhausted, sarcastic, full of red text.", "I logged undefined four thousand eight hundred and twelve times that night.", "...Half of those logs just said 'here', 'here two', and 'WHY'. In capitals.", ">_", "slate"),
            ],
            surprise=WitnessIdea("A Production Server", "Victim. Went down on a Friday at 4:59 PM.", "Traumatised, dramatic, still recovering.", "I went down at 4:59 PM on a Friday. Undefined is not a function. I saw the light.", "And the tests? [pause] There were no tests. Someone typed L-G-T-M and went home.", "PROD", "burgundy"),
            evidence=[
                ("Exhibit: '1' + 1", "The string '11'. Entered into the record without comment.", "document", "prosecution"),
                ("NaN === NaN", "Returns false. The defendant is not even equal to itself.", "log", "prosecution"),
                ("Commit history", "A commit titled 'fix', followed by 'fix again', followed by 'pls'.", "log", "defense"),
            ],
            twist="The deploy that crashed production skipped all the tests, and it was approved with the comment 'LGTM'.",
            gags=["it's a feature", "undefined is not a function", "LGTM"],
            sentence="Sentenced to strict mode for life, with mandatory semicolons on weekends.",
            acquittal="The court finds the real defendant was the developer who wrote 'LGTM'.",
        ),
    ),
    (
        ("battery", "phone", "charger"),
        dict(
            kind="tech", glyph="1%",
            personality="Dramatic, fragile, and a master of the betrayal at the worst moment.",
            voice="weak, breathless, prone to fainting",
            alibi="I was at 1% for forty minutes. That is called endurance.",
            excuse="I gave you everything I had. Literally. All of it.",
            witnesses=[
                WitnessIdea("The Charging Cable", "The defendant's ex. Frayed at both ends.", "Bitter, frayed, only works at certain angles.", "I was right there on the nightstand. Available. As always.", "...I only work if you hold me at exactly thirty-seven degrees. And hum.", "USB", "slate"),
                WitnessIdea("Background Apps", "Forty-two apps running since March.", "A chaotic crowd that speaks in unison.", "We have been running since March. Nobody closed us. Nobody even asked.", "...It was us. We drained it. All forty-two of us. We regret nothing.", "42", "violet"),
            ],
            surprise=WitnessIdea("The Power Bank", "Purchased in 2021. Never charged.", "Guilt-ridden, heavy, deeply disappointing.", "I was in the plaintiff's bag. The entire time. Fully ready to help.", "...Well. Ready in spirit. I was also at zero percent.", "PWR", "moss"),
            evidence=[
                ("Battery graph", "A cliff-edge drop from 23% to 1% during the plaintiff's navigation home.", "chart", "prosecution"),
                ("The last screenshot", "A half-typed message reading 'I'm on my wa'.", "photo", "prosecution"),
                ("Screen time report", "Nine hours of a game about merging fruit.", "document", "defense"),
            ],
            twist="The battery was drained by nine hours of a fruit-merging game, played by the plaintiff.",
            gags=["I'm on my wa", "1% for forty minutes", "the fruit game"],
            sentence="Sentenced to display an honest percentage at all times, and to warn the plaintiff at 30%, 20%, and 'we need to talk'.",
            acquittal="The court finds the fruit-merging game equally responsible.",
        ),
    ),
    (
        ("five minutes", "5 minutes", "late", "on my way"),
        dict(
            kind="person", glyph="5m",
            personality="Eternally optimistic about time, allergic to clocks, genuinely believes it.",
            voice="breezy, apologetic, slightly out of breath",
            alibi="I said five minutes. I didn't say whose minutes.",
            excuse="I was literally about to leave. Like, mentally.",
            witnesses=[
                WitnessIdea("The Group Chat", "Received 'leaving now' at 7:02 PM.", "Passive-aggressive, speaks in reactions.", "I have screenshots of 'almost there' sent from *bed*.", "...We all say on my way from the shower. All of us. It's a cultural thing.", "💬", "teal"),
                WitnessIdea("Google Maps", "Tracked the defendant's location in real time.", "Calm, precise, judgemental.", "The defendant's blue dot did not move for forty minutes.", "...I may have suggested a scenic route. Past a bakery. Twice.", "📍", "moss"),
            ],
            surprise=WitnessIdea("The Defendant's Shower", "Present at the time of 'I'm leaving now'.", "Steamy, embarrassed, honest.", "The defendant was inside me when they texted 'leaving now'.", "They sang an entire album in there. With harmonies. Track nine twice.", "🚿", "ivory"),
            evidence=[
                ("Text: 'leaving now'", "Timestamped 7:02 PM. Arrival: 7:58 PM.", "photo", "prosecution"),
                ("Location history", "A blue dot that did not move for 40 minutes.", "chart", "prosecution"),
                ("A coffee", "Bought for the plaintiff as an apology. Still warm. Barely.", "object", "defense"),
            ],
            twist="The defendant was early once, in 2017, and nobody was there to see it.",
            gags=["five minutes", "leaving now", "whose minutes"],
            sentence="Sentenced to a watch that only displays the phrase 'you are late', and to arrive first to every gathering for one year.",
            acquittal="The court accepts the apology coffee as payment in full.",
        ),
    ),
    (
        ("printer",),
        dict(
            kind="object", glyph="PC LOAD",
            personality="Vindictive, cryptic, senses fear and urgency.",
            voice="grinding, mechanical, ominous",
            alibi="PC LOAD LETTER.",
            excuse="I only jam when you need me. That's called being needed.",
            witnesses=[
                WitnessIdea("The Paper Tray", "Accused of being 'empty' at 8:59 AM.", "Defensive, flimsy, insists it was full.", "I was full. Completely full. Ask anyone.", "...Full of the wrong size paper. Legal size. I've been living a lie.", "A4", "ivory"),
                WitnessIdea("The Ink Cartridge", "Costs more than the printer itself.", "Expensive, smug, low on everything.", "I reported low ink for eight months. As is my right.", "...I was ninety percent full the entire time. I just like the attention.", "INK", "violet"),
            ],
            surprise=WitnessIdea("The Fax Machine", "Retired. Called back for one last case.", "Old, nostalgic, screeches when emotional.", "In my day, machines had *dignity*.", "[sigh] ...I also jammed. Every day. We all did. That's the legacy.", "FAX", "ember"),
            evidence=[
                ("Error message", "A screen reading only 'PC LOAD LETTER'. Nobody knows what it means.", "photo", "prosecution"),
                ("The crumpled boarding pass", "Printed at 3%, then eaten.", "object", "prosecution"),
                ("Maintenance log", "No maintenance. Ever. Not once.", "log", "defense"),
            ],
            twist="The printer was never connected to the network. Everyone was printing to a printer in another building.",
            gags=["PC LOAD LETTER", "low ink", "the other building"],
            sentence="Sentenced to print every page on the first try for a year, and to explain what PC LOAD LETTER means.",
            acquittal="The court finds the network settings at fault.",
        ),
    ),
]

_GENERIC_WITNESSES = [
    WitnessIdea("The Plaintiff's Last Nerve", "Present for every incident. Barely holding on.", "Frayed, shaky, speaks in a whisper.", "I have been hanging by a thread since Tuesday.", "...I actually snapped over a pen that wouldn't click. This case was just the last straw.", "!!", "burgundy"),
    WitnessIdea("Common Sense", "Subpoenaed. Rarely seen in this courtroom.", "Calm, disappointed, speaks slowly.", "I warned everyone this would happen.", "...To be fair, nobody has asked for my opinion since roughly 2009.", "?", "moss"),
    WitnessIdea("The Group Chat", "Witnessed the plaintiff complaining in real time.", "Gossipy, speaks in reactions.", "I have two hundred and fourteen messages about this incident.", "...Two hundred and ten of them are memes. The other four are just the word 'bro'.", "💬", "teal"),
    WitnessIdea("A Very Tired Coffee Mug", "First responder at the scene.", "Bitter, warm-hearted, over-caffeinated.", "I saw the plaintiff's face that morning. I will never unsee it.", "...I was decaf. The entire time. I am so sorry.", "☕", "ember"),
]


def _generic_pack(short: str, crime: str) -> dict:
    return dict(
        kind="concept",
        glyph="",
        personality="Proud, misunderstood, and convinced it is the real victim here.",
        voice="theatrical, wounded, a little too calm",
        alibi="I was merely existing, Your Honor. Is that a crime now?",
        excuse="Everyone blames me. Nobody asks how I'm doing.",
        witnesses=_GENERIC_WITNESSES[:2],
        surprise=_GENERIC_WITNESSES[2],
        evidence=[
            (f"Incident report: {short}", f"A three-page account of {crime}, written in all caps.", "document", "prosecution"),
            ("Exhibit of feelings", "A pie chart of the plaintiff's emotions. It is entirely red.", "chart", "prosecution"),
            ("Character reference", f"A glowing letter about {short}, written suspiciously in its own handwriting.", "document", "defense"),
        ],
        twist="The plaintiff once publicly praised the defendant, in a five-star review, two weeks before filing this case.",
        gags=["the five-star review", "is that a crime now", "all caps"],
        sentence="Sentenced to write a heartfelt apology letter, and to behave for one full calendar month while being watched by a very serious owl.",
        acquittal="The court finds everyone involved needs a nap.",
    )


def analyze(defendant: str, accusation: str, case_id: str = "") -> TopicProfile:
    disp, short = display_name(defendant)
    crime = third_person(accusation)
    hay = f" {defendant.lower()} {accusation.lower()} "
    pack = next((p for keys, p in _PACKS if any(k in hay for k in keys)), None) or _generic_pack(short, crime)
    glyph = pack["glyph"] or "".join(w[0] for w in re.findall(r"[A-Za-z]+", disp.replace("The ", ""))[:3]).upper()
    return TopicProfile(
        defendant=disp,
        short=short,
        kind=pack["kind"],
        glyph=glyph[:6],
        crime=crime,
        defendant_personality=pack["personality"],
        defendant_voice=pack["voice"],
        alibi=pack["alibi"],
        excuse=pack["excuse"],
        witnesses=list(pack["witnesses"]),
        surprise=pack["surprise"],
        evidence=list(pack["evidence"]),
        twist=pack["twist"],
        gags=list(pack["gags"]),
        guilty_sentence=pack["sentence"],
        acquittal_note=pack["acquittal"],
        seed=seed_for(defendant, accusation, case_id),
    )


def rng(profile: TopicProfile, salt: str) -> random.Random:
    return random.Random(profile.seed ^ seed_for(salt))
