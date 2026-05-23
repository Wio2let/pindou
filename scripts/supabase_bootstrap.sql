-- Bead Studio · 共享画廊后端建表脚本
--
-- 用法：登录 Supabase 控制台 → SQL Editor → 新建查询 → 把整段贴进去 → Run。
-- 跑完后会得到：
--   • gallery_works 表（存元数据）
--   • gallery-thumbs Storage bucket（存 JPEG 图片本体）
--   • 匿名（anon）用户可以 SELECT + INSERT，但不能 UPDATE / DELETE 别人的作品

-- 1. 元数据表 ---------------------------------------------------------------
create table if not exists public.gallery_works (
  id              uuid primary key default gen_random_uuid(),
  created_at      timestamptz not null default now(),
  title           text not null check (char_length(title) <= 60),
  width           int  not null check (width  between 1 and 1000),
  height          int  not null check (height between 1 and 1000),
  total_beads     int  not null check (total_beads >= 0),
  unique_colors   int  not null check (unique_colors >= 0),
  bead_shape      text not null check (bead_shape in ('circle','square','fill')),
  thumb_path      text not null      -- 对应 storage 里的 object path
);

create index if not exists gallery_works_created_idx
  on public.gallery_works (created_at desc);

-- 允许匿名读 + 写
alter table public.gallery_works enable row level security;

drop policy if exists gallery_anon_select on public.gallery_works;
create policy gallery_anon_select on public.gallery_works
  for select using (true);

drop policy if exists gallery_anon_insert on public.gallery_works;
create policy gallery_anon_insert on public.gallery_works
  for insert with check (true);

-- 2. Storage bucket ---------------------------------------------------------
insert into storage.buckets (id, name, public)
  values ('gallery-thumbs', 'gallery-thumbs', true)
  on conflict (id) do update set public = true;

-- 允许匿名上传 + 公开读
drop policy if exists gallery_thumbs_anon_insert on storage.objects;
create policy gallery_thumbs_anon_insert on storage.objects
  for insert with check (bucket_id = 'gallery-thumbs');

drop policy if exists gallery_thumbs_public_select on storage.objects;
create policy gallery_thumbs_public_select on storage.objects
  for select using (bucket_id = 'gallery-thumbs');
