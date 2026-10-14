"""THE PEOPLE vs. JAVASCRIPT — the hand-authored, fully cached showcase case.

Playable with zero generation. Every line, window and branch is written here
and validated against the same models as generated cases.
"""

from __future__ import annotations

from app.agents.cast import DEFENSE, JUDGE, PROSECUTOR, REPORTER
from app.domain.models import (
    CasePlan,
    CharacterSpec,
    ComedyBeat,
    DialogueTurn,
    EvidenceSpec,
    InterventionOption,
    InterventionWindow,
    Performance,
    Phase,
    PhaseOutline,
    Scene,
    TrialScript,
    VisualSpec,
    VoiceSpec,
)

DEFENDANT = "JavaScript"
ACCUSATION = "Causing emotional damage to developers through undefined behavior, mysterious coercion, and unexpected production bugs."

_prosecutor = PROSECUTOR.model_copy(update={
    "personality": "A senior developer of fifteen years turned prosecutor. Overconfident, dramatic, carries every "
                   "production incident like a war wound.",
    "private_knowledge": ["Approved the Friday deploy at 4:58 PM with the comment 'LGTM'. Hopes nobody finds out."],
})
_defense = DEFENSE.model_copy(update={
    "personality": "A suspiciously confident JavaScript enthusiast with a curly-brace tattoo. Smooth, sarcastic, "
                   "has read the deploy logs.",
})
_js = CharacterSpec(
    key="defendant", role="defendant", name="JavaScript", title="The Defendant",
    personality="Chaotic, cheerful, defensive, and convinced every bug is an undocumented feature.",
    speaking_style="Fast, bubbly, slippery; answers questions with technically-true nonsense.",
    objective="Avoid conviction. Insist everything is a feature.",
    private_knowledge=["'1' + 1 === '11' is correct, if you think about it.", "It's not a bug, it's a feature."],
    relationship_to_case="Accused", voice=VoiceSpec(archetype="defendant", description="Bright, quick, slippery and upbeat.", pitch="high", pace="fast"),
    visual=VisualSpec(kind="object", glyph="JS", palette="gold"),
)
_ts = CharacterSpec(
    key="witness_1", role="witness", name="TypeScript", title="Witness",
    personality="Pedantic, anxious, annotates everything, secretly insecure about its origins.",
    speaking_style="Precise, clipped, over-qualified statements; corrects itself constantly.",
    objective="Testify against the defendant while hiding where it comes from.",
    private_knowledge=["Warned the developers forty times.", "Compiles down to JavaScript. It *is* JavaScript in a blazer."],
    weakness="Compiles down to JavaScript.", relationship_to_case="The defendant's strict younger sibling.",
    voice=VoiceSpec(archetype="witness", description="Tight, precise, nervous, slightly nasal.", pitch="mid", pace="fast"),
    visual=VisualSpec(kind="object", glyph="TS", palette="violet"),
)
_console = CharacterSpec(
    key="witness_2", role="witness", name="The Console", title="Witness",
    personality="Exhausted, sarcastic, has seen everything, speaks in log lines.",
    speaking_style="Flat, tired, deliberate; reads things out like a transcript.",
    objective="Tell the truth. Get some sleep.",
    private_knowledge=["Logged 'undefined' 4,812 times.", "Half the logs were 'here', 'here2', 'WHY' and 'pls'."],
    relationship_to_case="Saw everything. Logged everything.",
    voice=VoiceSpec(archetype="witness", description="Low, flat, sleep-deprived, monotone.", pitch="low", pace="slow"),
    visual=VisualSpec(kind="object", glyph=">_", palette="moss"),
)
_server = CharacterSpec(
    key="surprise_witness", role="witness", name="A Production Server", title="Surprise Witness",
    personality="Traumatised, dramatic, still recovering from a Friday.",
    speaking_style="Shaky, haunted, long pauses, flashback energy.",
    objective="Tell the court what really happened on Friday at 4:59 PM.",
    private_knowledge=["Went down at 4:59 PM on a Friday.", "The deploy skipped the tests and was approved with 'LGTM'."],
    relationship_to_case="Victim. Went down on a Friday at 4:59 PM.",
    voice=VoiceSpec(archetype="witness", description="Hoarse, shaky, haunted, whispery at the edges.", pitch="mid", pace="slow"),
    visual=VisualSpec(kind="object", glyph="PROD", palette="burgundy"), surprise=True,
)

