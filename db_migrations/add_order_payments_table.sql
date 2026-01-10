-- Create order_payments table to track payment history
create table if not exists order_payments (
  id bigint generated always as identity primary key,
  order_id text not null references orders(id) on delete cascade,
  amount numeric not null,
  payment_method text not null,
  paid_at timestamptz default now(),
  created_at timestamptz default now()
);

-- Enable RLS
alter table order_payments enable row level security;

-- Allow anonymous read access
create policy "anon read order_payments" on order_payments for select to anon using (true);

-- Allow anonymous insert access
create policy "anon insert order_payments" on order_payments for insert to anon with check (true);

-- Allow anonymous update access
create policy "anon update order_payments" on order_payments for update to anon using (true);

-- Allow anonymous delete access
create policy "anon delete order_payments" on order_payments for delete to anon using (true);

-- Create index for faster queries
create index if not exists idx_order_payments_order_id on order_payments(order_id);
create index if not exists idx_order_payments_paid_at on order_payments(paid_at desc);

