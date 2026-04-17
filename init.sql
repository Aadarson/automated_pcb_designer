-- initialization script
CREATE TABLE users (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email       TEXT UNIQUE NOT NULL,
  hashed_pw   TEXT NOT NULL,
  created_at  TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE design_jobs (
  job_id          UUID PRIMARY KEY,
  user_id         UUID REFERENCES users(id),
  project_name    TEXT NOT NULL,
  spec            JSONB NOT NULL,
  status          TEXT NOT NULL DEFAULT 'queued',
  result          JSONB,
  errors          TEXT[],
  created_at      TIMESTAMPTZ DEFAULT now(),
  updated_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_jobs_user ON design_jobs(user_id);
CREATE INDEX idx_jobs_status ON design_jobs(status);