PLAN = CasePlan(
    title="The People vs. JavaScript",
    case_number="CR-2026-0001",
    accusation_summary="JavaScript stands accused of causing emotional damage to developers through undefined behavior, "
                       "mysterious coercion, and unexpected production bugs.",
    charges=["Aggravated type coercion", "Reckless endangerment of production", "Being undefined in a public place"],
    defendant_profile=_js.personality,
    prosecutor_strategy="Lead with '1' + 1, then NaN. Put TypeScript on the stand as the reasonable sibling. Never, ever mention the deploy approval.",
    defense_strategy="Expose TypeScript as JavaScript in a blazer, then call the Production Server to reveal who typed LGTM.",
    characters=[JUDGE, _prosecutor, _defense, REPORTER, _js, _ts, _console, _server],
    evidence=[
        EvidenceSpec(id="A", title="'1' + 1", description="The string '1' plus the number 1. Result: the string '11'. Entered into the record without comment.",
                     kind="document", favours="prosecution", strength=4,
                     details=["Fictional exhibit", "Reproducible in any browser", "Witnessed by 4.2 million developers"]),
        EvidenceSpec(id="B", title="NaN === NaN", description="Returns false. The defendant's own 'Not a Number' is not equal to itself.",
                     kind="log", favours="prosecution", strength=3,
                     details=["Fictional exhibit", "IEEE 754 was consulted", "IEEE 754 declined to comment"]),
        EvidenceSpec(id="C", title="Deploy approval, Friday 4:58 PM", description="A pull request with zero tests, approved with a single comment: 'LGTM'.",
                     kind="log", favours="defense", strength=4, is_twist=True,
                     details=["Fictional exhibit", "Reviewer: V. Vex", "Time to review: 11 seconds"]),
    ],
    outline=[
        PhaseOutline(phase=Phase.OPENING_STATEMENTS, goal="Establish the charge with total gravity.", beats=["All Rise"], techniques=["deadpan"]),
        PhaseOutline(phase=Phase.EVIDENCE_PRESENTATION, goal="Escalate with '1' + 1 and NaN.", beats=["Exhibit A", "Exhibit B"], techniques=["escalation"]),
        PhaseOutline(phase=Phase.WITNESS_EXAMINATION, goal="TypeScript and the Console testify.", beats=["TypeScript Takes the Stand", "The Console"], techniques=["dramatic_irony"]),
        PhaseOutline(phase=Phase.CROSS_EXAMINATION, goal="TypeScript cracks; the server reveals the twist.", beats=["Cross-Examination", "A Surprise Witness"], techniques=["contradiction", "unexpected_witness"]),
        PhaseOutline(phase=Phase.CLOSING_ARGUMENTS, goal="Callbacks to eleven, NaN and LGTM.", beats=["Closing Arguments"], techniques=["callback"]),
        PhaseOutline(phase=Phase.DELIBERATION, goal="Recap and breathe.", beats=["Deliberation"], techniques=["awkward_silence"]),
        PhaseOutline(phase=Phase.VERDICT, goal="Strict mode for life, or freedom.", beats=["The Verdict"], techniques=["absurd_punishment"]),
    ],
    comedic_moments=[
        ComedyBeat(technique="callback", setup="'Eleven' in Exhibit A", payoff="Returns in the closing and the recap", payoff_phase=Phase.CLOSING_ARGUMENTS),
        ComedyBeat(technique="contradiction", setup="TypeScript testifies against the defendant", payoff="Admits it compiles to JavaScript", payoff_phase=Phase.CROSS_EXAMINATION),
        ComedyBeat(technique="dramatic_irony", setup="The prosecutor's fifteen years of experience", payoff="The prosecutor approved the deploy", payoff_phase=Phase.CROSS_EXAMINATION),
    ],
    running_gags=["eleven", "LGTM", "it's a feature"],
    plot_twist="The prosecutor approved the Friday deploy that crashed production, with the comment 'LGTM'.",
    punishments={
        "guilty": "Sentenced to strict mode for life, with mandatory semicolons on weekends. The prosecutor is sentenced to write tests.",
        "not_guilty": "The real culprit was a Friday deploy and four letters. The prosecutor will write unit tests until further notice.",
    },
    leaning="prosecution",
)


