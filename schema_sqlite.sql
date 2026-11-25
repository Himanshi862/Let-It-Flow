-- Auto-generated SQLite twin of schema.sql (used when DB_BACKEND=sqlite)
-- Let It Flow - MySQL schema
-- Run once:  mysql -u root -p < schema.sql
-- (python app.py --init-db does the same thing for you)



CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  email TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,          -- hashed, never plain text
  age INTEGER NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_profiles (
  user_id INTEGER PRIMARY KEY,
  residence TEXT NULL,                   -- hostel / day_scholar
  typical_cycle_length INTEGER NULL,
  period_duration INTEGER NULL,
  self_regularity TEXT NULL,             -- regular / slightly_irregular / highly_irregular
  has_missed_periods INTEGER NULL,              -- 1 yes, 0 no, NULL not answered
  attendance_impact TEXT NULL,           -- never / sometimes / often
  sleep_routine TEXT NULL,               -- regular / irregular / night_owl
  onboarding_done INTEGER NOT NULL DEFAULT 0,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- One row per period START date (the core of the app)
CREATE TABLE IF NOT EXISTS menstrual_cycles (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  period_start DATE NOT NULL,
  period_end DATE NULL,
  notes TEXT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (user_id, period_start),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Daily bleeding / flow marks
CREATE TABLE IF NOT EXISTS period_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  log_date DATE NOT NULL,
  flow_intensity INTEGER NOT NULL,              -- 1 spotting .. 5 very heavy
  UNIQUE (user_id, log_date),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS symptom_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  log_date DATE NOT NULL,
  pain_severity INTEGER NULL,                   -- 0-10
  mood INTEGER NULL,                            -- 0 none .. 3 strong mood changes
  fatigue INTEGER NULL,
  bloating INTEGER NULL,
  acne INTEGER NULL,
  headache INTEGER NULL,
  notes TEXT NULL,
  UNIQUE (user_id, log_date),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS lifestyle_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  log_date DATE NOT NULL,
  sleep_hours REAL NULL,
  stress_level INTEGER NULL,                    -- 1-5
  exercise_minutes INTEGER NULL,
  exercise_type TEXT NULL,
  meals_skipped INTEGER NULL,
  water_litres REAL NULL,
  exam_period INTEGER NOT NULL DEFAULT 0,
  note TEXT NULL,
  UNIQUE (user_id, log_date),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS dietary_preferences (
  user_id INTEGER PRIMARY KEY,
  diet_type TEXT NULL,                   -- vegetarian / eggetarian / non_vegetarian / vegan
  dislikes TEXT NULL,
  skips_meals_often INTEGER NULL,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS exercise_preferences (
  user_id INTEGER PRIMARY KEY,
  preferred_exercise TEXT NULL,
  activity_level TEXT NULL,              -- sedentary / moderate / high
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS chatbot_conversations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  title TEXT NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS chatbot_messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  conversation_id INTEGER NOT NULL,
  user_id INTEGER NOT NULL,                         -- repeated on purpose: extra safety check
  role TEXT NOT NULL,                    -- user / bot
  content TEXT NOT NULL,
  intent TEXT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (conversation_id) REFERENCES chatbot_conversations(id) ON DELETE CASCADE,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Snapshot of the Irregular Cycle Intelligence result (history of how the pattern changes)
CREATE TABLE IF NOT EXISTS cycle_analysis (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  analysis_date DATE NOT NULL,
  status TEXT NOT NULL,
  n_cycles INTEGER NULL,
  mean_cycle REAL NULL,
  std_cycle REAL NULL,
  predicted_next DATE NULL,
  summary TEXT NULL,
  UNIQUE (user_id, analysis_date),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
