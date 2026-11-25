"""
Let It Flow - personalised nutrition & exercise guidance (Stage 7)

Rule-based on purpose: every suggestion can be traced to a reason shown to the
user.  General wellness ideas only - NOT medical treatment, no products, no
shopping links.  Foods are affordable, common Indian options.

Personalisation inputs
  * dietary preference  (vegan / vegetarian / eggetarian / non-vegetarian)
  * disliked foods      (filtered out)
  * cycle phase         (educational approximation)
  * recent symptoms     (pain, fatigue, bloating, headache)
  * activity level and preferred exercise
  * skipping meals
"""

# diet "levels": a person on level N can eat anything with level <= N
DIET_LEVEL = {"vegan": 0, "vegetarian": 1, "eggetarian": 2, "non_vegetarian": 3}

# (text, minimum diet level, phases it suits, tags)
FOODS = [
    ("Rajma chawal with a squeeze of lemon", 0, ["menstrual", "follicular", "luteal"], ["iron", "protein", "budget"]),
    ("Chole with roti and sliced onion-tomato salad", 0, ["menstrual", "luteal"], ["iron", "fibre", "budget"]),
    ("Palak dal with roti (add lemon for vitamin C)", 0, ["menstrual"], ["iron", "budget"]),
    ("Sprouts chaat with tomato, onion and lemon", 0, ["menstrual", "follicular", "ovulatory"], ["iron", "protein", "budget"]),
    ("Roasted chana (chickpeas) as an evening snack", 0, ["menstrual", "luteal"], ["iron", "fibre", "budget"]),
    ("Soya chunk curry or soya pulao", 0, ["follicular", "ovulatory"], ["protein", "budget"]),
    ("Tofu bhurji with vegetables and roti", 0, ["follicular", "ovulatory"], ["protein"]),
    ("Dal tadka with brown rice or roti", 0, ["follicular", "luteal"], ["protein", "fibre", "budget"]),
    ("Moong or besan chilla with green chutney", 0, ["follicular", "ovulatory"], ["protein", "budget"]),
    ("Vegetable khichdi (comfort food on heavy days)", 0, ["menstrual", "luteal"], ["comfort", "budget"]),
    ("Ragi porridge or ragi roti", 0, ["menstrual", "luteal"], ["iron", "fibre"]),
    ("Poha with peanuts and vegetables", 0, ["follicular", "ovulatory"], ["budget"]),
    ("Dalia (broken wheat) with vegetables", 0, ["luteal", "follicular"], ["fibre", "budget"]),
    ("Banana with a handful of peanuts", 0, ["luteal", "menstrual"], ["budget", "magnesium"]),
    ("Seasonal fruit - guava, orange, papaya or amla", 0, ["menstrual", "ovulatory", "follicular"], ["vitamin_c", "hydration", "budget"]),
    ("Cucumber, carrot and tomato salad", 0, ["ovulatory", "follicular"], ["hydration", "budget"]),
    ("Coconut water or nimbu paani", 0, ["ovulatory", "menstrual"], ["hydration", "budget"]),
    ("Roasted makhana (fox nuts) for evening cravings", 0, ["luteal"], ["budget"]),
    ("Til (sesame) and jaggery chikki - a small piece", 0, ["menstrual", "luteal"], ["iron"]),
    ("Idli or dosa with sambar", 0, ["follicular", "ovulatory"], ["budget"]),
    ("Paneer bhurji with multigrain roti", 1, ["follicular", "ovulatory"], ["protein"]),
    ("Curd or raita with lunch", 1, ["ovulatory", "luteal", "follicular"], ["hydration", "budget"]),
    ("Chaas (buttermilk) with roasted jeera", 1, ["ovulatory", "luteal"], ["hydration", "budget"]),
    ("Warm haldi doodh (turmeric milk) at night", 1, ["menstrual", "luteal"], ["comfort", "budget"]),
    ("Paneer or tofu sandwich with curd chutney", 1, ["luteal", "follicular"], ["protein"]),
    ("Boiled eggs or egg bhurji with roti", 2, ["menstrual", "follicular", "luteal"], ["protein", "iron", "budget"]),
    ("Vegetable omelette with toast", 2, ["follicular", "ovulatory"], ["protein", "budget"]),
    ("Home-style chicken curry with roti and salad", 3, ["menstrual", "follicular"], ["iron", "protein"]),
    ("Fish curry with rice and a vegetable side", 3, ["ovulatory", "luteal"], ["protein"]),
]

