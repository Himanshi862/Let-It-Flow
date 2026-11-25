-- Let It Flow - MySQL schema
-- Run once:  mysql -u root -p < schema.sql
-- (python app.py --init-db does the same thing for you)

CREATE DATABASE IF NOT EXISTS let_it_flow CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE let_it_flow;

CREATE TABLE IF NOT EXISTS users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  email VARCHAR(190) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,          -- hashed, never plain text
  age TINYINT UNSIGNED NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS user_profiles (
  user_id INT PRIMARY KEY,
  residence VARCHAR(20) NULL,                   -- hostel / day_scholar
  typical_cycle_length SMALLINT NULL,
  period_duration TINYINT NULL,
  self_regularity VARCHAR(30) NULL,             -- regular / slightly_irregular / highly_irregular
  has_missed_periods TINYINT NULL,              -- 1 yes, 0 no, NULL not answered
  attendance_impact VARCHAR(20) NULL,           -- never / sometimes / often
  sleep_routine VARCHAR(20) NULL,               -- regular / irregular / night_owl
  onboarding_done TINYINT NOT NULL DEFAULT 0,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- One row per period START date (the core of the app)
CREATE TABLE IF NOT EXISTS menstrual_cycles (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  period_start DATE NOT NULL,
  period_end DATE NULL,
  notes VARCHAR(255) NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_user_start (user_id, period_start),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Daily bleeding / flow marks
CREATE TABLE IF NOT EXISTS period_logs (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  log_date DATE NOT NULL,
  flow_intensity TINYINT NOT NULL,              -- 1 spotting .. 5 very heavy
  UNIQUE KEY uq_user_flowdate (user_id, log_date),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS symptom_logs (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  log_date DATE NOT NULL,
  pain_severity TINYINT NULL,                   -- 0-10
  mood TINYINT NULL,                            -- 0 none .. 3 strong mood changes
  fatigue TINYINT NULL,
  bloating TINYINT NULL,
  acne TINYINT NULL,
  headache TINYINT NULL,
  notes VARCHAR(255) NULL,
  UNIQUE KEY uq_user_symdate (user_id, log_date),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS lifestyle_logs (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  log_date DATE NOT NULL,
  sleep_hours DECIMAL(3,1) NULL,
  stress_level TINYINT NULL,                    -- 1-5
  exercise_minutes SMALLINT NULL,
  exercise_type VARCHAR(60) NULL,
  meals_skipped TINYINT NULL,
  water_litres DECIMAL(3,1) NULL,
  exam_period TINYINT NOT NULL DEFAULT 0,
  note VARCHAR(255) NULL,
  UNIQUE KEY uq_user_lifedate (user_id, log_date),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS dietary_preferences (
  user_id INT PRIMARY KEY,
  diet_type VARCHAR(20) NULL,                   -- vegetarian / eggetarian / non_vegetarian / vegan
  dislikes VARCHAR(255) NULL,
  skips_meals_often TINYINT NULL,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS exercise_preferences (
  user_id INT PRIMARY KEY,
  preferred_exercise VARCHAR(40) NULL,
  activity_level VARCHAR(20) NULL,              -- sedentary / moderate / high
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS chatbot_conversations (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  title VARCHAR(120) NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS chatbot_messages (
  id INT AUTO_INCREMENT PRIMARY KEY,
  conversation_id INT NOT NULL,
  user_id INT NOT NULL,                         -- repeated on purpose: extra safety check
  role VARCHAR(10) NOT NULL,                    -- user / bot
  content TEXT NOT NULL,
  intent VARCHAR(60) NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (conversation_id) REFERENCES chatbot_conversations(id) ON DELETE CASCADE,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Snapshot of the Irregular Cycle Intelligence result (history of how the pattern changes)
CREATE TABLE IF NOT EXISTS cycle_analysis (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  analysis_date DATE NOT NULL,
  status VARCHAR(30) NOT NULL,
  n_cycles SMALLINT NULL,
  mean_cycle DECIMAL(4,1) NULL,
  std_cycle DECIMAL(4,1) NULL,
  predicted_next DATE NULL,
  summary TEXT NULL,
  UNIQUE KEY uq_user_analysisdate (user_id, analysis_date),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;
