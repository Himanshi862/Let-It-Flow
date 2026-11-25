"""
Let It Flow - Menstrual Health Chatbot (Stage 8)

HOW IT WORKS (runs fully locally - no API key, no internet)
-----------------------------------------------------------
1. SAFETY first   : urgent symptoms / crisis words get a safety message.
2. DIAGNOSIS guard: "Do I have PCOS?" -> we never diagnose; we explain why and
                    show general information.
3. PERSONAL intents (regex rules): "When is my next period?", "What was my
                    last period?" ... answered from the user's own recorded data
                    (MySQL).  If data is missing we SAY so - nothing is invented.
4. KNOWLEDGE BASE retrieval (NLP): the question is cleaned (lowercase,
                    synonyms, light stemming) and compared with every knowledge
                    base entry using TF-IDF vectors + cosine similarity
                    (scikit-learn).  Best match above a threshold is returned.
5. PERSONAL HOOK  : when the matched topic relates to something the user has
                    logged, a short "From your logs" line is added (recorded
                    facts only), separate from the "General information".
6. FALLBACK       : if nothing matches well, we say we are not sure.

No external AI API is needed.  (If you later want one, call it only from
reply_with_llm() below and read the key from an environment variable.)
"""
import re
from datetime import date

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

import repository as repo
from chatbot.knowledge_base import KB
from chatbot.user_context import build_user_context, days_logged
from insights.recommendations import build_recommendations

MATCH_THRESHOLD = 0.22

# ---------------------------------------------------------------- text cleaning
STOPWORDS = set("""a an the is are am was were be been being do does did to of in on at for with and or my me i
you your it its this that these those can could should would will shall may might have has had how what why when
where which who whom about from as by so if then than too very just please tell us""".split())

SYNONYMS = {
    "periods": "period", "menses": "period", "menstruation": "period", "menstrual": "period",
    "mens": "period", "bleed": "bleeding", "bleeds": "bleeding", "cramp": "cramps",
    "cramping": "cramps", "dysmenorrhea": "cramps", "pimples": "acne", "pimple": "acne",
    "breakout": "acne", "tired": "fatigue", "tiredness": "fatigue", "exhausted": "fatigue",
    "exhaustion": "fatigue", "weak": "fatigue", "bloated": "bloating", "workout": "exercise",
    "workouts": "exercise", "gym": "exercise", "yoga": "exercise", "food": "diet", "foods": "diet",
    "eat": "diet", "eating": "diet", "meal": "diet", "meals": "diet", "delayed": "late",
    "delay": "late", "missed": "miss", "missing": "miss", "irregularity": "irregular",
    "pcod": "pcos", "anemia": "anaemia", "migraine": "headache", "headaches": "headache",
    "tension": "stress", "stressed": "stress", "anxiety": "stress", "exams": "exam",
    "pain": "pain", "painful": "pain", "hurts": "pain", "hurt": "pain",
}


def _stem(word):
    for suffix in ("ing", "ed", "es", "s"):
        if len(word) > len(suffix) + 3 and word.endswith(suffix):
            return word[: -len(suffix)]
    return word


def normalise(text):
    """lowercase -> words -> synonyms -> remove stopwords -> light stemming."""
    words = re.findall(r"[a-z0-9']+", text.lower())
    out = []
    for w in words:
        w = SYNONYMS.get(w, w)
        if w in STOPWORDS:
            continue
        out.append(_stem(w))
    return out


# --------------------------------------------------- build the TF-IDF index once
_docs = [" ".join([e["title"], e["title"], " ".join(e["examples"]), e["answer"]]) for e in KB]
_example_texts, _example_owner = [], []
for _i, _e in enumerate(KB):
    for _ex in _e["examples"] + [_e["title"]]:
        _example_texts.append(_ex)
        _example_owner.append(_i)

_vectorizer = TfidfVectorizer(analyzer=lambda t: (lambda toks: toks + [a + "_" + b for a, b in zip(toks, toks[1:])])(normalise(t)),
                              sublinear_tf=True)
_vectorizer.fit(_docs + _example_texts)
_doc_matrix = _vectorizer.transform(_docs)
_example_matrix = _vectorizer.transform(_example_texts)


