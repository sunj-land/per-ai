CREATE TABLE IF NOT EXISTS skill_store (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  version TEXT NOT NULL DEFAULT '0.1.0',
  description TEXT,
  author TEXT,
  tags TEXT,
  source_type TEXT NOT NULL DEFAULT 'local',
  source_url TEXT,
  install_url TEXT,
  file_path TEXT,
  install_dir TEXT,
  status TEXT NOT NULL DEFAULT 'active',
  install_status TEXT NOT NULL DEFAULT 'installed',
  dependency_snapshot TEXT,
  idempotency_key TEXT,
  last_install_at DATETIME,
  last_error TEXT,
  is_deleted BOOLEAN NOT NULL DEFAULT 0,
  input_schema TEXT,
  output_schema TEXT,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_skill_store_name ON skill_store(name);
CREATE INDEX IF NOT EXISTS idx_skill_store_version ON skill_store(version);
CREATE INDEX IF NOT EXISTS idx_skill_store_idempotency_key ON skill_store(idempotency_key);

CREATE TABLE IF NOT EXISTS skill_install_record (
  id TEXT PRIMARY KEY,
  task_id TEXT NOT NULL,
  skill_name TEXT NOT NULL,
  target_version TEXT NOT NULL DEFAULT 'latest',
  operation TEXT NOT NULL DEFAULT 'install',
  status TEXT NOT NULL DEFAULT 'pending',
  operator TEXT,
  idempotency_key TEXT,
  result_message TEXT,
  log_summary TEXT,
  started_at DATETIME NOT NULL,
  finished_at DATETIME,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_skill_install_record_task_id ON skill_install_record(task_id);
CREATE INDEX IF NOT EXISTS idx_skill_install_record_skill_name ON skill_install_record(skill_name);
CREATE INDEX IF NOT EXISTS idx_skill_install_record_idempotency_key ON skill_install_record(idempotency_key);

CREATE TABLE IF NOT EXISTS skill_dependency (
  id TEXT PRIMARY KEY,
  skill_name TEXT NOT NULL,
  skill_version TEXT NOT NULL DEFAULT '0.1.0',
  dependency_name TEXT NOT NULL,
  required_version TEXT NOT NULL DEFAULT '*',
  resolved_version TEXT,
  source TEXT NOT NULL DEFAULT 'registry',
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_skill_dependency_skill_name ON skill_dependency(skill_name);
CREATE INDEX IF NOT EXISTS idx_skill_dependency_dependency_name ON skill_dependency(dependency_name);
