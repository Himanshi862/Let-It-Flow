# Let It Flow — menstrual health intelligence for college students

Flask + MySQL web app with a machine-learning period estimate, rule-based **Irregular Cycle Intelligence**,
student lifestyle insights, Indian-food/exercise suggestions, a local NLP health chatbot and a ReportLab PDF report.

---------------------------------------------------------------------------------------------------

## 1. How to run (Windows / macOS / Linux)

You need **Python 3.10+** and **MySQL 8** (or MariaDB). Open a terminal inside the `let-it-flow` folder.

### Step 1 – virtual environment + packages
```bash
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux
pip install -r requirements.txt
```

### Step 2 – tell the app your MySQL password
Copy `.env.example` to a new file called `.env` and edit it:
```
DB_BACKEND=mysql
MYSQL_HOST=localhost
MYSQL_USER=root
MYSQL_PASSWORD=your_mysql_password_here
MYSQL_DATABASE=let_it_flow
```
(The password lives only in `.env`, never in the code.)

### Step 3 – start the app (it creates the database and tables automatically)
```bash
python app.py
```
Open **http://127.0.0.1:5000** → *Create account* → follow the 3 skippable onboarding steps.

Prefer to create tables yourself?  `mysql -u root -p < schema.sql`  (same result).

### No MySQL installed? Quick try-out mode
Set `DB_BACKEND=sqlite` in `.env` (or run `set DB_BACKEND=sqlite` first). Everything works with a local file
database. Use MySQL for your project submission.

### Step 4 (optional) – retrain the model
The trained models are already in `models/`. To retrain from the datasets in `datasets/`:
```bash
python prediction/train_model.py
```
This re-creates `models/*.joblib`, `models/metrics.json` and `models/primary_summary.json`.