def retrieve(question, top_k=3):
    """Return [(score, kb_entry), ...] best first."""
    q = _vectorizer.transform([question])
    doc_sim = (_doc_matrix @ q.T).toarray().ravel()
    ex_sim = (_example_matrix @ q.T).toarray().ravel()
    best = doc_sim * 0.8                                     # whole-entry similarity
    for sim, owner in zip(ex_sim, _example_owner):           # best single example question
        best[owner] = max(best[owner], sim)
    order = np.argsort(-best)[:top_k]
    return [(float(best[i]), KB[i]) for i in order]


# ------------------------------------------------------------------ safety
URGENT = re.compile(
    r"(soak(ing|ed)?\s+(through\s+)?(a\s+|one\s+)?(pad|tampon)s?|every\s+hour|can'?t\s+stop\s+bleeding|"
    r"cannot\s+stop\s+bleeding|faint(ed|ing)?|passed\s+out|unconscious|collaps(e|ed)|"
    r"(severe|unbearable|worst)\s+(abdominal|stomach|belly|pelvic)?\s*pain|chest\s+pain|can'?t\s+breathe)", re.I)
CRISIS = re.compile(r"(suicid|kill\s+myself|end\s+my\s+life|want\s+to\s+die|hurt\s+myself|self[- ]?harm)", re.I)
DIAGNOSIS = re.compile(
    r"\b(do|does|did)\s+i\s+have\b|\bam\s+i\s+(suffering|having|diagnosed)\b|\bis\s+it\s+(pcos|pcod|thyroid|"
    r"endometriosis)\b|\bdiagnos(e|is)\s+me\b|\bwhat\s+(disease|condition)\s+do\s+i\b", re.I)

URGENT_REPLY = ("This could be urgent. If you are bleeding very heavily (soaking a pad or tampon every hour), "
                "feel faint, have severe pain, or feel very unwell, please seek medical care now - go to the "
                "nearest hospital or emergency department, or call 112 in India. I can share general "
                "information, but I cannot assess an emergency.")
CRISIS_REPLY = ("I'm really sorry you're feeling this way, and I'm glad you said it. You deserve support right "
                "now. If you might act on these thoughts or are in danger, please call 112 or go to the nearest "
                "emergency room. In India you can also call the Tele-MANAS helpline at 14416, available any time. "
                "If you can, tell someone you trust - a friend, family member or warden - so you are not alone.")


# ------------------------------------------------------ personal-intent rules
def _has(text, *patterns):
    return any(re.search(p, text, re.I) for p in patterns)


def _fmt(d):
    return d.strftime("%d %b %Y")


def _personal_intent(text):
    t = text.lower()
    rules = [
        ("recall_chats", [r"what did i (ask|say|tell)", r"(previous|earlier|last) (chat|conversation|time)", r"remember (me|what)"]),
        ("late_status", [r"(is|am) (my|i).{0,20}(late|delayed|overdue)", r"how many days late", r"why is my period late.*my"]),
        ("last_period", [r"(my )?(last|latest|previous|most recent) period", r"when did (my|i).{0,25}(start|period)"]),
        ("next_period", [r"next period", r"when (will|is|do|should).{0,25}period", r"when.{0,15}period.{0,10}(due|come)", r"predict(ed|ion)? (my|the next)"]),
        ("history", [r"(my|list|show).{0,15}(period )?(history|dates|records)", r"previous periods", r"past periods"]),
        ("cycle_length", [r"my (average |usual |typical )?cycle (length|lengths)", r"how long (is|are) my (cycle|cycles)", r"my cycles?\b.*(days|long)"]),
        ("regularity", [r"(am i|is my).{0,20}(irregular|regular|normal)", r"my (cycle )?pattern", r"irregular.{0,10}analysis", r"my periods.{0,12}(regular|irregular)"]),
        ("symptoms", [r"my (symptoms|pain|cramps)", r"what (have|did) i (log|logged|record)", r"how (bad|much).{0,20}my (pain|cramps)"]),
        ("lifestyle", [r"my (sleep|stress|lifestyle|exercise)", r"how (have|am) i (been )?(sleeping|doing)"]),
        ("phase_now", [r"(which|what).{0,10}phase", r"current phase", r"what day of my cycle", r"cycle day", r"where am i in my cycle"]),
        ("greeting", [r"^(hi|hello|hey|hii+|namaste|good (morning|evening|afternoon))\b"]),
        ("thanks", [r"^(thanks|thank you|thx|ok thanks)\b"]),
        ("about_bot", [r"who are you", r"what can you do", r"help me$", r"^help$"]),
    ]
    for name, pats in rules:
        if _has(t, *pats):
            return name
    return None


