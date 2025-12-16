# Backend (Python + FastAPI + Supabase)

## Setup
```bash
cd back
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Create `.env` in `back/`:
```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
PORT=4000
```

Run dev server:
```bash
uvicorn app.main:app --reload --port 4000
```

## Endpoints
- `GET /health`
- `GET /orders`
- `GET /inspections` (joins `inspection_tasks`)
- `GET /inventory/items`
- `GET /inventory/orders`
- `GET /maintenance/tasks`
- `GET /reports/summary` (totals from orders + expenses)
- `GET /invoices`
- `GET /chat/messages` (latest 50)
- `GET /attendance/logs` (latest 50)

## Supabase tables (SQL)
Run in Supabase SQL Editor:
```sql
-- Users (Authentication)
create table if not exists users (
  id text primary key,
  username text not null unique,
  password_hash text not null,
  created_at timestamptz default now()
);
alter table users enable row level security;
create policy "anon read users" on users for select to anon using (true);
create policy "anon insert users" on users for insert to anon with check (true);

-- Orders
create table if not exists orders (
  id text primary key,
  guest_name text not null,
  unit_number text not null,
  arrival_date date not null,
  departure_date date not null,
  status text not null,
  guests_count int not null,
  special_requests text,
  internal_notes text,
  paid_amount numeric not null default 0,
  total_amount numeric not null default 0,
  payment_method text
);
alter table orders enable row level security;
create policy "anon read orders" on orders for select to anon using (true);

-- Inspections
create table if not exists inspections (
  id text primary key,
  unit_number text not null,
  guest_name text not null,
  departure_date date not null,
  status text not null
);
create table if not exists inspection_tasks (
  id text primary key,
  inspection_id text references inspections(id) on delete cascade,
  name text not null,
  completed boolean not null default false
);
alter table inspections enable row level security;
alter table inspection_tasks enable row level security;
create policy "anon read inspections" on inspections for select to anon using (true);
create policy "anon read inspection_tasks" on inspection_tasks for select to anon using (true);

-- Inventory
create table if not exists inventory_items (
  id text primary key,
  name text not null,
  category text not null,
  unit text not null,
  current_stock int not null,
  min_stock int not null
);
create table if not exists inventory_orders (
  id text primary key,
  item_id text references inventory_items(id),
  item_name text not null,
  quantity int not null,
  unit text not null,
  order_date date not null,
  delivery_date date,
  status text not null,
  order_type text not null,
  ordered_by text,
  unit_number text
);
alter table inventory_items enable row level security;
alter table inventory_orders enable row level security;
create policy "anon read inventory_items" on inventory_items for select to anon using (true);
create policy "anon read inventory_orders" on inventory_orders for select to anon using (true);

-- Maintenance
create table if not exists maintenance_tasks (
  id text primary key,
  unit_id text not null,
  title text not null,
  description text,
  status text not null,
  priority text not null,
  created_date date not null,
  assigned_to text,
  image_uri text,
  category text
);
alter table maintenance_tasks enable row level security;
create policy "anon read maintenance_tasks" on maintenance_tasks for select to anon using (true);

-- Expenses (for reports)
create table if not exists expenses (
  id bigint generated always as identity primary key,
  amount numeric not null,
  category text,
  description text,
  paid_at date default now()
);
alter table expenses enable row level security;
create policy "anon read expenses" on expenses for select to anon using (true);

-- Invoices
create table if not exists invoices (
  id bigint generated always as identity primary key,
  vendor text,
  invoice_number text,
  amount numeric,
  payment_method text,
  issued_at date,
  file_url text
);
alter table invoices enable row level security;
create policy "anon read invoices" on invoices for select to anon using (true);

-- Chat messages
create table if not exists chat_messages (
  id bigint generated always as identity primary key,
  sender text,
  content text not null,
  created_at timestamptz default now()
);
alter table chat_messages enable row level security;
create policy "anon read chat_messages" on chat_messages for select to anon using (true);

-- Attendance / time clock
create table if not exists attendance_logs (
  id bigint generated always as identity primary key,
  employee text,
  clock_in timestamptz not null default now(),
  clock_out timestamptz,
  hourly_rate numeric
);
alter table attendance_logs enable row level security;
create policy "anon read attendance_logs" on attendance_logs for select to anon using (true);
```