PHASE_TEXT = {
    "menstrual": ("Iron and comfort focus",
                  "Some iron is lost with bleeding, so iron-containing foods paired with vitamin C "
                  "(lemon, guava, orange) are a practical choice. Warm, simple meals can feel good."),
    "follicular": ("Protein and whole grains",
                   "Energy often rises after your period. Steady meals with protein and whole grains "
                   "help you stay full through classes and study sessions."),
    "ovulatory": ("Hydration and fresh produce",
                  "Many people feel energetic mid-cycle. Water, fruit and vegetables plus regular meals "
                  "are a simple, affordable focus."),
    "luteal": ("Fibre and steady meals",
               "Appetite and cravings can change before a period. Regular meals with fibre and "
               "complex carbohydrates (dal-roti, dalia, ragi) can help avoid big energy dips."),
}

EXERCISE_TEXT = {
    "menstrual": ("Gentle movement",
                  "Light movement is safe for most people and some find it eases cramps. Rest if you "
                  "feel unwell - there is no rule that you must exercise."),
    "follicular": ("Build momentum",
                   "Energy often trends up. A good time to try longer or slightly harder sessions if "
                   "you feel like it."),
    "ovulatory": ("Active days",
                  "Many people feel strongest mid-cycle. Warm up well and keep drinking water."),
    "luteal": ("Steady and kind to yourself",
               "Energy can dip before a period. Moderate sessions, yoga and stretching often feel better "
               "than pushing hard."),
}

# preferred exercise -> activity ideas (kept simple and free)
EXERCISES = {
    "walking": ["Brisk walk around campus or hostel ground", "Walk during a phone call or between classes"],
    "yoga": ["Gentle yoga or stretching from a free video", "Child's pose, cat-cow, supine twist"],
    "gym": ["Strength session with basic compound moves", "Machine circuit with longer rest"],
    "home": ["Bodyweight squats, glute bridges, planks", "Beginner pilates at home"],
    "cardio": ["Jogging, skipping rope or cycling", "Dance workout from a free video"],
}
DEFAULT_EX = "walking"

PHASE_INTENSITY = {
    "menstrual": "light (10-25 minutes)",
    "follicular": "light to moderate (20-45 minutes)",
    "ovulatory": "moderate (30-45 minutes)",
    "luteal": "light to moderate (20-35 minutes)",
}


def _normalise_diet(value):
    value = (value or "").lower().replace("-", "_").replace(" ", "_")
    if value in DIET_LEVEL:
        return value
    if value in ("veg", "vegetarian"):
        return "vegetarian"
    if value in ("non_veg", "nonveg", "non_vegetarian"):
        return "non_vegetarian"
    return None


def _symptom_reasons(symptoms):
    """Look at the last 14 logged days and note what stands out (recorded facts only)."""
    recent = symptoms[:14]
    reasons = []

    def avg(key):
        vals = [s[key] for s in recent if s.get(key) is not None]
        return (sum(vals) / len(vals), len(vals)) if vals else (None, 0)

    pain, n = avg("pain_severity")
    if pain is not None and pain >= 5:
        reasons.append(("pain", f"Your logged pain averaged {pain:.1f}/10 over {n} recent day(s)."))
    fatigue, n = avg("fatigue")
    if fatigue is not None and fatigue >= 2:
        reasons.append(("fatigue", f"You logged fatigue on {n} recent day(s) (average {fatigue:.1f}/3)."))
    bloat, n = avg("bloating")
    if bloat is not None and bloat >= 2:
        reasons.append(("bloating", f"You logged bloating on {n} recent day(s)."))
    head, n = avg("headache")
    if head is not None and head >= 2:
        reasons.append(("headache", f"You logged headaches on {n} recent day(s)."))
    return reasons