def _personal_answer(intent, ctx):
    """Answers built only from recorded data. Returns the reply text."""
    snap = ctx["snapshot"]
    pred = ctx["prediction"]
    starts = ctx["starts"]

    if intent == "greeting":
        return (f"Hi {ctx['name']}! I'm the Let It Flow assistant. I can answer questions about periods and "
                "cycles, and look at the dates and symptoms you have logged. What would you like to know?")
    if intent == "thanks":
        return "You're welcome! Ask me anything else about your cycle whenever you like."
    if intent == "about_bot":
        return ("I can: explain cycle basics, cramps, late periods and other topics; tell you what is "
                "recorded in your own logs (last period, cycle lengths, symptoms); and explain your "
                "estimates. I can't diagnose conditions or replace a doctor.")

    if intent == "last_period":
        if not starts:
            return "You haven't logged any period dates yet, so I can't say. Add your last period start date on the Cycle Tracker."
        ago = ctx["days_since_last"]
        return (f"Recorded in your logs: your most recent period started on {_fmt(starts[-1])} "
                f"({ago} day(s) ago).")

    if intent == "history":
        if not starts:
            return "No period dates are logged yet. You can add past dates on the Cycle Tracker."
        lines = [f"- {_fmt(d)}" for d in reversed(starts[-8:])]
        extra = f"\n(Showing the latest {min(8, len(starts))} of {len(starts)} recorded dates.)"
        return "Recorded period start dates in your logs:\n" + "\n".join(lines) + extra

    if intent == "cycle_length":
        iv = ctx["usable_intervals"]
        if not iv:
            tl = ctx["profile"].get("typical_cycle_length")
            if tl:
                return (f"You haven't logged enough dates to calculate it yet. You told us your typical "
                        f"cycle is about {tl} days - that is your own estimate, not a calculated value.")
            return "I need at least two period start dates to calculate a cycle length. Please add some on the Cycle Tracker."
        return (f"Recorded in your logs: {len(iv)} cycle(s) calculated from your dates. Average {ctx['mean_cycle']} "
                f"days, shortest {min(iv)}, longest {max(iv)}. Most recent: {iv[-1]} days."
                + ("\nWith only a few cycles recorded, treat this average as rough." if len(iv) < 3 else ""))

    if intent in ("next_period", "late_status"):
        if not pred["available"]:
            return ("I can't estimate your next period yet - " + (pred["notes"][0] if pred["notes"] else
                    "please log more period dates."))
        msg = (f"Estimate (not a guaranteed date): your next period may start around {_fmt(pred['next_start'])}, "
               f"most likely between {_fmt(pred['range_start'])} and {_fmt(pred['range_end'])}. "
               f"Method: {pred['method_label']}. Confidence: {pred['confidence']} "
               f"(based on {pred['n_usable']} logged cycle(s)).")
        if pred["days_late"]:
            msg += (f"\nFrom your logs: that window has passed - your period appears {pred['days_late']} day(s) "
                    "later than estimated. Common reasons include stress, routine changes and illness; if you "
                    "might be pregnant, a pregnancy test is the quickest check, and if it is more than 2 months "
                    "late please see a doctor.")
        elif pred["days_until"] is not None:
            msg += f"\nThat is about {pred['days_until']} day(s) from today."
        return msg

    if intent == "regularity":
        a = ctx["analysis"]
        if a["status"] == "not_enough_data":
            return ("I don't have enough logged cycles to judge your pattern (I need at least 3 cycles, "
                    "i.e. 4 period dates). Add past dates on the Cycle Tracker.")
        s = a["stats"]
        top = [f["title"] for f in a["findings"] if f["severity"] in ("talk", "notice")][:3]
        msg = (f"Pattern status from your logs: {a['status_label']}. Average cycle {s['mean']} days, "
               f"shortest {s['shortest']}, longest {s['longest']}.")
        if top:
            msg += "\nThings to notice: " + "; ".join(top) + "."
        msg += "\nThis is an automated observation, not a diagnosis. See the Cycle Intelligence page for details."
        return msg

    if intent == "symptoms":
        pain, n = ctx["pain"]
        if not ctx["sym30"] and n == 0:
            return "You haven't logged symptoms recently, so I can't summarise them. Try the Daily Log page."
        parts = []
        if n:
            parts.append(f"average pain {pain:.1f}/10 over {n} recent day(s)")
        for key, label in [("fatigue", "fatigue"), ("bloating", "bloating"), ("headache", "headaches"),
                           ("acne", "acne"), ("mood", "mood changes")]:
            d = days_logged(ctx, key)
            if d:
                parts.append(f"{label} on {d} of the last 30 days")
        return "Recorded in your logs: " + ("; ".join(parts) if parts else "entries exist but no symptom levels were filled in") + "."

    if intent == "lifestyle":
        parts = []
        sl, n = ctx["sleep"]
        if n:
            parts.append(f"average sleep {sl:.1f} h")
        st, n2 = ctx["stress"]
        if n2:
            parts.append(f"average stress {st:.1f}/5")
        ex, n3 = ctx["exercise"]
        if n3:
            parts.append(f"average exercise {ex:.0f} min/day")
        if not parts:
            return "You haven't logged sleep, stress or exercise recently. Add them on the Daily Log page."
        return "Recorded in the last 14 days: " + "; ".join(parts) + "."

    if intent == "phase_now":
        if ctx["cycle_day"] is None:
            return "I need your last period start date to place you in a cycle phase."
        names = {"menstrual": "menstrual", "follicular": "follicular", "ovulatory": "mid-cycle", "luteal": "luteal"}
        return (f"Based on your last recorded period ({_fmt(ctx['last_start'])}), today is day {ctx['cycle_day']} "
                f"of this cycle. The approximate phase is {names.get(ctx['phase'], ctx['phase'])}. "
                "Phase is a rough estimate from day count - real hormone levels vary between people.")

    if intent == "recall_chats":
        return None        # handled in reply() because it needs DB access
    return None