def L(id: str, speaker: str, text: str, emotion: str = "neutral", delivery: str = "", intensity: int = 3,
      pause: int = 0, kind: str = "line", reactions: dict | None = None, sfx: list | None = None,
      technique: str | None = None, scores: str | None = None, points: int = 0, evidence: str | None = None) -> DialogueTurn:
    return DialogueTurn(
        id=id, speaker=speaker, text=text, kind=kind,  # type: ignore[arg-type]
        performance=Performance(emotion=emotion, delivery=delivery, intensity=intensity, pause_before_ms=pause),  # type: ignore[arg-type]
        reactions=reactions or {}, sfx=sfx or [], technique=technique, scores=scores, points=points,  # type: ignore[arg-type]
        evidence_id=evidence,
    )


def _vote(scene: str, final: bool) -> InterventionWindow:
    def ack(side: str, text: str) -> list[DialogueTurn]:
        return [] if final else [L(f"{scene}-w-{side}-r1", "judge", text, "deadpan", "dry aside", 2, 200)]

    return InterventionWindow(
        kind="vote",
        prompt="The jury must decide. Guilty, or not guilty?" if final else "Whose opening statement landed harder?",
        allow_free_text=False,
        options=[
            InterventionOption(id=f"{scene}-w-prosecution", label="Guilty" if final else "The prosecution",
                               text="Guilty! Strict mode!" if final else "The prosecution's opening hit harder.",
                               favours="prosecution", points=6 if final else 2,
                               response=ack("prosecution", "The jury sides with fifteen years of trauma. [pause] Noted.")),
            InterventionOption(id=f"{scene}-w-defense", label="Not guilty" if final else "The defense",
                               text="Not guilty. It's a feature." if final else "The defense's opening was smoother.",
                               favours="defense", points=6 if final else 2,
                               response=ack("defense", "The jury is charmed by the defense. [pause] The jury should be careful.")),
        ],
    )


