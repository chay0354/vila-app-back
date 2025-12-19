-- Create chat_messages table if it doesn't exist
-- Run this in Supabase SQL Editor

create table if not exists chat_messages (
  id bigint generated always as identity primary key,
  sender text,
  content text not null,
  created_at timestamptz default now()
);

-- Enable RLS (Row Level Security)
alter table chat_messages enable row level security;

-- Allow anonymous read access
create policy "anon read chat_messages" on chat_messages for select to anon using (true);

-- Allow anonymous insert access
create policy "anon insert chat_messages" on chat_messages for insert to anon with check (true);