# ------------------------------------------------------- personal hooks for KB
def _hook(entry, ctx):
    """One short 'From your logs' line related to the matched topic (recorded facts only)."""
    tags = set(entry["tags"])
    pred = ctx["prediction"]
    if "late" in tags and ctx["days_since_last"] is not None and ctx["mean_cycle"]:
        return (f"From your logs: your last period started {ctx['days_since_last']} day(s) ago; "
                f"your recorded average cycle is {ctx['mean_cycle']} days.")
    if {"cycle_length", "regularity"} & tags and ctx["usable_intervals"]:
        iv = ctx["usable_intervals"]
        return (f"From your logs: {len(iv)} cycle(s) recorded, average {ctx['mean_cycle']} days "
                f"(shortest {min(iv)}, longest {max(iv)}).")
    if {"cramps", "pain"} & tags and ctx["pain"][1]:
        return f"From your logs: your recorded pain averaged {ctx['pain'][0]:.1f}/10 over {ctx['pain'][1]} recent day(s)."
    for key, label in [("fatigue", "fatigue"), ("bloating", "bloating"), ("headache", "headaches"),
                       ("acne", "acne"), ("mood", "mood changes")]:
        if key in tags or (key == "mood" and "pms" in tags):
            d = days_logged(ctx, key)
            if d:
                return f"From your logs: you recorded {label} (moderate or strong) on {d} of the last 30 days."
    if {"sleep", "stress"} & tags:
        sl, n = ctx["sleep"]
        st, n2 = ctx["stress"]
        bits = []
        if n:
            bits.append(f"average sleep {sl:.1f} h")
        if n2:
            bits.append(f"average stress {st:.1f}/5")
        if bits:
            return "From your logs (last 14 days): " + ", ".join(bits) + "."
    if "period_length" in tags and ctx["snapshot"]["period_length"]:
        return f"From your profile and logs: your period usually lasts about {ctx['snapshot']['period_length']} day(s)."
    if "phase" in tags and ctx["cycle_day"]:
        return f"From your logs: today is about day {ctx['cycle_day']} of your current cycle."
    if "prediction" in tags and pred["available"]:
        return (f"From your logs: your current estimate uses {pred['n_usable']} cycle(s); "
                f"confidence is {pred['confidence']}.")
    if "diet" in tags and entry["id"] in ("diet_period", "iron_fatigue") and ctx["diet_pref"].get("diet_type"):
        rec = build_recommendations(ctx["phase"], ctx["diet_pref"].get("diet_type"), ctx["diet_pref"].get("dislikes"),
                                    ctx["exercise_pref"].get("activity_level"), ctx["exercise_pref"].get("preferred_exercise"),
                                    ctx["diet_pref"].get("skips_meals_often"), ctx["snapshot"]["symptoms"])
        return ("Matching your saved diet preference (" + rec["diet_label"] + "): "
                + "; ".join(rec["foods"][:3]) + ".")
    return None


