-- Enable UUIDs
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Optional: keep server clock for created_at/updated_at
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS trigger AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- =========================================
-- users (optional but useful)
-- =========================================
CREATE TABLE IF NOT EXISTS users (
  id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  email        TEXT UNIQUE,
  display_name TEXT,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_users_email ON users (email);

CREATE TRIGGER users_set_updated_at
BEFORE UPDATE ON users
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- =========================================
-- providers (Open-Meteo, OpenWeather, etc.)
-- =========================================
CREATE TABLE IF NOT EXISTS providers (
  id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name         TEXT NOT NULL UNIQUE,        -- e.g., 'open-weather', 'open-meteo'
  base_url     TEXT,
  notes        TEXT,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TRIGGER providers_set_updated_at
BEFORE UPDATE ON providers
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- =========================================
-- locations — canonicalized places
-- Allow many inputs (zip/city/landmark), but one canonical record
-- =========================================
CREATE TABLE IF NOT EXISTS locations (
  id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  canonical_name TEXT NOT NULL,             -- e.g., "Seattle, WA, US"
  latitude       NUMERIC(8,5) NOT NULL,     -- ±90.00000
  longitude      NUMERIC(8,5) NOT NULL,     -- ±180.00000
  country_code   VARCHAR(2),
  admin1         TEXT,                      -- state/province
  admin2         TEXT,                      -- county/district
  postal_code    TEXT,                      -- if applicable
  landmark       TEXT,                      -- optional (Space Needle)
  tz_name        TEXT,                      -- Olson TZ (e.g., America/Los_Angeles)
  created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (latitude, longitude),
  UNIQUE (canonical_name, country_code, admin1, admin2, postal_code)
);
CREATE INDEX IF NOT EXISTS idx_locations_canon ON locations USING btree (canonical_name);
CREATE INDEX IF NOT EXISTS idx_locations_geo ON locations (latitude, longitude);

CREATE TRIGGER locations_set_updated_at
BEFORE UPDATE ON locations
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- =========================================
-- requests — every user query (location + date range)
-- Max results window: 7 days (inclusive)
-- =========================================
CREATE TYPE request_status AS ENUM ('pending','ok','error');

CREATE TABLE IF NOT EXISTS requests (
  id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id        UUID REFERENCES users(id) ON DELETE SET NULL,
  location_id    UUID NOT NULL REFERENCES locations(id) ON DELETE CASCADE,
  provider_id    UUID REFERENCES providers(id) ON DELETE SET NULL, -- provider chosen/resolved
  query_raw      TEXT,                       -- user input before canonicalization
  start_date     DATE NOT NULL,
  end_date       DATE NOT NULL,
  granularity    TEXT NOT NULL CHECK (granularity IN ('current','hourly','daily')),
  status         request_status NOT NULL DEFAULT 'pending',
  error_message  TEXT,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  -- Enforce max 7 days inclusive
  CONSTRAINT requests_max_7_days CHECK (end_date <= start_date + INTERVAL '7 days')
);
CREATE INDEX IF NOT EXISTS idx_requests_loc_dates ON requests (location_id, start_date, end_date);
CREATE INDEX IF NOT EXISTS idx_requests_user ON requests (user_id);
CREATE INDEX IF NOT EXISTS idx_requests_status ON requests (status);

CREATE TRIGGER requests_set_updated_at
BEFORE UPDATE ON requests
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- =========================================
-- weather_observations — point-in-time actuals (past/current)
-- =========================================
CREATE TABLE IF NOT EXISTS weather_observations (
  id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  location_id    UUID NOT NULL REFERENCES locations(id) ON DELETE CASCADE,
  provider_id    UUID NOT NULL REFERENCES providers(id) ON DELETE CASCADE,
  observed_at    TIMESTAMPTZ NOT NULL,          -- the time this weather is valid for
  temperature_c  NUMERIC(6,2),
  humidity_pct   NUMERIC(5,2),
  pressure_hpa   NUMERIC(7,2),
  wind_speed_ms  NUMERIC(6,2),
  wind_gust_ms   NUMERIC(6,2),
  wind_deg       NUMERIC(5,1),
  precip_mm      NUMERIC(7,2),
  snow_mm        NUMERIC(7,2),
  cloud_pct      NUMERIC(5,2),
  visibility_m   NUMERIC(9,2),
  uv_index       NUMERIC(4,2),
  weather_code   TEXT,                          -- provider-specific symbol ID
  payload_raw    JSONB,                          -- full provider blob for auditing
  ingested_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (location_id, provider_id, observed_at)
);
CREATE INDEX IF NOT EXISTS idx_obs_loc_time ON weather_observations (location_id, observed_at DESC);
CREATE INDEX IF NOT EXISTS idx_obs_provider_time ON weather_observations (provider_id, observed_at DESC);
CREATE INDEX IF NOT EXISTS idx_obs_payload_gin ON weather_observations USING GIN (payload_raw);

-- =========================================
-- weather_forecasts — snapshot of predictions
-- snapshot_time: when you fetched it
-- forecast_time: time the forecast is for (target time)
-- horizon_hours: forecast lead time
-- =========================================
CREATE TYPE forecast_kind AS ENUM ('hourly','daily');

CREATE TABLE IF NOT EXISTS weather_forecasts (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  location_id     UUID NOT NULL REFERENCES locations(id) ON DELETE CASCADE,
  provider_id     UUID NOT NULL REFERENCES providers(id) ON DELETE CASCADE,
  kind            forecast_kind NOT NULL,       -- 'hourly' or 'daily'
  snapshot_time   TIMESTAMPTZ NOT NULL,         -- when we retrieved the forecast
  forecast_time   TIMESTAMPTZ NOT NULL,         -- the target time the forecast refers to
  horizon_hours   INT GENERATED ALWAYS AS (GREATEST(0, EXTRACT(EPOCH FROM (forecast_time - snapshot_time))::INT / 3600)) STORED,
  temperature_c   NUMERIC(6,2),
  temp_min_c      NUMERIC(6,2),
  temp_max_c      NUMERIC(6,2),
  humidity_pct    NUMERIC(5,2),
  pressure_hpa    NUMERIC(7,2),
  wind_speed_ms   NUMERIC(6,2),
  wind_gust_ms    NUMERIC(6,2),
  wind_deg        NUMERIC(5,1),
  precip_mm       NUMERIC(7,2),
  snow_mm         NUMERIC(7,2),
  cloud_pct       NUMERIC(5,2),
  pop_pct         NUMERIC(5,2),                 -- probability of precipitation (0-100)
  weather_code    TEXT,
  payload_raw     JSONB,
  ingested_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  -- Forecasts should be for now or future (allow near-past from provider quirks up to 1h)
  CONSTRAINT forecast_not_far_past CHECK (forecast_time >= snapshot_time - INTERVAL '1 hour'),
  UNIQUE (location_id, provider_id, kind, snapshot_time, forecast_time)
);
CREATE INDEX IF NOT EXISTS idx_fc_loc_time ON weather_forecasts (location_id, forecast_time);
CREATE INDEX IF NOT EXISTS idx_fc_loc_kind_snap ON weather_forecasts (location_id, kind, snapshot_time);
CREATE INDEX IF NOT EXISTS idx_fc_payload_gin ON weather_forecasts USING GIN (payload_raw);

-- =========================================
-- favorites (optional)
-- =========================================
CREATE TABLE IF NOT EXISTS favorites (
  user_id      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  location_id  UUID NOT NULL REFERENCES locations(id) ON DELETE CASCADE,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (user_id, location_id)
);

-- =========================================
-- audit_logs (optional) — track CRUD events
-- =========================================
CREATE TYPE audit_action AS ENUM ('create','read','update','delete','ingest');

CREATE TABLE IF NOT EXISTS audit_logs (
  id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id      UUID REFERENCES users(id) ON DELETE SET NULL,
  entity_table TEXT NOT NULL,           -- e.g., 'requests','locations','weather_observations'
  entity_id    UUID,                    -- UUID of the row in that table (nullable for bulk ops)
  action       audit_action NOT NULL,
  changed_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  details      JSONB                    -- free-form (diffs, request params, etc.)
);
CREATE INDEX IF NOT EXISTS idx_audit_table_time ON audit_logs (entity_table, changed_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_user_time ON audit_logs (user_id, changed_at DESC);

-- =========================================
-- Helpful views
-- =========================================
CREATE OR REPLACE VIEW v_recent_requests AS
SELECT r.*, u.email, l.canonical_name
FROM requests r
LEFT JOIN users u ON u.id = r.user_id
JOIN locations l ON l.id = r.location_id
ORDER BY r.created_at DESC;

-- =========================================
-- Optional retention (example): keep raw provider blobs 90 days
-- (You’d wire this via a cron job or pg\_cron extension)
-- =========================================
-- DELETE FROM weather_observations WHERE ingested_at < NOW() - INTERVAL '90 days';
-- DELETE FROM weather_forecasts   WHERE ingested_at < NOW() - INTERVAL '90 days';
