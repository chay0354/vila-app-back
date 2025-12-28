-- Create push_subscriptions table for storing Web Push and FCM subscriptions
create table if not exists push_subscriptions (
  id text primary key,
  username text not null,
  type text not null check (type in ('web', 'fcm')),
  endpoint text, -- For Web Push
  p256dh text, -- For Web Push
  auth text, -- For Web Push
  fcm_token text, -- For FCM
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- Create index for faster lookups
create index if not exists idx_push_subscriptions_username on push_subscriptions(username);
create index if not exists idx_push_subscriptions_endpoint on push_subscriptions(endpoint);
create index if not exists idx_push_subscriptions_fcm_token on push_subscriptions(fcm_token);

-- Enable RLS
alter table push_subscriptions enable row level security;

-- Allow anonymous read/write (will be secured by backend API)
create policy "anon all push_subscriptions" on push_subscriptions for all to anon using (true) with check (true);