FOOTER = "General information only - not medical advice."


# ------------------------------------------------------------------ main entry
def reply(user_id, message, conv_id=None, history=None):
    """
    Returns (reply_text, intent_name).
    user_id  : the logged-in user (comes from the SESSION, never from the request body)
    history  : previous messages of THIS conversation [{'role','content'}, ...]
    """
    text = (message or "").strip()[:500]
    if not text:
        return "Please type a question.", "empty"

    if CRISIS.search(text):
        return CRISIS_REPLY, "crisis"

    ctx = build_user_context(user_id)

    if URGENT.search(text):
        return URGENT_REPLY, "urgent"

    intent = _personal_intent(text)
    if intent == "recall_chats":
        past = repo.recent_user_questions(user_id, limit=4, exclude_conv=conv_id)
        if not past:
            return "I don't have earlier conversations with you yet.", intent
        return ("Your recent questions from earlier chats:\n"
                + "\n".join(f"- {p['content'][:90]}" for p in past)), intent
    if intent:
        answer = _personal_answer(intent, ctx)
        if answer:
            return answer, intent

    # ---- diagnosis guard
    if DIAGNOSIS.search(text):
        entry = next(e for e in KB if e["id"] == "conditions_info")
        extra = ""
        if ctx["analysis"]["status"] != "not_enough_data":
            extra = (f"\n\nFrom your logs: your pattern status is \"{ctx['analysis']['status_label']}\". "
                     "That is an automated observation about cycle dates, not a diagnosis.")
        return ("I can't diagnose conditions, and an app can't either.\n\n" + entry["answer"] + extra), "diagnosis_guard"

    # ---- knowledge base retrieval (with a little conversation memory)
    query = text
    if history and len(normalise(text)) <= 2 and len(text.split()) <= 3:   # a short follow-up like "and why?"
        prev_user = [m["content"] for m in history if m["role"] == "user"]
        if prev_user:
            query = prev_user[-1] + " " + text          # short follow-up, e.g. "and why?"
    results = retrieve(query)
    score, entry = results[0]
    if score < MATCH_THRESHOLD:
        return ("I'm not sure I have reliable information on that. I can help with period and cycle basics, "
                "cramps, late or irregular periods, stress, sleep, food and exercise, or look at your own "
                "logged dates and symptoms. You could also rephrase, or ask a doctor for anything specific "
                "to your health."), "fallback"

    parts = [f"{entry['title']}\n{entry['answer']}"]
    hook = _hook(entry, ctx)
    if hook:
        parts.append(hook)
    related = [e["title"] for s, e in results[1:] if s >= MATCH_THRESHOLD * 0.8 and e["id"] != entry["id"]]
    if related:
        parts.append("You might also ask about: " + "; ".join(related[:2]) + ".")
    parts.append(FOOTER)
    return "\n\n".join(parts), "kb:" + entry["id"]


def reply_with_llm(user_id, message):                    # pragma: no cover
    """
    OPTIONAL: where an external AI API could be plugged in later.
    Read the key from an environment variable (e.g. os.environ['LLM_API_KEY']);
    never write it in the source code.  Send only the recorded facts from
    build_user_context(user_id) and the retrieved knowledge-base text.
    The project works fully without this.
    """
    raise NotImplementedError("Local chatbot is used by default.")