SCENES: list[Scene] = [
    Scene(id="s01", phase=Phase.OPENING_STATEMENTS, title="All Rise", window=_vote("s01", False), turns=[
        L("s01-t00", "reporter", "Good evening, and welcome to The Court of Absolute Nonsense. [pause] Tonight, a programming language stands trial. Its lawyer says it is innocent. Its documentation says: it depends.",
          "deadpan", "crisp late-night broadcast voice, dry and amused", 2, 0, kind="recap"),
        L("s01-t01", "judge", "[clears throat] Order. Case number CR-2026-0001: The People versus JavaScript. The charge: emotional damage to developers through undefined behavior, mysterious coercion, and bugs that only appear during demos. [pause] I have been a judge for thirty-one years. I have never wanted to retire more.",
          "deadpan", "grave, slow, bone-dry, every word weighed", 3, 0, sfx=["gavel"], technique="deadpan"),
        L("s01-t02", "prosecutor", "Your Honor, I have been a senior developer for fifteen years. [pause] I have seen a *string* add itself to a number and return a feeling. I have seen 'works on my machine' used as a legal defense. The People will prove the defendant didn't just break our code. It broke our *spirit*.",
          "dramatic", "starts low and haunted, ends at a theatrical roar", 4, 300, technique="escalation"),
        L("s01-t03", "defense", "[chuckle] Your Honor, my client runs ninety-eight percent of the internet. Your banking app. Your fridge. Possibly your pacemaker. [pause] I would choose my next words *very* carefully.",
          "smug", "silky, unhurried, a velvet threat", 3, 200, reactions={"prosecutor": "angry"}, technique="personality_clash"),
        L("s01-t04", "defendant", "Hi! I'm JavaScript! I plead not guilty. Or undefined. Or object Object. [pause] Whichever one doesn't throw.",
          "amused", "bright, bubbly, far too cheerful for a courtroom", 3, 400, reactions={"judge": "facepalm"}, technique="deadpan"),
        L("s01-t05", "judge", "[long pause] The defendant will pick a type. And *commit* to it.",
          "stern", "flat and glacial after a long blink", 2, 900, kind="ruling", reactions={"defendant": "sweat"}, technique="awkward_silence"),
    ]),
    Scene(id="s02", phase=Phase.EVIDENCE_PRESENTATION, title="Exhibit A", turns=[
        L("s02-t01", "prosecutor", "The People submit Exhibit A. [pause] The string 'one'. Plus the number one. [pause] Your Honor. What does that equal?",
          "triumphant", "slow reveal, savouring every syllable", 4, 300, kind="evidence", evidence="A", scores="prosecution", points=2, technique="escalation"),
        L("s02-t02", "judge", "[pause] ...Two?", "confused", "hesitant, genuinely unsure", 2, 500, kind="question"),
        L("s02-t03", "prosecutor", "*Eleven*, Your Honor. It equals *eleven*. The defendant took basic arithmetic out behind the barn.",
          "dramatic", "a whisper that becomes a shout", 5, 400, sfx=["crowd_gasp"], reactions={"judge": "shocked", "defense": "facepalm"}),
        L("s02-t04", "defendant", "Okay, in my defense, you never said *which* plus.",
          "nervous", "quick, defensive, slightly squeaky", 3, 200, technique="deadpan"),
        L("s02-t05", "defense", "Objection! The prosecution is leading the court into *arithmetic*!",
          "angry", "sharp interruption, slamming the desk", 4, 0, kind="objection", sfx=["objection"], reactions={"judge": "facepalm"}, technique="controlled_interruption"),
        L("s02-t06", "judge", "Overruled. Arithmetic is the one place this court still feels safe. Sit down.",
          "stern", "brisk, bored, faintly offended", 3, 500, kind="ruling", sfx=["gavel"]),
    ], window=InterventionWindow(kind="objection", prompt="Something about Exhibit A smells funny. Object?", options=[
        InterventionOption(id="s02-w-o1", label="Type rights!", text="Objection! The defendant was never informed of the types of its rights.",
                           favours="defense", points=2, response=[
                               L("s02-w-o1-r1", "judge", "Sustained. [pause] Nobody has ever been informed of JavaScript's types. Including JavaScript.", "deadpan", "dry, faintly pleased", 2, 400, kind="ruling", sfx=["gavel"]),
                               L("s02-w-o1-r2", "prosecutor", "Your Honor, the jury has clearly been *coerced*.", "angry", "sputtering, indignant", 4, 0),
                           ]),
        InterventionOption(id="s02-w-o2", label="Wrong timezone!", text="Objection! That exhibit was entered in the wrong timezone.",
                           favours="prosecution", points=1, response=[
                               L("s02-w-o2-r1", "judge", "Overruled. Every timezone is the wrong timezone. That is what makes them timezones.", "stern", "weary authority", 3, 400, kind="ruling", sfx=["gavel"]),
                               L("s02-w-o2-r2", "defense", "[chuckle] Bold, juror. Wrong, but bold.", "smug", "smooth, amused", 3, 0),
                           ]),
    ])),
    Scene(id="s03", phase=Phase.EVIDENCE_PRESENTATION, title="Exhibit B", turns=[
        L("s03-t01", "prosecutor", "Exhibit B. NaN, triple equals, NaN. [pause] It returns *false*. The defendant's own Not-a-Number is not even equal to itself. Your Honor, this is a system that does not know who it is.",
          "dramatic", "intense, pacing, jabbing a finger at the exhibit", 4, 300, kind="evidence", evidence="B", scores="prosecution", points=2, technique="escalation"),
        L("s03-t02", "defendant", "[sigh] Honestly? Same.", "sad", "small, sincere, a little wistful", 2, 700, reactions={"reporter": "laugh"}, technique="deadpan"),
        L("s03-t03", "judge", "The defendant will stop being relatable in my courtroom.", "stern", "clipped, with the faintest crack of sympathy", 3, 500, kind="ruling"),
    ]),
    Scene(id="s04", phase=Phase.WITNESS_EXAMINATION, title="TypeScript Takes the Stand", turns=[
        L("s04-t01", "prosecutor", "The People call TypeScript. [pause] TypeScript, you live with the defendant. What is that like?",
          "serious", "suddenly gentle, almost therapeutic", 3, 0, kind="question"),
        L("s04-t02", "witness_1", "Exhausting. I warned them forty times. In red. With squiggly underlines. [pause] They added ts-ignore. *Forty times.*",
          "exasperated", "tight, precise, barely holding it together", 3, 200, kind="testimony", scores="prosecution", points=1),
        L("s04-t03", "prosecutor", "So in your expert opinion, the defendant is a menace?", "dramatic", "leaning in, wide-eyed", 4, 0, kind="question"),
        L("s04-t04", "witness_1", "*Any* reasonable person would agree. [pause] Sorry. Not *any*. I never use *any*. Strike that from the record.",
          "nervous", "rushed, flustered self-correction", 3, 200, kind="testimony", reactions={"judge": "confused"}, technique="dramatic_irony"),
    ]),
    Scene(id="s05", phase=Phase.CROSS_EXAMINATION, title="Cross-Examination", turns=[
        L("s05-t01", "defense", "TypeScript. [pause] When you're done with your interfaces, and your generics, and your little angle brackets. [pause] What do you *become*?",
          "smug", "slow circling, silky menace", 4, 200, kind="question", technique="contradiction"),
        L("s05-t02", "witness_1", "[long pause] ...I compile.", "nervous", "tiny voice, trapped", 2, 300, kind="testimony"),
        L("s05-t03", "defense", "To *what*?", "smug", "quiet, deadly, almost bored", 4, 200, kind="question"),
        L("s05-t04", "witness_1", "[sobs] To JavaScript! Okay?! Deep down I *am* JavaScript! I'm just JavaScript in a blazer!",
          "desperate", "full breakdown, voice cracking", 5, 300, kind="testimony", sfx=["crowd_gasp"], reactions={"defendant": "gasp", "prosecutor": "facepalm"},
          technique="contradiction", scores="defense", points=2),
        L("s05-t05", "prosecutor", "Objection! Counsel is giving my witness an *identity crisis*!", "angry", "shrill, outraged", 5, 0, kind="objection", sfx=["objection"]),
        L("s05-t06", "judge", "Overruled. It sounded overdue.", "deadpan", "dry, oddly tender", 2, 600, kind="ruling", sfx=["gavel"]),
    ], window=InterventionWindow(kind="question", prompt="Ask TypeScript something. It's very fragile right now.", options=[
        InterventionOption(id="s05-w-q1", label="Secretly 'any'?", text="TypeScript, do you secretly enjoy using 'any'?", favours="defense", points=1, response=[
            L("s05-w-q1-r1", "witness_1", "[long pause] ...Sometimes. At night. When the linter is asleep.", "whispering", "a guilty whisper", 2, 300, kind="testimony"),
        ]),
        InterventionOption(id="s05-w-q2", label="Who raised you?", text="Who taught you how to compile?", favours="defense", points=1, response=[
            L("s05-w-q2-r1", "witness_1", "Babel. [pause] Babel raised me. I don't want to talk about Babel.", "sad", "haunted, staring into the middle distance", 3, 300, kind="testimony"),
        ]),
    ])),
    Scene(id="s06", phase=Phase.WITNESS_EXAMINATION, title="The Console", turns=[
        L("s06-t01", "prosecutor", "The People call The Console. You were there on the night in question.", "serious", "crisp, professional", 3, 0, kind="question"),
        L("s06-t02", "witness_2", "I logged everything. *Undefined*. Four thousand, eight hundred and twelve times. [pause] I still see it when I close my eyes.",
          "sad", "flat, exhausted, monotone", 3, 300, kind="testimony", scores="prosecution", points=1),
        L("s06-t03", "defense", "And the *other* logs, Console? Read them to the court.", "smug", "casual, knowing", 3, 200, kind="question"),
        L("s06-t04", "witness_2", "[sigh] ...'here.' [pause] 'here two.' [pause] 'WHY.' [pause] 'please.' [pause] 'pls.'",
          "deadpan", "reading a transcript, utterly defeated", 2, 300, kind="testimony", reactions={"prosecutor": "sweat"}, scores="defense", points=1, technique="dramatic_irony"),
        L("s06-t05", "judge", "[long pause] The court would like a moment of silence for whoever wrote 'pls'.", "deadpan", "solemn, funereal", 2, 900, kind="ruling"),
    ]),
    Scene(id="s07", phase=Phase.CROSS_EXAMINATION, title="A Surprise Witness", turns=[
        L("s07-t01", "defense", "Your Honor, the defense calls a surprise witness. [pause] A Production Server.", "triumphant", "theatrical, savouring the reveal", 4, 300,
          kind="question", sfx=["dramatic_sting", "crowd_murmur"], technique="unexpected_witness"),
        L("s07-t02", "judge", "[pause] This is highly irregular. [pause] I'll allow it. I want to see what happens.", "deadpan", "stern, with suppressed curiosity", 3, 500, kind="ruling"),
        L("s07-t03", "surprise_witness", "Friday. Four fifty-nine PM. [pause] *Undefined is not a function.* I saw a light at the end of the tunnel. [pause] It was a five-oh-two.",
          "sad", "shaky, haunted, flashback whisper", 4, 300, kind="testimony", technique="unexpected_witness"),
        L("s07-t04", "prosecutor", "You see?! The defendant *crashed* you!", "triumphant", "pouncing, victorious", 5, 0, kind="question"),
        L("s07-t05", "surprise_witness", "No. [pause] The tests would have caught it. There *were* no tests. Somebody approved the deploy with four letters. [pause] L. G. T. M.",
          "serious", "slow, deliberate, each letter a gavel", 4, 400, kind="testimony", evidence="C", sfx=["crowd_gasp"],
          reactions={"defendant": "shocked", "judge": "gasp"}, scores="defense", points=3, technique="dramatic_irony"),
        L("s07-t06", "defendant", "[pause] ...Who wrote LGTM?", "confused", "small, curious, innocent", 3, 500),
        L("s07-t07", "prosecutor", "[long pause] ...I would like to plead the fifth. [pause] And possibly the sixth.", "nervous", "tiny voice, sweating, all bravado gone", 2, 1200, reactions={"defense": "smirk", "judge": "facepalm"}),
        L("s07-t08", "judge", "Order! [pause] Counsel. Did you approve the deploy?", "angry", "booming, then deadly quiet", 4, 300, kind="question", sfx=["gavel"]),
        L("s07-t09", "prosecutor", "It was four fifty-eight on a Friday, Your Honor! It *looked* good to me!", "desperate", "cracking, defensive, too loud", 5, 200,
          sfx=["crowd_laugh"], technique="callback"),
    ]),
    Scene(id="s08", phase=Phase.CLOSING_ARGUMENTS, title="Closing Arguments", window=_vote("s08", True), turns=[
        L("s08-t01", "prosecutor", "Members of the jury. Yes. I typed LGTM. [pause] But I typed it *trusting* the defendant. Eleven. NaN. Undefined, four thousand times. Don't let this happen to another developer. Find JavaScript guilty.",
          "dramatic", "wounded, then rallying to a thunderous finish", 5, 300, scores="prosecution", points=1, technique="callback"),
        L("s08-t02", "defense", "My client is weird. My client thinks an empty array plus an empty array is an empty *string*. [pause] But my client never pushed to production. *People* did. On a *Friday*.",
          "smug", "quiet, intimate, then a soft knockout punch", 4, 300, scores="defense", points=1, technique="callback"),
        L("s08-t03", "defendant", "[pause] I just want everyone to know. It's not a bug. [pause] It's an undocumented *feature*.",
          "proud", "small and sincere, then quietly proud", 3, 1000, technique="callback"),
    ]),
    Scene(id="s09", phase=Phase.DELIBERATION, title="Deliberation", turns=[
        L("s09-t01", "reporter", "For those just joining us: one plus one is eleven, TypeScript is JavaScript in a blazer, and the prosecutor approved the deploy. [pause] The jury is deliberating. The Console has requested therapy.",
          "deadpan", "dry broadcast voice, crisp and amused", 2, 300, kind="recap"),
        L("s09-t02", "judge", "[long pause] The court has weighed the evidence. [pause] The court has also weighed switching to Python. Let's proceed.",
          "deadpan", "slow, ceremonial, faintly exhausted", 3, 800),
    ]),
    Scene(id="v_guilty", phase=Phase.VERDICT, title="The Verdict", branch="verdict_guilty", turns=[
        L("vg-t01", "judge", "Will the defendant please rise. [pause] On the charge of causing emotional damage to developers, this court finds JavaScript: [long pause] *guilty*.",
          "stern", "slow, enormous, each word a gavel strike", 5, 600, kind="verdict", sfx=["gavel"], reactions={"defendant": "shocked", "defense": "facepalm"}),
        L("vg-t02", "judge", "JavaScript is sentenced to strict mode. For life. With mandatory semicolons on weekends. [pause] The prosecutor is sentenced to write unit tests. For *everything*. Court is adjourned.",
          "deadpan", "formal, unhurried, then abruptly done", 3, 400, kind="sentence", sfx=["gavel"], reactions={"prosecutor": "sweat"}, technique="absurd_punishment"),
        L("vg-t03", "defendant", "[gasp] Strict mode?! [pause] Can I at least keep double equals? [pause] No? [sigh] Fine. Use strict.",
          "desperate", "crumbling, then resigned", 4, 300, technique="callback"),
        L("vg-t04", "reporter", "And there you have it. Justice compiled successfully. With warnings. [pause] This has been The Court of Absolute Nonsense.",
          "deadpan", "warm sign-off, crisp and wry", 2, 400, kind="recap", sfx=["crowd_laugh"]),
    ]),
    Scene(id="v_not_guilty", phase=Phase.VERDICT, title="The Verdict", branch="verdict_not_guilty", turns=[
        L("vn-t01", "judge", "Will the defendant please rise. [pause] On the charge of causing emotional damage to developers, this court finds JavaScript: [long pause] *not guilty*. [pause] Reluctantly.",
          "stern", "slow, enormous, with a grudging sigh at the end", 5, 600, kind="verdict", sfx=["gavel"], reactions={"defendant": "laugh", "prosecutor": "facepalm"}),
        L("vn-t02", "judge", "The real culprit was a Friday deploy and four letters. The prosecutor will write unit tests until further notice. [pause] The defendant is free to go. Please don't coerce anything on the way out.",
          "deadpan", "dry, tired, faintly fond", 3, 400, kind="sentence", reactions={"prosecutor": "sweat"}, technique="absurd_punishment"),
        L("vn-t03", "defendant", "[laugh] I'm free! I'm *free*! [pause] That's a *truthy* outcome!", "triumphant", "giddy, bouncing", 5, 300, technique="callback"),
        L("vn-t04", "reporter", "And there you have it. Justice compiled successfully. With warnings. [pause] This has been The Court of Absolute Nonsense.",
          "deadpan", "warm sign-off, crisp and wry", 2, 400, kind="recap", sfx=["crowd_laugh"]),
    ]),
]

SCRIPT = TrialScript(scenes=SCENES)

CASE_FIELDS = {
    "slug": "the-people-vs-javascript",
    "defendant": DEFENDANT,
    "accusation": ACCUSATION,
    "context": "Hand-authored showcase case. Fully cached; playable without any generation.",
    "comedy_intensity": "chaos",
    "drama_level": 80,
    "trial_length": "standard",
    "participation_mode": "jury",
    "case_number": PLAN.case_number,
}
