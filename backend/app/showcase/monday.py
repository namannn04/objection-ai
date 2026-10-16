"""THE PEOPLE vs. MONDAY MORNING — a hand-authored, desi-household special.

Full-blown Indian ghar ka kalesh, performed in English: Mummy, Papa, Sharma ji's son,
the manager's Sunday-night "Hi", and a screen-time twist. Every line, window and
branch is written here and validated like any generated case.

Voices are hand-cast from generic public Fish Audio voices with Indian-English accents
(no clones or impersonations of real people).
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
    Phase,
    PhaseOutline,
    Scene,
    TrialScript,
    VisualSpec,
    VoiceSpec,
)
from app.showcase.javascript import L

DEFENDANT = "Monday Morning"
ACCUSATION = "Arriving every single week without permission, waking up entire households, and enabling 'quick five-minute calls' that last two hours."


def _v(voice: VoiceSpec, fish: str, label: str, description: str) -> VoiceSpec:
    return voice.model_copy(update={"fish_voice": fish, "fish_label": label, "description": description})


_judge = JUDGE.model_copy(update={
    "name": "Justice K. K. Kaleshwar",
    "personality": "Thirty-four years on the bench, has never once had a good Monday. Formal, tired, speaks in "
                   "government-office English, and is quietly terrified of every Indian mother.",
    "speaking_style": "Slow, official, 'kindly do the needful'. Long pauses before a devastating one-liner.",
    "voice": _v(JUDGE.voice, "73770ea2927d46c19e461e7e812b2f95", "Indian (old, authoritative)",
                "Old, measured, authoritative Indian-English judge."),
})
_prosecutor = PROSECUTOR.model_copy(update={
    "name": "Advocate Pinky Malhotra",
    "personality": "South Delhi firecracker. Treats every inconvenience as a national emergency. Personally hates Mondays.",
    "speaking_style": "Fast, loud, dramatic, 'Excuse me?!' energy, rhetorical questions at full volume.",
    "private_knowledge": ["Watched reels until 3:47 AM on Sunday. Liked one called 'Monday be like'. Hopes nobody checks."],
    "voice": _v(PROSECUTOR.voice, "b67de7cfa4c6404ba5fb913b564b77dc", "Indian female (bright, confident)",
                "Bright, confident, fast Indian-English woman."),
})
_defense = DEFENSE.model_copy(update={
    "name": "Advocate Bunty Bhalla",
    "personality": "King of jugaad. Smooth, cheeky, always has a loophole, calls everyone 'ji'.",
    "speaking_style": "Easy, charming, 'one minute, My Lord, one minute', drops the knockout line casually.",
    "voice": _v(DEFENSE.voice, "1da86bba49dd4775a0d2f460cd2b4ce4", "Indian (cheerful, animated)",
                "Cheerful, animated, cheeky Indian-English man."),
})
_reporter = REPORTER.model_copy(update={
    "name": "Chhavi Chaudhary",
    "title": "Prime-Time Anchor",
    "personality": "Prime-time news anchor. Everything is BREAKING NEWS. Has never used an indoor voice.",
    "speaking_style": "Breathless, urgent, dramatic news-channel cadence.",
    "voice": _v(REPORTER.voice, "1600f0a2e2af4ef3af1b350367683ede", "Hindi (confident, energetic)",
                "Confident, energetic, urgent Indian-English news anchor."),
})
_monday = CharacterSpec(
    key="defendant", role="defendant", name="Monday Morning", title="The Accused",
    personality="Lazy, smug, weirdly calm. Thinks he is the only punctual one in the country.",
    speaking_style="Slow, sleepy, unbothered; every line sounds like a yawn.",
    objective="Get acquitted. Prove it was Sunday night all along.",
    private_knowledge=["Has never sent a single WhatsApp message.", "Is secretly Mummy's favourite day."],
    relationship_to_case="Accused. Arrives fifty-two times a year.",
    voice=VoiceSpec(archetype="defendant", description="Young, slow, sleepy, calm Indian-English voice.", pitch="mid", pace="slow",
                    fish_voice="ce9c96291460478ea6851049cb847d73", fish_label="Indian (young, calm, slow)"),
    visual=VisualSpec(kind="object", glyph="MON", palette="slate"),
)
_mummy = CharacterSpec(
    key="witness_1", role="witness", name="Mummy", title="Head of the Household",
    personality="The most powerful person in any Indian home. Has the dal on the gas and no time for nonsense.",
    speaking_style="Loud, sharp, rapid-fire taunts; can switch from fury to emotion in one breath.",
    objective="Testify against Monday. Get back to the kitchen.",
    private_knowledge=["Secretly loves Monday: the only morning she drinks her chai hot, alone, in peace."],
    weakness="Secretly loves Monday.", relationship_to_case="Has woken the victim up every Monday since 1998.",
    voice=VoiceSpec(archetype="witness", description="Bold, raspy, expressive, angry Indian mother.", pitch="high", pace="fast",
                    fish_voice="d8c8963125a545c0b4ef8fb05c51c38c", fish_label="Aunty (bold, expressive)"),
    visual=VisualSpec(kind="human", palette="ember", accessory="none", hair="bun", attire="saree", bindi=True),
)
_papa = CharacterSpec(
    key="witness_2", role="witness", name="Papa", title="Retired, Reads the Newspaper",
    personality="Retired for six years. Still has strong opinions about the fan, the electricity bill and your generation.",
    speaking_style="Warm but lecturing; 'in my day'; ends every argument with savings.",
    objective="Complain. Properly.",
    private_knowledge=["Retired six years ago. Has not had a Monday since."],
    weakness="Doesn't even have Mondays any more.", relationship_to_case="Father of the victim. Professional complainer.",
    voice=VoiceSpec(archetype="witness", description="Warm, measured, middle-aged Indian father.", pitch="low", pace="measured",
                    fish_voice="9dc372bfccb04efb9f6b7cd588952a73", fish_label="Indian (warm, measured)"),
    visual=VisualSpec(kind="human", palette="moss", accessory="glasses", hair="balding", mustache=True),
)
_manager = CharacterSpec(
    key="witness_3", role="witness", name="Mr. Khanna", title="Team Lead",
    personality="Corporate to the bone. Believes in 'quick syncs', 'circling back' and 'we are a family'.",
    speaking_style="Fast, salesy, buzzwords; sounds like an advertisement for himself.",
    objective="Defend the 9 AM meeting. Never discuss the hike.",
    private_knowledge=["Sent 'Hi' at 11:58 PM on Sunday and then typed for forty minutes.", "The hike has been 'under process' for two years."],
    weakness="The 'five-minute' call lasted two hours.", relationship_to_case="Monday's accomplice.",
    voice=VoiceSpec(archetype="witness", description="Fast, persuasive, salesy Indian-English corporate voice.", pitch="mid", pace="fast",
                    fish_voice="d9898b658fde4a9ca2752a5e9bb7451b", fish_label="Indian male (fast, persuasive)"),
    visual=VisualSpec(kind="human", palette="slate", accessory="tie", hair="crop"),
)
_screen = CharacterSpec(
    key="surprise_witness", role="witness", name="Screen Time", title="Surprise Witness",
    personality="Your phone's weekly report. Calm, clinical, merciless. Has seen everything.",
    speaking_style="Flat, precise, reads numbers like a verdict.",
    objective="Tell the court what really happened on Sunday night.",
    private_knowledge=["Sunday: 4 hours 12 minutes of reels. Last activity 3:47 AM.", "Device owner: Advocate Pinky Malhotra."],
    relationship_to_case="Witnessed Sunday night. Every minute of it.",
    voice=VoiceSpec(archetype="witness", description="Calm, flat, clinical, measured voice.", pitch="low", pace="slow",
                    fish_voice="ca1c77bf09ee4497ac5cd97c5db1f6d5", fish_label="Indian (calm, clinical)"),
    visual=VisualSpec(kind="object", glyph="3:47", palette="violet"), surprise=True,
)

PLAN = CasePlan(
    title="The People vs. Monday Morning",
    case_number="CR-2026-0952",
    accusation_summary="Monday Morning stands accused of arriving every week without permission, waking entire households, "
                       "and enabling two-hour 'quick calls'.",
    charges=["Waking people up with intent", "Aiding and abetting a 9 AM meeting", "Ruining Sunday night by existing"],
    defendant_profile=_monday.personality,
    prosecutor_strategy="Lead with the manager's Sunday-night 'Hi' and the alarm log. Put Mummy on the stand. Never mention reels.",
    defense_strategy="Show Monday never did anything; expose Mummy's hot chai, Papa's retirement, the manager, and Sunday night.",
    characters=[_judge, _prosecutor, _defense, _reporter, _monday, _mummy, _papa, _manager, _screen],
    evidence=[
        EvidenceSpec(id="A", title="WhatsApp: 'Hi'", description="A message from the manager, Sunday 11:58 PM. It says only 'Hi'. Followed by 'typing...' for forty minutes.",
                     kind="recording", favours="prosecution", strength=4,
                     details=["Fictional exhibit", "Sent: Sunday, 11:58 PM", "Typing indicator: 40 minutes", "Follow-up: none"]),
        EvidenceSpec(id="B", title="The Alarm Log", description="Snoozed alarms from 6:00 to 7:45 AM, labelled 'Last chance', 'Really last chance' and 'Mummy is coming'.",
                     kind="log", favours="prosecution", strength=3,
                     details=["Fictional exhibit", "Alarms set: 11", "Alarms obeyed: 0", "Final alarm: 'Mummy is coming'"]),
        EvidenceSpec(id="C", title="Screen Time, Sunday", description="Four hours twelve minutes of reels. Last activity 3:47 AM. Last reel liked: 'Monday be like'.",
                     kind="chart", favours="defense", strength=5, is_twist=True,
                     details=["Fictional exhibit", "Reels: 4h 12m", "Last activity: 3:47 AM", "Device owner: P. Malhotra"]),
    ],
    outline=[
        PhaseOutline(phase=Phase.OPENING_STATEMENTS, goal="Breaking news; the nation is in pyjamas.", beats=["All Rise"], techniques=["deadpan"]),
        PhaseOutline(phase=Phase.EVIDENCE_PRESENTATION, goal="The Sunday-night 'Hi' and the alarm log.", beats=["Exhibit A", "Exhibit B"], techniques=["escalation"]),
        PhaseOutline(phase=Phase.WITNESS_EXAMINATION, goal="Mummy, Papa and the manager testify.", beats=["Mummy Takes the Stand", "Papa", "The Manager"], techniques=["personality_clash"]),
        PhaseOutline(phase=Phase.CROSS_EXAMINATION, goal="Mummy's hot chai; Screen Time exposes the prosecutor.", beats=["Cross-Examination", "A Surprise Witness"], techniques=["contradiction", "unexpected_witness"]),
        PhaseOutline(phase=Phase.CLOSING_ARGUMENTS, goal="Callbacks to 'Hi', 3:47 and Sharma ji's son.", beats=["Closing Arguments"], techniques=["callback"]),
        PhaseOutline(phase=Phase.DELIBERATION, goal="Breaking-news recap.", beats=["Deliberation"], techniques=["awkward_silence"]),
        PhaseOutline(phase=Phase.VERDICT, goal="Monday starts at 11 AM forever, or walks free.", beats=["The Verdict"], techniques=["absurd_punishment"]),
    ],
    comedic_moments=[
        ComedyBeat(technique="contradiction", setup="Mummy testifies against Monday", payoff="Admits Monday is the only day she drinks her chai hot", payoff_phase=Phase.CROSS_EXAMINATION),
        ComedyBeat(technique="dramatic_irony", setup="The prosecutor personally hates Mondays", payoff="Her phone was up till 3:47 AM liking 'Monday be like'", payoff_phase=Phase.CROSS_EXAMINATION),
        ComedyBeat(technique="callback", setup="Sharma ji's son is in Canada", payoff="Mummy's favourite child is Sharma ji's son", payoff_phase=Phase.CROSS_EXAMINATION),
    ],
    running_gags=["Sharma ji's son", "just one more reel", "quick five-minute call", "the fan"],
    plot_twist="The prosecutor watched reels until 3:47 AM on Sunday and liked one called 'Monday be like'.",
    punishments={
        "guilty": "Monday starts at 11 AM forever; every 9 AM meeting must serve hot chai and samosa; the manager may never say 'quick call' again.",
        "not_guilty": "The real culprit was Sunday night and one more reel. The prosecutor's phone is confiscated after 11 PM. By Mummy.",
    },
    leaning="prosecution",
)


def _ack(id: str, text: str, emotion: str = "deadpan", delivery: str = "dry aside, tired") -> list[DialogueTurn]:
    return [L(id, "judge", text, emotion, delivery, 2, 200)]


def _vote(scene: str, final: bool) -> InterventionWindow:
    return InterventionWindow(
        kind="vote",
        prompt="The jury must decide. Is Monday guilty?" if final else "Whose opening hit harder?",
        allow_free_text=False,
        options=[
            InterventionOption(id=f"{scene}-w-prosecution", label="Guilty" if final else "Pinky Malhotra",
                               text="Guilty! Monday starts at eleven!" if final else "The prosecution's opening hit harder.",
                               favours="prosecution", points=6 if final else 2,
                               response=[] if final else _ack(f"{scene}-w-prosecution-r1", "The jury has chosen violence. [pause] Noted.")),
            InterventionOption(id=f"{scene}-w-defense", label="Not guilty" if final else "Bunty Bhalla",
                               text="Not guilty. Blame Sunday night." if final else "The defense's opening was smoother.",
                               favours="defense", points=6 if final else 2,
                               response=[] if final else _ack(f"{scene}-w-defense-r1", "The jury fell for 'day-ism'. [pause] Mr. Bhalla will now be unbearable for a week.")),
        ],
    )


ANCHOR = "breathless prime-time news anchor, urgent and over the top, every sentence a headline"

SCENES: list[Scene] = [
    Scene(id="s01", phase=Phase.OPENING_STATEMENTS, title="All Rise", window=_vote("s01", False), turns=[
        L("s01-t00", "reporter", "[inhales] Breaking news! Breaking news! *Breaking* news! [pause] I'm Chhavi Chaudhary, and tonight the whole country is asking one question. [pause] Why does Monday come *every single week*? [pause] The accused is in court. The nation is in pyjamas. Let's go live.",
          "dramatic", ANCHOR, 4, 0, kind="recap"),
        L("s01-t01", "judge", "[clears throat] Order. Order! [pause] Case number CR-2026-0952. The People of Every Indian Household versus Monday Morning. The charges: waking people up with intent, and aiding a *quick five-minute call* that lasted two hours. [pause] I have been a judge for thirty-four years. Not *one* Monday has been good. [pause] Prosecution, kindly do the needful.",
          "deadpan", "slow, official, government-office gravity, bone-dry", 3, 0, sfx=["gavel"], technique="deadpan"),
        L("s01-t02", "prosecutor", "Thank you, My Lord. [pause] Every Sunday night, crores of people go to bed happy. And at six AM, *this* fellow walks in. No knock. No sorry. Just an alarm, a cold floor, and Mummy shouting from the kitchen: [pause] 'The sun is up! Sharma ji's son is up! Why are *you* not up?!' [pause] My Lord, he has done this fifty-two times a year. Since *birth*.",
          "dramatic", "loud, theatrical, building to a full Delhi roar", 4, 300, technique="escalation", reactions={"defendant": "sweat"}),
        L("s01-t03", "defense", "[chuckle] My Lord, one minute, one minute. My client is just a *day*. Same twenty-four hours as Saturday. [pause] Has anybody filed a case against Saturday? No! Saturday gets *brunch*. My client gets *hate*. [pause] This is discrimination, My Lord. *Day-ism*.",
          "smug", "easy, cheeky charm, enjoying himself", 3, 200, reactions={"prosecutor": "angry"}, technique="personality_clash"),
        L("s01-t04", "defendant", "[sigh] Hello, everyone. Good morning. [pause] Oh, sorry, you hate that. [pause] Look, I don't even *want* to come. Sunday just leaves without telling anyone, and I'm the only one who shows up for work. [pause] Honestly? I'm the most punctual one in this country.",
          "deadpan", "slow, sleepy, completely unbothered, like a yawn", 2, 400, reactions={"judge": "facepalm"}, technique="deadpan"),
        L("s01-t05", "judge", "[long pause] The accused will *not* call himself punctual in a country where the nine AM meeting starts at nine forty. [pause] Sit down.",
          "stern", "flat, glacial, after a very long stare", 3, 900, kind="ruling", reactions={"defendant": "sweat"}, technique="awkward_silence"),
    ]),
    Scene(id="s02", phase=Phase.EVIDENCE_PRESENTATION, title="Exhibit A", turns=[
        L("s02-t01", "prosecutor", "My Lord, the prosecution submits Exhibit A. [pause] A WhatsApp message. From the *manager*. Sunday night, eleven fifty-eight PM. [pause] It says: 'Hi.' [long pause] That's it. Just 'Hi'. And then 'typing' for *forty minutes*.",
          "dramatic", "slow, horrified reveal, as if reading a ransom note", 4, 300, kind="evidence", evidence="A", scores="prosecution", points=2,
          sfx=["crowd_gasp"], technique="escalation"),
        L("s02-t02", "judge", "[pause] Just... 'Hi'? On a *Sunday night*? [inhales] Somebody get this court a glass of water.",
          "shocked", "genuinely rattled, hand on chest", 3, 500, reactions={"defense": "shocked"}),
        L("s02-t03", "defense", "Objection, My Lord! That 'Hi' was sent on *Sunday*! My client wasn't even born yet! [pause] Arrest Sunday!",
          "desperate", "sharp, scrambling, slapping the desk", 4, 0, kind="objection", sfx=["objection"], technique="controlled_interruption"),
        L("s02-t04", "judge", "Overruled. Sunday is not on trial. Sunday is *family*. [pause] Sit down, Mr. Bhalla.",
          "stern", "brisk, protective, faintly offended", 3, 400, kind="ruling", sfx=["gavel"]),
        L("s02-t05", "defendant", "[nervous laugh] For the record, I didn't send it. I just *deliver* it. I'm like the courier boy. [pause] You don't blame the courier boy.",
          "nervous", "slow and sleepy, suddenly a little anxious", 3, 300),
        L("s02-t06", "prosecutor", "You *are* the courier boy who comes at six AM and rings the bell *forty* times!",
          "angry", "instant, loud, finger pointed", 5, 0, sfx=["crowd_laugh"], reactions={"defendant": "sweat"}),
    ], window=InterventionWindow(kind="objection", prompt="That 'Hi' is suspicious. Object?", options=[
        InterventionOption(id="s02-w-o1", label="Left on seen!", text="Objection! My client never had to reply. He left the manager on seen.",
                           favours="defense", points=2, response=[
                               L("s02-w-o1-r1", "judge", "Sustained. [pause] Leaving the manager on 'seen' is not a crime. It is *self-care*.", "deadpan", "dry, quietly approving", 2, 400, kind="ruling", sfx=["gavel"]),
                               L("s02-w-o1-r2", "prosecutor", "My Lord, *this* is how anarchy begins!", "angry", "sputtering, outraged", 4, 0),
                           ]),
        InterventionOption(id="s02-w-o2", label="That's Hi-say!", text="Objection! That's not hearsay, My Lord. That's *Hi*-say.",
                           favours="prosecution", points=1, response=[
                               L("s02-w-o2-r1", "judge", "[long pause] Overruled. And the juror will stay back after court. For that joke.", "stern", "slow, deeply unimpressed", 3, 600, kind="ruling", sfx=["gavel"]),
                               L("s02-w-o2-r2", "defense", "[chuckle] Bold. Wrong, but bold.", "smug", "smooth, amused", 3, 0),
                           ]),
    ])),
    Scene(id="s03", phase=Phase.EVIDENCE_PRESENTATION, title="Exhibit B", turns=[
        L("s03-t01", "prosecutor", "Exhibit B, My Lord. The victim's alarm history. [pause] Six AM. Six oh five. Six ten. [pause] Six fifteen, labelled 'Last chance'. Six twenty, labelled 'Really last chance'. [pause] And seven forty-five, labelled... [shaky breath] 'Mummy is coming.'",
          "dramatic", "intense, counting like a countdown, voice dropping on the last label", 4, 300, kind="evidence", evidence="B",
          scores="prosecution", points=2, sfx=["crowd_laugh"], technique="escalation"),
        L("s03-t02", "defendant", "[sigh] Honestly? I respected the six twenty one. It had *ambition*.",
          "amused", "slow, sleepy, faintly impressed", 2, 600, reactions={"reporter": "laugh"}, technique="deadpan"),
        L("s03-t03", "judge", "[pause] The court will note... the court *also* has a 'Mummy is coming' alarm. [pause] This court is not above this. Continue.",
          "deadpan", "dry, with a crack of very personal trauma", 3, 500, kind="ruling"),
    ]),
    Scene(id="s04", phase=Phase.WITNESS_EXAMINATION, title="Mummy Takes the Stand", turns=[
        L("s04-t01", "prosecutor", "My Lord, the prosecution calls the most powerful person in any Indian home. [pause] *Mummy*.",
          "triumphant", "reverent, almost scared, lowering her voice", 4, 0, kind="question", sfx=["dramatic_sting", "crowd_murmur"]),
        L("s04-t02", "witness_1", "Yes, yes, I'm coming! I left the dal on the gas, so make it quick. [pause] What do you want?",
          "exasperated", "loud, busy, walking in mid-argument, zero patience", 4, 300, kind="testimony"),
        L("s04-t03", "prosecutor", "Mummy, what happens in your house on a Monday morning?", "serious", "gentle, careful, a little afraid", 3, 0, kind="question"),
        L("s04-t04", "witness_1", "Kalesh. Full kalesh. [pause] Six AM, I'm shouting. Six thirty, I'm shouting louder. Seven o'clock, I'm saying, 'Look at Sharma ji's son! He woke up at five, did yoga, made his own breakfast, and now he's in *Canada*!' [pause] And this one? Still under the blanket. Like a *samosa*.",
          "angry", "rapid-fire, furious, every taunt a slap, building to a shout", 5, 200, kind="testimony", scores="prosecution", points=2,
          sfx=["crowd_laugh"], reactions={"defendant": "sweat"}, technique="escalation"),
        L("s04-t05", "prosecutor", "And who do you blame for all this, Mummy?", "dramatic", "leaning in, egging her on", 4, 0, kind="question"),
        L("s04-t06", "witness_1", "Monday! And the phone! And the fan running all night with nobody in the room. [pause] Who is paying the electricity bill? [scoff] *Your father?*",
          "angry", "sharp, sarcastic, glaring at everyone at once", 5, 200, kind="testimony", reactions={"witness_2": "sweat", "judge": "sweat"}),
        L("s04-t07", "judge", "[pause] The witness may... kindly... continue. [pause] This court is also scared of her.",
          "nervous", "very small voice, avoiding eye contact", 2, 600, kind="ruling"),
    ]),
    Scene(id="s05", phase=Phase.CROSS_EXAMINATION, title="Cross-Examination", turns=[
        L("s05-t01", "defense", "Mummy-ji. Namaste. Lovely saree. [pause] Just one small question. Once everybody leaves the house on Monday... what do *you* do?",
          "smug", "sweet as jalebi, slowly circling", 4, 200, kind="question", technique="contradiction"),
        L("s05-t02", "witness_1", "[pause] Why are you asking? [pause] ...Nothing. Housework.", "nervous", "suspicious, suddenly guarded", 3, 300, kind="testimony"),
        L("s05-t03", "defense", "At ten AM? The house empty? Nobody calling 'Mummy'?", "smug", "quiet, knowing, almost a whisper", 4, 200, kind="question"),
        L("s05-t04", "witness_1", "[long pause] [sigh] ...I make one cup of chai. And I drink it *hot*. For the first time in the whole week. [pause] Nobody saying 'Mummy, where is my sock?' Nobody saying 'Mummy, the Wi-Fi is not working.' [pause] [sniffs] It is... *beautiful*.",
          "sad", "the fury melts, soft, dreamy, close to tears", 4, 300, kind="testimony", sfx=["crowd_gasp"],
          reactions={"defendant": "gasp", "prosecutor": "facepalm"}, technique="contradiction", scores="defense", points=2),
        L("s05-t05", "defendant", "[gasp] Mummy... you *like* me?", "shocked", "sleepy voice suddenly wide awake and touched", 3, 300),
        L("s05-t06", "witness_1", "Don't push it. Go and take a bath.", "stern", "instantly back to full Mummy, flat and lethal", 4, 0, kind="testimony", sfx=["crowd_laugh"]),
        L("s05-t07", "prosecutor", "Objection! My Lord, the witness has been *chai-jacked*!", "angry", "shrill, outraged", 5, 0, kind="objection", sfx=["objection"]),
        L("s05-t08", "judge", "Overruled. [pause] Hot chai is sacred in this court.", "deadpan", "dry, oddly tender", 2, 600, kind="ruling", sfx=["gavel"]),
    ], window=InterventionWindow(kind="question", prompt="Ask Mummy something. Carefully.", options=[
        InterventionOption(id="s05-w-q1", label="Where's the remote?", text="Mummy, where is the TV remote?", favours="prosecution", points=1, response=[
            L("s05-w-q1-r1", "witness_1", "Where it always is. In front of your eyes. [pause] And if *I* come and find it, you'll see what happens.", "angry", "low, slow, a threat every Indian child knows", 4, 300, kind="testimony"),
        ]),
        InterventionOption(id="s05-w-q2", label="Who's your favourite?", text="Mummy, who is your favourite child?", favours="defense", points=1, response=[
            L("s05-w-q2-r1", "witness_1", "[chuckle] Sharma ji's son.", "amused", "instant, sweet, no hesitation at all", 3, 400, kind="testimony", sfx=["crowd_laugh"], technique="callback"),
        ]),
    ])),
    Scene(id="s06", phase=Phase.WITNESS_EXAMINATION, title="Papa", turns=[
        L("s06-t01", "prosecutor", "The prosecution calls Papa. [pause] He has been reading the same newspaper since seven AM.", "serious", "crisp, respectful", 3, 0, kind="question"),
        L("s06-t02", "witness_2", "[clears throat] Yes. First of all, switch off that fan, nobody is sitting under it. [pause] Now. In my day there was no Monday problem. I walked eight kilometres to office. In the rain. Uphill. *Both ways*.",
          "proud", "warm, lecturing, very pleased with himself", 3, 300, kind="testimony", scores="prosecution", points=1),
        L("s06-t03", "defense", "Papa-ji, with respect. Which office was uphill *both* ways?", "amused", "polite, cheeky, trying not to laugh", 3, 200, kind="question"),
        L("s06-t04", "witness_2", "[pause] Don't argue with your elders. That is the problem with your generation. [pause] Too many questions. Not enough *savings*.",
          "stern", "offended, slow, final", 3, 300, kind="testimony", reactions={"judge": "nod"}),
        L("s06-t05", "defense", "One more, Papa-ji. You retired six years ago. [pause] So... you don't even *have* Mondays.", "smug", "gentle, then the trap snaps shut", 4, 200, kind="question", technique="contradiction"),
        L("s06-t06", "witness_2", "[long pause] I have *his* Mondays. [pause] Somebody in this house has to suffer properly.",
          "deadpan", "dead serious, completely sincere", 3, 500, kind="testimony", sfx=["crowd_laugh"], scores="defense", points=1),
        L("s06-t07", "judge", "[chuckle] The court... will allow it. [pause] I have said the same thing to my son.", "amused", "a rare, dry chuckle", 2, 500, kind="ruling"),
    ]),
    Scene(id="s07", phase=Phase.WITNESS_EXAMINATION, title="The Manager", turns=[
        L("s07-t01", "prosecutor", "The prosecution calls Monday's accomplice. Mr. Khanna, Team Lead. [pause] Sir, did you schedule a meeting at nine AM on Monday?", "dramatic", "accusing, pacing", 4, 0, kind="question"),
        L("s07-t02", "witness_3", "Yes, yes! Just a *quick* sync. Five minutes only. Cameras on, energy high! [pause] We are a *family* here.",
          "proud", "fast, salesy, like an advertisement for himself", 4, 300, kind="testimony"),
        L("s07-t03", "defense", "Mr. Khanna. How long did the five-minute call actually last?", "smug", "calm, patient, holding a stopwatch", 3, 200, kind="question"),
        L("s07-t04", "witness_3", "[pause] Two hours. Fourteen minutes. [pause] But we *aligned*. We circled back. And then we took it *offline*.",
          "nervous", "still salesy, but sweating through it", 3, 300, kind="testimony", scores="defense", points=1, reactions={"defendant": "smirk"}),
        L("s07-t05", "defense", "And the hike you promised last year?", "smug", "soft, deadly", 4, 200, kind="question"),
        L("s07-t06", "witness_3", "[nervous laugh] It's under *process*. The process takes three to five business years. [pause] But you'll get a certificate! And a pizza party. Half a slice per person.",
          "nervous", "fast, cheerful panic, overselling", 4, 300, kind="testimony", sfx=["crowd_laugh"]),
        L("s07-t07", "judge", "[long pause] Mr. Khanna. This court would like to take *you* offline. [pause] Permanently.",
          "stern", "slow, enormous, utterly done", 4, 700, kind="ruling", sfx=["gavel"], reactions={"witness_3": "sweat"}, technique="callback"),
    ]),
    Scene(id="s08", phase=Phase.CROSS_EXAMINATION, title="A Surprise Witness", turns=[
        L("s08-t01", "defense", "My Lord, the defense calls a surprise witness. [pause] The one who sees *everything*. [pause] Screen Time.",
          "triumphant", "theatrical, savouring the reveal", 4, 300, kind="question", sfx=["dramatic_sting", "crowd_murmur"], technique="unexpected_witness"),
        L("s08-t02", "judge", "[pause] Highly irregular. [pause] Allowed. [pause] I want to know my own screen time also. [pause] No. Never mind.", "deadpan", "stern, then quietly afraid of the answer", 3, 500, kind="ruling"),
        L("s08-t03", "surprise_witness", "Weekly report. [pause] Sunday night. Reels: four hours, twelve minutes. [pause] Last activity: three forty-seven AM. [pause] Last reel liked: 'Monday be like.'",
          "deadpan", "flat, clinical, reading numbers like a verdict", 3, 300, kind="testimony", evidence="C", technique="unexpected_witness"),
        L("s08-t04", "prosecutor", "[scoff] So? That proves *nothing*! Whose phone is that, anyway?", "smug", "dismissive, too confident", 4, 0, kind="question"),
        L("s08-t05", "surprise_witness", "[pause] Device owner. [long pause] Advocate Pinky Malhotra.",
          "serious", "slow, deliberate, each word a gavel strike", 4, 400, kind="testimony", sfx=["crowd_gasp"],
          reactions={"prosecutor": "shocked", "defendant": "shocked", "judge": "gasp"}, scores="defense", points=3, technique="dramatic_irony"),
        L("s08-t06", "defendant", "[pause] You liked a meme about *me*? At three forty-seven? [pause] Ma'am. I wasn't even *up* yet.",
          "confused", "slow, sleepy, genuinely hurt", 3, 500, sfx=["crowd_laugh"]),
        L("s08-t07", "prosecutor", "[long pause] [nervous laugh] My Lord... that was... legal research. [pause] Very deep research. Reel by reel.",
          "nervous", "tiny voice, sweating, all the Delhi gone out of her", 2, 1100, reactions={"defense": "smirk", "judge": "facepalm"}),
        L("s08-t08", "judge", "Order! *Order!* [inhales] Advocate Malhotra. [long pause] You slept at three forty-seven... and blamed *Monday*?",
          "angry", "booming, then deadly quiet", 4, 300, kind="question", sfx=["gavel"]),
        L("s08-t09", "prosecutor", "It was *just one more reel*, My Lord! [exhales] Everybody says 'just one more reel'! [pause] *Nobody* means it!",
          "desperate", "cracking, defensive, far too loud", 5, 200, sfx=["crowd_laugh"], technique="callback"),
    ]),
    Scene(id="s09", phase=Phase.CLOSING_ARGUMENTS, title="Closing Arguments", window=_vote("s09", True), turns=[
        L("s09-t01", "prosecutor", "Members of the jury. Yes. I watched reels till three forty-seven. [pause] But who made me *dread* the morning? Who brought the 'Hi'? Who brought the two-hour quick call? [pause] Monday. Every week. Since birth. Find him *guilty*!",
          "dramatic", "wounded, then rallying to a thunderous finish", 5, 300, scores="prosecution", points=1, technique="callback"),
        L("s09-t02", "defense", "My client didn't send the 'Hi'. My client didn't watch the reels. My client didn't even make the chai cold. [pause] My client just *showed up*. On time. Every week. [pause] In this country, My Lord, that alone deserves a medal.",
          "smug", "quiet, warm, then a soft knockout punch", 4, 300, scores="defense", points=1, technique="callback"),
        L("s09-t03", "defendant", "[pause] I just want everyone to know... I'm not the villain. [pause] I'm just the morning after the night you didn't sleep.",
          "sad", "small, sincere, sleepy, a little heartbreaking", 3, 1000, technique="callback"),
    ]),
    Scene(id="s10", phase=Phase.DELIBERATION, title="Deliberation", turns=[
        L("s10-t01", "reporter", "Breaking news! Mummy drinks her chai hot on Mondays. Papa doesn't even *have* Mondays. The manager has been taken offline. And the prosecutor was up till three forty-seven liking reels about the accused! [pause] The jury is deliberating. Mummy has asked everyone to remove their shoes.",
          "dramatic", ANCHOR, 4, 300, kind="recap"),
        L("s10-t02", "judge", "[long pause] The court has weighed the evidence. [pause] The court has also set an alarm for six twenty. 'Really last chance.' [pause] Let us proceed.",
          "deadpan", "slow, ceremonial, faintly exhausted", 3, 800),
    ]),
    Scene(id="v_guilty", phase=Phase.VERDICT, title="The Verdict", branch="verdict_guilty", turns=[
        L("vg-t01", "judge", "Will the accused please rise. [pause] Rise. *Rise*, Monday, I know you can. [pause] On the charge of emotional damage to every Indian household, this court finds Monday Morning: [long pause] *guilty*.",
          "stern", "slow, enormous, each word a gavel strike", 5, 600, kind="verdict", sfx=["gavel"], reactions={"defendant": "shocked", "defense": "facepalm"}),
        L("vg-t02", "judge", "Monday will now start at eleven AM. Forever. Every nine AM meeting must serve hot chai and samosa. Mr. Khanna may never say 'quick call' again. [pause] And Advocate Malhotra's phone will be kept by Mummy after eleven PM. Court is adjourned.",
          "deadpan", "formal, unhurried, then abruptly done", 3, 400, kind="sentence", sfx=["gavel"], reactions={"prosecutor": "sweat"}, technique="absurd_punishment"),
        L("vg-t03", "defendant", "[gasp] Eleven AM?! [pause] That's... honestly that's the best thing that has ever happened to me. [laugh] Wait. Is this a punishment?",
          "confused", "sleepy shock turning into delight", 4, 300, technique="callback"),
        L("vg-t04", "reporter", "And there you have it! Monday convicted, the nation sleeps in! [pause] This has been The Court of Absolute Nonsense. Now go and take a bath.",
          "triumphant", ANCHOR, 4, 400, kind="recap", sfx=["crowd_laugh"]),
    ]),
    Scene(id="v_not_guilty", phase=Phase.VERDICT, title="The Verdict", branch="verdict_not_guilty", turns=[
        L("vn-t01", "judge", "Will the accused please rise. [pause] Rise, Monday. On the charge of emotional damage to every Indian household, this court finds Monday Morning: [long pause] *not guilty*. [sigh] Reluctantly.",
          "stern", "slow, enormous, with a grudging sigh at the end", 5, 600, kind="verdict", sfx=["gavel"], reactions={"defendant": "laugh", "prosecutor": "facepalm"}),
        L("vn-t02", "judge", "The real culprit was Sunday night and *one more reel*. Advocate Malhotra's phone is confiscated after eleven PM. By Mummy. [pause] The accused is free to go. [sigh] He'll be back in six days anyway.",
          "deadpan", "dry, tired, faintly fond", 3, 400, kind="sentence", reactions={"prosecutor": "sweat"}, technique="absurd_punishment"),
        L("vn-t03", "defendant", "[laugh] I'm free! See you all next week! [pause] Six AM sharp. Don't snooze me.",
          "triumphant", "sleepy voice finally lit up, cheeky", 4, 300, technique="callback"),
        L("vn-t04", "reporter", "And there you have it! Monday walks free, and Sunday night has some explaining to do! [pause] This has been The Court of Absolute Nonsense. Now go and take a bath.",
          "triumphant", ANCHOR, 4, 400, kind="recap", sfx=["crowd_laugh"]),
    ]),
]

SCRIPT = TrialScript(scenes=SCENES)

CASE_FIELDS = {
    "slug": "the-people-vs-monday-morning",
    "defendant": DEFENDANT,
    "accusation": ACCUSATION,
    "context": "Hand-authored desi special. Mummy, Papa, the manager, and a screen-time twist.",
    "comedy_intensity": "chaos",
    "drama_level": 85,
    "trial_length": "standard",
    "participation_mode": "jury",
    "case_number": PLAN.case_number,
}
