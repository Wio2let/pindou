-- 给已有 Supabase 项目追加「取消发布」需要的策略
-- 之前 scripts/supabase_bootstrap.sql 只放了 SELECT + INSERT 权限；
-- 这个脚本再加一对 DELETE 策略，让匿名用户可以删行 + 删对应的 Storage 文件。
--
-- 在 Supabase SQL Editor 里新开一个查询，整段贴进去，Run 一次即可。
-- 已经跑过会幂等（重复 drop / create），不会出错。

-- 1. 表行可以匿名删
drop policy if exists gallery_anon_delete on public.gallery_works;
create policy gallery_anon_delete on public.gallery_works
  for delete using (true);

-- 2. Storage 对应缩略图可以匿名删
drop policy if exists gallery_thumbs_anon_delete on storage.objects;
create policy gallery_thumbs_anon_delete on storage.objects
  for delete using (bucket_id = 'gallery-thumbs');

-- 说明：
-- 真正的「只删自己的」是靠前端在 localStorage 里只追踪自己发布过的作品 id，
-- 只对这些 id 显示「取消发布」按钮。RLS 这里放开是因为匿名身份没法在
-- 服务器端区分"谁是谁"，这是个人项目可以接受的权衡。
