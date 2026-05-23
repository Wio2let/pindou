-- 给每个登录账号建一份云端库存
--
-- 跑一次。已存在会幂等跳过。

create table if not exists public.user_inventories (
  user_id    uuid primary key references auth.users(id) on delete cascade,
  counts     jsonb       not null default '{}'::jsonb,   -- { "A1": 950, "B2": 1500, ... }
  threshold  int         not null default 100,
  updated_at timestamptz not null default now()
);

alter table public.user_inventories enable row level security;

-- 只允许账号读写自己的那一行
drop policy if exists ui_self_select on public.user_inventories;
create policy ui_self_select on public.user_inventories
  for select using (auth.uid() = user_id);

drop policy if exists ui_self_insert on public.user_inventories;
create policy ui_self_insert on public.user_inventories
  for insert with check (auth.uid() = user_id);

drop policy if exists ui_self_update on public.user_inventories;
create policy ui_self_update on public.user_inventories
  for update using (auth.uid() = user_id) with check (auth.uid() = user_id);
