"""
Let It Flow - menstrual-health knowledge base.

Each entry:
  id        short name
  title     shown to the user
  tags      used to add 'From your logs' lines (see chatbot.py)
  examples  sample questions (the NLP matcher compares the user's question to
            these AND to the answer text)
  answer    plain-language education.  Never a diagnosis.

General guidance is consistent with public information from ACOG, NHS and WHO.
It is educational and not a substitute for a doctor.
"""

KB = [
    {"id": "phases", "title": "The four phases of the menstrual cycle", "tags": ["phase"],
     "examples": ["what are the phases of the menstrual cycle", "explain cycle phases",
                  "what happens during my cycle", "menstrual follicular ovulation luteal"],
     "answer": "A cycle is often described in four phases:\n"
               "- Menstrual: bleeding days, the start of a new cycle (day 1 = first day of bleeding).\n"
               "- Follicular: after bleeding, the body prepares an egg; energy often rises.\n"
               "- Ovulation (mid-cycle): an egg is released, usually around the middle of the cycle.\n"
               "- Luteal: the second half, before the next period; PMS symptoms can show up here.\n"
               "Timing differs from person to person, and the phase shown in the app is only an approximation."},
    {"id": "cycle_length_meaning", "title": "What cycle length means", "tags": ["cycle_length"],
     "examples": ["what is cycle length", "how do I count my cycle length", "how long is a cycle",
                  "how to calculate cycle length"],
     "answer": "Cycle length is the number of days from the FIRST day of one period to the day before "
               "the first day of the next one. Example: periods starting 1 March and 29 March give a "
               "28-day cycle. It is normal for it to vary by a few days from month to month."},
    {"id": "normal_cycle", "title": "What is a normal cycle length?", "tags": ["cycle_length", "regularity"],
     "examples": ["what is a normal cycle length", "is 35 days normal", "is my cycle normal",
                  "how many days should a cycle be", "is a 28 day cycle normal", "short cycle", "long cycle"],
     "answer": "For most adults a cycle of about 24-38 days is considered within the usual range (often "
               "quoted as 21-35 days). In teenagers and the first years after periods begin, cycles up "
               "to 45 days can be normal. A difference of up to roughly 7-9 days between your shortest "
               "and longest recent cycle is commonly seen. Cycles that are repeatedly outside these "
               "ranges are worth mentioning to a doctor."},
    {"id": "period_duration", "title": "How long should a period last?", "tags": ["period_length"],
     "examples": ["how long should my period last", "period duration", "is a 7 day period normal",
                  "my period lasts too long", "how many days of bleeding is normal"],
     "answer": "Bleeding usually lasts about 2-7 days. Periods that regularly last longer than 7 days, "
               "or that are very heavy, are worth discussing with a doctor."},
    {"id": "cramps_cause", "title": "Why do period cramps happen?", "tags": ["cramps", "pain"],
     "examples": ["why do I get cramps", "why am I having period cramps", "what causes period pain",
                  "dysmenorrhea", "stomach pain during period", "lower abdominal pain period"],
     "answer": "Cramps are usually caused by the womb muscle contracting to shed its lining. Chemicals "
               "called prostaglandins drive these contractions - higher levels are linked with stronger "
               "cramps. Mild to moderate cramps in the first days of a period are very common. Pain that "
               "is severe, getting worse over time, or not controlled by usual self-care should be checked "
               "by a doctor."},
    {"id": "cramps_relief", "title": "Easing period cramps", "tags": ["cramps", "pain"],
     "examples": ["how to reduce period cramps", "how can I relieve period pain", "home remedies for cramps",
                  "what helps with cramps", "heating pad period pain", "exercise for cramps"],
     "answer": "Things many people find helpful:\n- A warm compress or hot water bag on the lower belly.\n"
               "- Gentle movement: walking, stretching, easy yoga.\n- Staying hydrated and eating regular, "
               "simple meals.\n- Rest and enough sleep.\n- Over-the-counter pain relief used exactly as the "
               "label says - ask a pharmacist or doctor if you are unsure or have other conditions.\n"
               "If pain is severe or stops you from attending classes, see a doctor."},
    {"id": "severe_pain", "title": "When period pain needs a doctor", "tags": ["pain", "doctor"],
     "examples": ["severe period pain", "unbearable cramps", "pain so bad I miss college",
                  "when should I worry about period pain", "pain not going away with medicine"],
     "answer": "Please see a doctor if period pain: is severe or keeps you from daily activities; is not "
               "helped by usual pain relief; is getting worse over the months; or comes with fainting, "
               "vomiting, fever or very heavy bleeding. You deserve proper care - painful periods are "
               "common but should not be ignored when they are severe."},
    {"id": "heavy_bleeding", "title": "Heavy bleeding - when to get help", "tags": ["bleeding", "doctor"],
     "examples": ["heavy period", "how much bleeding is too much", "soaking pads", "large clots",
                  "bleeding too much", "flooding period"],
     "answer": "Heavy bleeding needs medical attention if you: soak through a pad or tampon every hour for "
               "2 or more hours; pass clots larger than a coin; bleed for more than 7 days; or feel dizzy, "
               "faint, breathless or very weak. If it is happening right now, seek urgent care. Heavy periods "
               "can also lead to low iron, so tiredness is worth mentioning to a doctor."},
    {"id": "late_period", "title": "Why might a period be late?", "tags": ["late", "cycle_length"],
     "examples": ["why is my period late", "period is delayed", "late period reasons", "period not coming",
                  "why might my period be late", "my period has not started"],
     "answer": "A late period can have many causes: stress (including exam stress), poor sleep, illness, "
               "travel or a change of routine, big changes in weight or exercise, skipping meals, some "
               "medicines, or pregnancy. Medical conditions can also be behind repeated delays - only a doctor "
               "can find out. If you could be pregnant, a home pregnancy test is the quickest check. If your "
               "period is more than about 2 months late, or you are worried, please see a doctor."},
    {"id": "missed_periods", "title": "Missed periods and long gaps", "tags": ["late", "doctor"],
     "examples": ["I missed my period", "missed periods for months", "no period for 3 months",
                  "amenorrhea", "long gap between periods", "no periods"],
     "answer": "Missing one period is common and often linked to stress or routine changes. Not having a "
               "period for 3 months (90 days) - when you are not pregnant - should be checked by a doctor. "
               "Missing several periods in a row, or having long gaps again and again, is worth discussing "
               "too. Tracking your dates in Let It Flow gives the doctor a clear history."},
    {"id": "irregular", "title": "What are irregular periods?", "tags": ["regularity", "cycle_length"],
     "examples": ["what are irregular periods", "why are my periods irregular", "irregular cycle causes",
                  "my periods are not regular", "irregular menstruation"],
     "answer": "Periods are often called irregular when cycle length changes a lot from month to month "
               "(more than about 7-9 days), when cycles are often shorter than 21-24 days or longer than "
               "35-38 days, or when periods are missed. Common reasons include stress, sleep changes, "
               "weight changes, intense exercise, skipping meals, illness and hormonal medicines. "
               "Sometimes a medical condition is involved - a doctor can check. Irregular does not "
               "automatically mean something is wrong."},
    {"id": "stress", "title": "Stress and periods", "tags": ["stress", "lifestyle"],
     "examples": ["does stress affect periods", "exam stress period late", "stress and menstrual cycle",
                  "can stress delay my period", "college stress periods"],
     "answer": "Stress can be associated with changes in periods. Stress hormones can influence the "
               "signals that control the cycle, so periods may come late, early or be skipped during very "
               "stressful times such as exams. This is common and often settles when things calm down. "
               "Sleep, regular meals, movement and talking to someone you trust can help. If periods stay "
               "disrupted for several months, see a doctor."},
    {"id": "sleep", "title": "Sleep and your cycle", "tags": ["sleep", "lifestyle"],
     "examples": ["does sleep affect periods", "poor sleep period irregular", "night shift sleep cycle",
                  "how much sleep should I get", "sleep and menstrual cycle"],
     "answer": "Regular, adequate sleep (most adults need 7-9 hours) supports healthy hormone balance. "
               "Irregular sleep and long late nights have been associated with cycle changes and with "
               "stronger PMS symptoms in some studies. This is an association, not proof of cause. A steady "
               "sleep time, even in hostel life, is a good goal."},
    {"id": "exercise", "title": "Exercise during your period", "tags": ["exercise"],
     "examples": ["can I exercise on my period", "workout during periods", "is yoga ok during periods",
                  "gym on period", "what exercise is best for my phase", "exercises suitable for my cycle phase"],
     "answer": "Exercise during your period is safe for most people and many feel better for it. "
               "Light options such as walking, stretching and yoga are popular on heavy or crampy days; "
               "you can return to your usual workouts when you feel up to it. Listen to your body - rest is "
               "fine too. Very intense training combined with too little food can disturb periods."},
    {"id": "diet_period", "title": "Eating during your period", "tags": ["diet"],
     "examples": ["what to eat during periods", "foods for menstrual phase", "diet for period",
                  "what foods help during periods", "indian food for periods", "what foods can I include"],
     "answer": "There is no special 'period diet', but some practical ideas: eat regular meals; include "
               "iron-containing foods such as dal, rajma, chole, sprouts, green leafy vegetables, ragi or "
               "eggs/chicken if you eat them, along with a vitamin C source (lemon, guava, orange) to help "
               "iron absorption; drink enough water; and keep simple comforting meals like khichdi handy. "
               "See the Nutrition & Exercise page for ideas based on your own diet preference."},
    {"id": "iron_fatigue", "title": "Tiredness and iron", "tags": ["fatigue", "diet"],
     "examples": ["why am I so tired during periods", "fatigue period", "low energy menstruation",
                  "iron deficiency periods", "anaemia", "feeling weak on my period"],
     "answer": "Feeling tired around your period is common: sleep can be disturbed, and bleeding loses "
               "some iron. Iron-containing foods with vitamin C, regular meals and good sleep help. If you "
               "feel very tired all the time, look pale, get breathless easily or have heavy periods, ask a "
               "doctor about a blood test for anaemia - do not start iron tablets without advice."},
    {"id": "skipping_meals", "title": "Skipping meals or strict dieting", "tags": ["diet", "lifestyle"],
     "examples": ["does skipping meals affect periods", "dieting and periods", "weight loss missed period",
                  "fasting and menstrual cycle", "not eating enough period stopped"],
     "answer": "Eating too little for long periods, crash dieting or very intense exercise can be associated "
               "with irregular or missed periods, because the body may reduce reproductive hormones when it "
               "is low on energy. Regular meals with enough calories and protein are important. If your "
               "periods have changed after dieting, please talk to a doctor."},
    {"id": "weight", "title": "Weight and periods", "tags": ["lifestyle"],
     "examples": ["does weight affect periods", "gaining weight irregular periods",
                  "losing weight period late", "bmi and menstrual cycle"],
     "answer": "Both low body weight and weight gain can be associated with changes in periods. Sudden "
               "changes in weight tend to matter more than a stable weight. If your cycles changed "
               "alongside a weight change, mention it to a doctor."},
    {"id": "bloating", "title": "Bloating around periods", "tags": ["bloating"],
     "examples": ["why do I feel bloated before my period", "period bloating", "water retention pms",
                  "how to reduce bloating period"],
     "answer": "Hormone changes before and during a period can cause the body to hold on to water and "
               "slow digestion, leading to bloating. Smaller regular meals, enough water, light movement "
               "and less very salty packaged food can help some people. Bloating that is severe or does "
               "not settle after your period is worth mentioning to a doctor."},
    {"id": "headache", "title": "Headaches and periods", "tags": ["headache"],
     "examples": ["headache before period", "menstrual migraine", "why do I get headaches on my period",
                  "period headache"],
     "answer": "Headaches around periods are common, partly because oestrogen levels fall just before "
               "bleeding starts. Staying hydrated, eating regularly and sleeping well can help. If "
               "headaches are severe, come with vision changes, or are new and different for you, "
               "see a doctor."},
    {"id": "acne", "title": "Acne around periods", "tags": ["acne"],
     "examples": ["why do I get pimples before my period", "period acne", "hormonal acne breakout",
                  "acne and menstrual cycle"],
     "answer": "Many people get pimples in the week before a period because hormone changes make skin "
               "oilier. Gentle face washing twice a day and not picking spots help. If acne is severe or "
               "comes with very irregular periods or excess hair growth, a doctor can check for other causes."},
    {"id": "pms", "title": "PMS (premenstrual symptoms)", "tags": ["pms", "mood"],
     "examples": ["what is pms", "mood swings before period", "premenstrual symptoms", "irritable before my period",
                  "mood changes menstrual cycle", "why am I emotional before period"],
     "answer": "PMS is a group of physical and emotional symptoms in the days before a period - mood changes, "
               "irritability, bloating, tender breasts, cravings, tiredness. It usually eases once bleeding "
               "starts. Regular sleep, movement, balanced meals and less caffeine can help. If mood symptoms "
               "are severe - such as intense sadness, hopelessness or anger that disrupts your life - please "
               "talk to a doctor or counsellor."},
    {"id": "spotting", "title": "Bleeding or spotting between periods", "tags": ["bleeding", "doctor"],
     "examples": ["spotting between periods", "bleeding in the middle of cycle", "brown discharge before period",
                  "light bleeding not on period"],
     "answer": "Light spotting can happen around mid-cycle or just before or after a period and is often "
               "harmless. Spotting that happens repeatedly, bleeding after intercourse, or bleeding that is "
               "heavy between periods should be checked by a doctor."},
    {"id": "conditions_info", "title": "Medical conditions that can affect periods (information only)",
     "tags": ["doctor"],
     "examples": ["do I have pcos", "is it pcos", "thyroid and periods", "endometriosis symptoms",
                  "can pcos cause irregular periods", "what medical conditions cause irregular periods"],
     "answer": "Several medical conditions can affect periods - for example thyroid problems, polycystic "
               "ovary syndrome (PCOS), endometriosis, and some medicines. I cannot tell whether you have any "
               "of these, and neither can an app: only a doctor can diagnose with an examination and tests. "
               "If you have repeated irregular or missed periods, severe pain, or heavy bleeding, "
               "download your report and discuss it with a doctor."},
    {"id": "prediction_how", "title": "How does Let It Flow predict my next period?", "tags": ["prediction"],
     "examples": ["how does the prediction work", "how are you predicting my period", "how accurate is the prediction",
                  "is the period prediction correct", "machine learning prediction", "why is my predicted date different"],
     "answer": "Let It Flow looks at the gaps between your logged period start dates. With 3 or more usable "
               "cycles it uses a regression model trained on a public research dataset (Kaggle FedCycle, "
               "mostly adults aged around 31) - in testing it was only slightly better than simply averaging "
               "your recent cycles, with an average error of roughly 2 days. With fewer cycles it uses your "
               "average. Predictions are estimates, not guaranteed dates, and they are less reliable when "
               "your cycles vary a lot. The model was NOT trained on Indian college students."},
    {"id": "tracking_tips", "title": "How to track your period well", "tags": ["tracking"],
     "examples": ["how do I track my period", "what should I log", "tips for tracking menstrual cycle",
                  "how many months of history do I need"],
     "answer": "Log the FIRST day of every period (that is what drives predictions and pattern analysis). "
               "Past dates help a lot: 3-6 months is ideal. Optional daily notes on pain, flow, mood, sleep "
               "and stress let the app show patterns over time. Skip anything you do not know - you can add "
               "or fix entries later."},
    {"id": "hygiene", "title": "Period hygiene basics", "tags": ["hygiene"],
     "examples": ["how often should I change my pad", "period hygiene", "pad vs tampon vs cup",
                  "hostel period hygiene", "rash from pads", "how to stay clean on period"],
     "answer": "Change pads every 4-6 hours (more often if heavy), and tampons at least every 4-8 hours - "
               "never leave a tampon in for longer than 8 hours. Wash hands before and after, wash the "
               "outer genital area with plain water, and avoid scented products. Pick whatever is "
               "comfortable and available to you. Fever, a strong foul smell, or severe itching deserve a "
               "doctor's visit."},
    {"id": "college_periods", "title": "Managing periods in college and hostel", "tags": ["college"],
     "examples": ["period in hostel", "managing periods during exams", "period pain in class",
                  "periods affect my attendance", "college period kit", "period during exam"],
     "answer": "Practical ideas: keep a small kit (pads, spare underwear, a pain-relief option your doctor "
               "approves, a small snack) in your bag; use a warm water bottle in the hostel; eat regularly "
               "even on busy exam days; and tell a trusted friend, warden or faculty member if you need to "
               "rest. If periods often make you miss classes, that is a good reason to see a doctor - many "
               "causes are treatable."},
    {"id": "hydration", "title": "Water and caffeine", "tags": ["diet"],
     "examples": ["how much water should I drink", "does caffeine affect periods", "tea coffee period cramps",
                  "hydration and menstruation"],
     "answer": "Drinking enough water (around 2-3 litres a day for many adults, more in hot weather) can "
               "help with bloating and headaches. Very large amounts of tea or coffee may make cramps, "
               "anxiety or sleep worse for some people; moderation is sensible."},
    {"id": "contraception_scope", "title": "Pregnancy, fertility and contraception", "tags": ["scope"],
     "examples": ["can I get pregnant on my period", "am I fertile today", "ovulation date to avoid pregnancy",
                  "use app as birth control", "safe days to avoid pregnancy", "fertile window"],
     "answer": "Let It Flow is not a contraception or fertility tool. Its estimates can be off by several "
               "days, so they must never be used to avoid or plan pregnancy. For contraception or pregnancy "
               "questions, please speak to a doctor or a family-planning clinic."},
    {"id": "see_doctor", "title": "When to see a healthcare professional", "tags": ["doctor"],
     "examples": ["when should I see a doctor about my period", "when to worry about periods",
                  "red flags periods", "should I see a gynecologist"],
     "answer": "Please see a doctor if you: have not had a period for 3 months (and are not pregnant); "
               "have periods more often than every 21 days or less often than every 45 days, again and "
               "again; bleed for more than 7 days or very heavily; have severe pain; bleed between periods "
               "or after sex; or feel your periods are affecting your studies and wellbeing. Take your "
               "Let It Flow report with you."},
    {"id": "privacy", "title": "Privacy of your data", "tags": ["privacy"],
     "examples": ["is my data safe", "who can see my period data", "delete my data", "privacy",
                  "can others see my chats"],
     "answer": "Your records are stored in the Let It Flow database and are only available to your own "
               "logged-in account. Passwords are stored hashed. You can edit or delete any entry, delete all "
               "your logs, or delete your whole account from Settings."},
    {"id": "first_period_teens", "title": "Cycles in the first years after periods begin", "tags": ["regularity"],
     "examples": ["periods are irregular since I started", "teenager irregular periods",
                  "irregular periods after menarche", "I am 18 and my periods vary"],
     "answer": "In the first few years after periods begin, cycles are often irregular as the body's hormone "
               "system matures. Cycles of 21-45 days can still be normal in this stage. Keep logging; if "
               "periods are very heavy, very painful, or you go 3 months without one, see a doctor."},
    {"id": "ovulation", "title": "What is ovulation?", "tags": ["phase"],
     "examples": ["what is ovulation", "ovulation symptoms", "when do I ovulate", "mid cycle pain",
                  "ovulatory phase"],
     "answer": "Ovulation is when an ovary releases an egg, usually around the middle of the cycle (roughly 14 "
               "days before the next period, though it varies a lot). Some people notice mild one-sided "
               "pain, clearer discharge or higher energy. Let It Flow does not detect ovulation, and the "
               "mid-cycle label in the app is only an approximation for education."},
    {"id": "luteal_pms_timing", "title": "The luteal phase and the days before a period", "tags": ["phase", "pms"],
     "examples": ["what is the luteal phase", "luteal phase symptoms", "why do I feel low before my period",
                  "premenstrual week"],
     "answer": "The luteal phase is the second half of the cycle, after ovulation and before bleeding. "
               "Progesterone rises then falls, which can bring PMS symptoms such as bloating, cravings, "
               "mood changes and tiredness. Regular meals, sleep, and gentle exercise help many people."},
    {"id": "vitamins", "title": "Supplements", "tags": ["diet"],
     "examples": ["should I take iron tablets", "vitamin supplements for periods", "do I need vitamin d",
                  "magnesium for cramps", "which supplements help periods"],
     "answer": "Food first: most students can meet their needs with balanced Indian meals. Supplements "
               "such as iron should be taken only after a doctor has checked whether you need them, because "
               "too much can be harmful. Ask a doctor or pharmacist before starting any supplement."},
]