def build_recommendations(phase, diet_type, dislikes, activity_level, preferred_exercise,
                          skips_meals, symptoms, extra_dislikes=""):
    """Return a dict the Nutrition & Exercise page can show directly."""
    phase = phase if phase in PHASE_TEXT else "follicular"
    diet = _normalise_diet(diet_type)
    level = DIET_LEVEL.get(diet, 1)          # unknown diet -> assume vegetarian (safe choice)
    reasons = _symptom_reasons(symptoms)
    reason_keys = {k for k, _ in reasons}

    blocked = [w.strip().lower() for w in (str(dislikes or "") + "," + str(extra_dislikes or "")).split(",")
               if w.strip()]

    def allowed(food):
        text = food[0].lower()
        return food[1] <= level and not any(b in text for b in blocked)

    # score foods: phase match first, then tags that match what the user logged
    wanted_tags = set()
    if "fatigue" in reason_keys or phase == "menstrual":
        wanted_tags.add("iron")
    if "bloating" in reason_keys:
        wanted_tags.add("hydration")
    if "pain" in reason_keys:
        wanted_tags |= {"magnesium", "comfort"}
    if "headache" in reason_keys:
        wanted_tags.add("hydration")

    scored = []
    for food in FOODS:
        if not allowed(food):
            continue
        score = (2 if phase in food[2] else 0) + len(wanted_tags & set(food[3])) + (0.5 if "budget" in food[3] else 0)
        if score > 0:
            scored.append((score, food))
    scored.sort(key=lambda x: -x[0])
    foods = [f[0] for _, f in scored[:6]]

    # ---- exercise ----
    ex_key = preferred_exercise if preferred_exercise in EXERCISES else DEFAULT_EX
    ideas = list(EXERCISES[ex_key])
    intensity = PHASE_INTENSITY[phase]
    if activity_level == "sedentary":
        intensity = "start small: 10-20 minutes, building slowly"
    if "pain" in reason_keys:
        ideas = ["Gentle stretching or yoga (hip openers, child's pose)",
                 "A slow walk, and a warm compress on the lower belly"] + ideas[:1]
    if phase == "menstrual" and "pain" not in reason_keys:
        ideas = ideas[:2] + ["Rest fully if you feel unwell - that is fine"]

    tips = []
    if skips_meals:
        tips.append("You said you often skip meals. Regular meals - even a simple roti-sabzi or "
                    "banana and peanuts - help keep energy steady. Not eating enough for long periods "
                    "can be linked with changes in periods.")
    if "fatigue" in reason_keys:
        tips.append("Feeling tired often? Iron-containing foods with vitamin C help, and so does "
                    "7-8 hours of sleep. If tiredness is constant, a doctor can check for anaemia.")
    if "bloating" in reason_keys:
        tips.append("For bloating: smaller regular meals, enough water, and going easy on very salty "
                    "packaged snacks can help some people.")
    if "headache" in reason_keys:
        tips.append("For headaches: drink water regularly and avoid long gaps between meals.")
    if "pain" in reason_keys:
        tips.append("For cramps: warmth, gentle movement and rest help many people. Pain that is "
                    "severe or stops your daily life is worth discussing with a doctor.")
    tips.append("Aim for about 2-3 litres of water a day unless a doctor told you otherwise.")

    return {
        "phase": phase,
        "diet_title": PHASE_TEXT[phase][0], "diet_text": PHASE_TEXT[phase][1],
        "foods": foods,
        "ex_title": EXERCISE_TEXT[phase][0], "ex_text": EXERCISE_TEXT[phase][1],
        "exercises": ideas, "intensity": intensity,
        "tips": tips, "reasons": [r for _, r in reasons],
        "diet_label": (diet or "not set").replace("_", "-"),
        "diet_known": diet is not None,
    }
