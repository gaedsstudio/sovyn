create table users (
  id uuid primary key default gen_random_uuid(),
  email text,
  created_at timestamptz not null default now()
);

create table assets (
  id text primary key,
  symbol text not null unique,
  name text not null,
  type text not null,
  asset_group text not null
);

create table observations (
  id bigserial primary key,
  asset_id text not null references assets(id),
  timestamp timestamptz not null,
  value double precision not null,
  source text not null
);

create table events (
  id text primary key,
  type text not null,
  asset_id text not null references assets(id),
  direction text not null,
  magnitude double precision not null,
  timestamp timestamptz not null,
  confidence double precision not null,
  summary text not null
);

create table event_asset_links (
  id uuid primary key default gen_random_uuid(),
  event_id text not null references events(id),
  asset_id text not null references assets(id),
  direction text not null,
  relevance double precision not null,
  rationale text not null
);

create table impact_rules (
  id uuid primary key default gen_random_uuid(),
  source text not null,
  target_group text not null,
  direction text not null,
  strength double precision not null,
  rationale text not null
);

create table signals (
  id text primary key,
  event_id text not null references events(id),
  signal_date date not null,
  impact_score jsonb not null
);

create table watchlists (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id),
  name text not null,
  created_at timestamptz not null default now()
);

create table watchlist_items (
  id uuid primary key default gen_random_uuid(),
  watchlist_id uuid not null references watchlists(id),
  asset_id text not null references assets(id),
  created_at timestamptz not null default now()
);

create table ai_explanations (
  id uuid primary key default gen_random_uuid(),
  signal_id text not null references signals(id),
  provider text not null,
  fact text not null,
  interpretation text not null,
  uncertainty text not null,
  created_at timestamptz not null default now()
);

create index observations_asset_timestamp_idx on observations(asset_id, timestamp desc);
create index events_timestamp_idx on events(timestamp desc);
create index signals_signal_date_idx on signals(signal_date desc);
create index watchlists_user_id_idx on watchlists(user_id);