### Step 5 (optional) – run the automatic tests
```bash
python tests/smoke_test.py
```
42 checks: registration, every page, CRUD, chatbot, PDF, and **account isolation** (user B cannot touch user A's data).

> Internet note: Chart.js (charts) and Google Fonts load from a CDN. Offline, the app still works — charts show a short
> message and the tables remain, fonts fall back to Georgia / system fonts.

---------------------------------------------------------------------------------------------------

## 2. What is in the project

```
let-it-flow/
├── app.py                  Flask routes, login, CSRF, security headers
├── config.py               settings read from .env
├── database.py             MySQL/SQLite connection + safe query helpers (parameterised)
├── repository.py           every SQL query (all filtered by user_id)
├── snapshot.py             gathers one user's data + prediction + analysis (shared by pages, chatbot, PDF)
├── schema.sql              MySQL tables   (schema_sqlite.sql = same for SQLite)
├── prediction/
│   ├── features.py             feature builder shared by training AND prediction
│   ├── train_model.py          Stage 5: cleaning, participant-level split, baselines, evaluation, Joblib
│   ├── cycle_prediction.py     loads the model, gives estimate + range + confidence
│   └── irregularity_analysis.py  Stage 6: age-aware rules, never diagnoses
├── insights/
│   ├── lifestyle.py            associations (sleep, stress, exams, exercise, skipped meals)
│   └── recommendations.py      diet + exercise ideas (affordable Indian foods)
├── chatbot/
│   ├── knowledge_base.py       ~35 menstrual-health topics
│   ├── user_context.py         recorded facts for the logged-in user only
│   └── chatbot.py              NLP: safety → intents → TF-IDF retrieval → personal "From your logs" line
├── reports/generate_report.py  ReportLab doctor-ready PDF
├── templates/  static/         the redesigned UI (HTML, one CSS file, tiny JS)
├── datasets/                   your two datasets + Stage-1 data-quality report
├── models/                     trained .joblib models + metrics.json + primary_summary.json
└── tests/smoke_test.py
```

## 3. Features → where they live

| Feature | Page (route) | Backend |
|---|---|---|
| Register / login, hashed passwords | `/register` `/login` | `app.py` (Werkzeug hashes) |
| Gradual onboarding (all skippable, "why we ask") | `/onboarding` | `app.py`, `user_profiles`, preference tables |
| Dashboard with cycle ring, estimate, check-in | `/dashboard` | `snapshot.py` |
| Cycle tracker: calendar, add/edit/delete periods | `/tracker` | `menstrual_cycles` |
| Daily log: flow, pain, mood, sleep, stress, exercise, skipped meals, exam day | `/log` | `period_logs`, `symptom_logs`, `lifestyle_logs` |
| ML prediction page with honest test results | `/prediction` | `prediction/` |
| Irregular Cycle Intelligence | `/intelligence` | `irregularity_analysis.py`, `cycle_analysis` |
| Student lifestyle insights | `/insights` | `insights/lifestyle.py` |
| Nutrition & exercise | `/nutrition` | `insights/recommendations.py` |
| Health chatbot (per-user history) | `/assistant` | `chatbot/`, `chatbot_conversations`, `chatbot_messages` |
| Education | `/learn` | static content + references |
| Doctor-ready PDF + CSV export | `/reports` | `reports/generate_report.py` |
| Profile, settings, delete logs / account | `/profile` `/settings` | `repository.py` |

## 4. The ML model — what was actually found (real numbers)

* **Training data:** Kaggle/FedCycle only. After cleaning: 1,645 cycles from 159 participants
  (12 exact duplicate rows and 8 conflicting rows removed; nothing invented).
* **Task:** predict the next cycle length from the previous 2–3 cycle lengths (+ their mean and spread).
* **Leakage control:** split **by participant** (GroupKFold for model choice, 20% of participants held out for the final test).
  Columns that describe the cycle being predicted (ovulation day, luteal length…) are not used.
* **Held-out test (26 participants, model needing 3 past cycles):**

| Method | MAE (days) | RMSE |
|---|---|---|
| Ridge regression (the saved model) | **1.79** | 2.50 |
| Average of recent cycles (baseline) | 1.82 | 2.55 |
| Repeat last cycle (baseline) | 2.45 | 3.39 |
| One number for everyone (baseline) | 2.52 | 3.33 |

**Honest reading:** the model is only about 2% better than simply averaging recent cycles. With only 2 past cycles it was
*not* better than the average, so the app uses the plain average there and says so. The ±3.4-day range covers about 86% of
held-out cycles.
* **Primary survey sanity check:** only 4 students had enough usable dates; the model was *not* better than the baselines on them
  (MAE 3.5 vs 2.75 for "repeat last cycle"). That is far too few to conclude anything — it is shown to be transparent.
* **Population caveat:** trained on adults (median age ≈ 31) who tracked for fertility awareness — **not** Indian college students.
  The app never claims otherwise. The primary survey is used only to describe the student sample (Insights page).
* Predictions are estimates, not guaranteed dates, and not for contraception or fertility planning.

## 5. NLP chatbot (no API key needed)
1. Safety: urgent bleeding/pain words and self-harm words get a safety message first.
2. Diagnosis guard: "Do I have PCOS?" → it explains it cannot diagnose.
3. Personal intents ("When is my next period?", "What was my last period?", "Is my cycle regular?") are answered **only from your own rows**;
   if data is missing it says so.
4. Everything else: question text is cleaned (synonyms, light stemming) and matched to the knowledge base with **TF-IDF + cosine similarity** (scikit-learn).
5. Matching topics get a short **"From your logs"** line; general text is labelled general information.
6. Weak matches → an honest "I'm not sure".
Conversations are stored per user; a user can't open or continue another user's chat. `chatbot.py → reply_with_llm()` shows where an
external AI API could be added later (key via environment variable); the project does not need one.

## 6. Security checklist
* Password hashing (Werkzeug), min 8 chars with letters + numbers; same error message for wrong email/password; login throttling.
* `login_required` on all private pages; user id only from the signed session cookie (HttpOnly, SameSite=Lax).
* Every SQL statement is parameterised and filtered by `user_id`; edit/delete of another user's record returns 404.
* CSRF token on every POST (including the chat API); security headers + Content-Security-Policy; private pages are not cached.
* Edit/delete of every record type; "Delete my logs" and "Delete account" need the password.

## 7. Changes from the original UI prototype
* New visual identity: orchid/rose/peach/sage palette (your lavender kept), Fraunces + Plus Jakarta Sans, the four-colour **bloom ring** for cycle phases, soft tinted cards, mobile bottom navigation.
* Removed fake numbers from the mock-up (e.g. "±1 day high confidence", invented lifestyle effects). All numbers now come from your data or from real test results.
* Removed "fertile window" wording: the project must not give fertility advice. The mid-cycle phase is labelled as an educational approximation.
* Pages added to match the spec: onboarding, daily log, prediction, intelligence, student insights, report, profile and settings.

## 8. Limits to mention in your viva
* The MySQL path uses PyMySQL and standard SQL, but automated tests here ran on SQLite — please run `python app.py` against your MySQL once and tell me if anything errors.
* Cycle phases are day-count estimates; irregularity rules are simplified from ACOG/FIGO ranges (they are education, not diagnosis).
* The primary survey (33 students) is far too small for statistical claims; insights from it are descriptive only.
* Please check the reference list on the Learn page against the original sources before submission.
