-- 升级画廊为「邮箱登录用户体系」
--
-- 在 Supabase SQL Editor 里整段贴进去 Run 一次。已经跑过会幂等。
--
-- 跑完之后：
--   • 已经存在的画廊作品 user_id 是 NULL，所有人都能看（SELECT 公开）
--     但谁也删不掉（DELETE 要求 user_id = auth.uid()），它们变成"遗产"
--   • 新发布的作品需要登录后才能发，user_id 自动记成当前账号
--   • 只有发布者本人能删自己的作品
--   • 文件按 <user_id>/<slug>.png 的目录结构存，Storage 策略只允许
--     在自己 uid 文件夹下读写

-- ============================================================================
-- 1. gallery_works 表增加 user_id 列
-- ============================================================================
alter table public.gallery_works
  add column if not exists user_id uuid references auth.users(id) on delete cascade;

create index if not exists gallery_works_user_idx on public.gallery_works(user_id);

-- ============================================================================
-- 2. 替换 INSERT / DELETE 策略
-- ============================================================================
drop policy if exists gallery_anon_insert on public.gallery_works;
drop policy if exists gallery_anon_delete on public.gallery_works;

-- 登录后才能发，且 user_id 必须是自己
create policy gallery_authed_insert on public.gallery_works
  for insert with check (auth.uid() = user_id);

-- 只能删自己的行
create policy gallery_authed_delete on public.gallery_works
  for delete using (auth.uid() = user_id);

-- SELECT 保持公开（gallery_anon_select 保持不变，所有人都能看）

-- ============================================================================
-- 3. Storage 策略也按 user 文件夹隔离
-- ============================================================================
drop policy if exists gallery_thumbs_anon_insert on storage.objects;
drop policy if exists gallery_thumbs_anon_delete on storage.objects;

-- 上传到 <auth.uid()>/xxx.png 才允许
create policy gallery_thumbs_authed_insert on storage.objects
  for insert with check (
    bucket_id = 'gallery-thumbs'
    and auth.uid()::text = (storage.foldername(name))[1]
  );

-- 删除同样要求文件在自己的 uid 目录下
create policy gallery_thumbs_authed_delete on storage.objects
  for delete using (
    bucket_id = 'gallery-thumbs'
    and auth.uid()::text = (storage.foldername(name))[1]
  );

-- 读取保持公开（gallery_thumbs_public_select 不变）

-- ============================================================================
-- 4. (可选) 清掉那些 user_id 为 NULL 的旧作品 ——
--    它们现在没人能删，可以一次性洗掉。如果想保留就把下面这段注释掉。
-- ============================================================================
-- delete from public.gallery_works where user_id is null;
