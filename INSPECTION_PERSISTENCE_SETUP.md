# Inspection Task Persistence Setup

This document explains how to set up database persistence for inspection task completion status.

## SQL Migration Command

Run this SQL command in your Supabase SQL Editor to add the necessary database structure:

```sql
-- Migration: Add order_id to inspections table and ensure proper structure for task persistence
-- This allows linking inspections to orders and persisting task completion status

-- Add order_id column if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'inspections' AND column_name = 'order_id'
    ) THEN
        ALTER TABLE inspections ADD COLUMN order_id text;
    END IF;
END $$;

-- Ensure inspection_tasks table has the correct structure
-- (It should already exist based on README, but we'll ensure it's correct)
CREATE TABLE IF NOT EXISTS inspection_tasks (
    id text primary key,
    inspection_id text references inspections(id) on delete cascade,
    name text not null,
    completed boolean not null default false
);

-- Add write permissions for inspections and inspection_tasks
-- (Read permissions should already exist)
DROP POLICY IF EXISTS "anon insert inspections" ON inspections;
CREATE POLICY "anon insert inspections" ON inspections FOR INSERT TO anon WITH CHECK (true);

DROP POLICY IF EXISTS "anon update inspections" ON inspections;
CREATE POLICY "anon update inspections" ON inspections FOR UPDATE TO anon USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "anon insert inspection_tasks" ON inspection_tasks;
CREATE POLICY "anon insert inspection_tasks" ON inspection_tasks FOR INSERT TO anon WITH CHECK (true);

DROP POLICY IF EXISTS "anon update inspection_tasks" ON inspection_tasks;
CREATE POLICY "anon update inspection_tasks" ON inspection_tasks FOR UPDATE TO anon USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "anon delete inspection_tasks" ON inspection_tasks;
CREATE POLICY "anon delete inspection_tasks" ON inspection_tasks FOR DELETE TO anon USING (true);
```

## What This Does

1. **Adds `order_id` column** to `inspections` table to link inspections to orders
2. **Ensures `inspection_tasks` table exists** with proper structure
3. **Adds write permissions** so the app can create/update inspections and tasks

## Backend Changes

The backend now includes:
- `GET /api/inspections` - Returns all inspections with their tasks
- `POST /api/inspections` - Creates or updates an inspection with all its tasks
- `PATCH /api/inspections/{inspection_id}/tasks/{task_id}` - Updates a single task (e.g., toggle completion)

## Frontend Changes

Both PWA and Native app now:
- Load inspections from backend on startup
- Save task completion status to backend when tasks are toggled
- Persist all task states across sessions

## How It Works

1. When you mark a task as completed, it's immediately saved to the database
2. When you reload the app, it loads inspections from the database with their saved completion status
3. Task completion persists across all devices and sessions




