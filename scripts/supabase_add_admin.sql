-- 给画廊后端增加「管理员」角色 —— 可以删任意人发布的作品
--
-- 跑这个脚本之前先要做一次性的事：
--   1. Supabase Dashboard → Authentication → Users → 「Add user」
--   2. Email 填  root@pindou.local
--      Password 填  Bl/i1088
--      勾选 「Auto Confirm User」（跳过邮箱验证）
--      点 Create user
--   3. 列表里点这个新用户复制它的 UUID（user_id）
--
-- 然后把下面 INSERT 那一行的 'PASTE-ROOT-USER-UUID-HERE' 替换成那个 UUID。
-- 整段贴进 SQL Editor 跑一次。重复跑不会出错（幂等）。
--
-- 之后在登录框输入 root + Bl/i1088 就能用管理员身份登录，
-- 画廊里每张卡片都会出现 🗑 取消发布 按钮。

-- ============================================================================
-- 1. 管理员用户表
-- ============================================================================
create table if not exists public.gallery_admins (
  user_id    uuid primary key references auth.users(id) on delete cascade,
  created_at timestamptz not null default now(),
  note       text
);

alter table public.gallery_admins enable row level security;

-- 任何登录用户都能读管理员名单（用来在前端判断自己是不是 admin）
drop policy if exists gallery_admins_authed_select on public.gallery_admins;
create policy gallery_admins_authed_select on public.gallery_admins
  for select using (auth.role() = 'authenticated');

-- ============================================================================
-- 2. ⚠️ 把 root 用户的 UUID 填到下面再跑
-- ============================================================================
insert into public.gallery_admins (user_id, note)
  values ('PASTE-ROOT-USER-UUID-HERE', 'root admin')
  on conflict (user_id) do nothing;

-- ============================================================================
-- 3. 升级 DELETE 策略 —— 自己的行或者 admin 都能删
-- ============================================================================
drop policy if exists gallery_authed_delete on public.gallery_works;
create policy gallery_authed_delete on public.gallery_works
  for delete using (
    auth.uid() = user_id
    or auth.uid() in (select user_id from public.gallery_admins)
  );

-- ============================================================================
-- 4. Storage 同步升级 —— 自己 uid 文件夹下的文件或者 admin 都能删
-- ============================================================================
drop policy if exists gallery_thumbs_authed_delete on storage.objects;
create policy gallery_thumbs_authed_delete on storage.objects
  for delete using (
    bucket_id = 'gallery-thumbs'
    and (
      auth.uid()::text = (storage.foldername(name))[1]
      or auth.uid() in (select user_id from public.gallery_admins)
    )
  );
