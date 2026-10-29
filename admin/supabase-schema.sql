-- UPDATIQ Admin: initial content schema
-- Run in Supabase SQL Editor. All tables use RLS.
-- Admin authorization uses app_metadata.role = 'admin', set only by trusted server/admin tooling.

create table if not exists public.updatiq_news (
  id uuid primary key default gen_random_uuid(),
  title text not null check (char_length(title) between 1 and 160),
  category text not null default 'Новости' check (category in ('Патч','Новости','Событие','Киберспорт','Объявление')),
  body text not null default '',
  status text not null default 'draft' check (status in ('draft','published','archived')),
  created_by uuid references auth.users(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  published_at timestamptz
);

create index if not exists updatiq_news_status_published_at_idx
  on public.updatiq_news(status, published_at desc);

create table if not exists public.updatiq_announcements (
  id uuid primary key default gen_random_uuid(),
  title text not null check (char_length(title) between 1 and 160),
  body text not null default '',
  status text not null default 'draft' check (status in ('draft','published','archived')),
  starts_at timestamptz,
  ends_at timestamptz,
  created_by uuid references auth.users(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  published_at timestamptz
);

create table if not exists public.updatiq_content (
  key text primary key check (char_length(key) between 1 and 100),
  value jsonb not null default '{}'::jsonb,
  description text not null default '',
  updated_by uuid references auth.users(id) on delete set null,
  updated_at timestamptz not null default now()
);

create or replace function public.updatiq_is_admin()
returns boolean
language sql
stable
security invoker
set search_path = ''
as $$
  select coalesce((auth.jwt() -> 'app_metadata' ->> 'role') = 'admin', false);
$$;

create or replace function public.updatiq_touch_updated_at()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists updatiq_news_touch_updated_at on public.updatiq_news;
create trigger updatiq_news_touch_updated_at before update on public.updatiq_news
for each row execute function public.updatiq_touch_updated_at();

drop trigger if exists updatiq_announcements_touch_updated_at on public.updatiq_announcements;
create trigger updatiq_announcements_touch_updated_at before update on public.updatiq_announcements
for each row execute function public.updatiq_touch_updated_at();

drop trigger if exists updatiq_content_touch_updated_at on public.updatiq_content;
create trigger updatiq_content_touch_updated_at before update on public.updatiq_content
for each row execute function public.updatiq_touch_updated_at();

alter table public.updatiq_news enable row level security;
alter table public.updatiq_announcements enable row level security;
alter table public.updatiq_content enable row level security;

-- Anyone may read published public-facing content; only admins may write.
drop policy if exists "Public can read published UPDATIQ news" on public.updatiq_news;
create policy "Public can read published UPDATIQ news"
on public.updatiq_news for select to anon, authenticated
using (status = 'published');

drop policy if exists "Admins manage UPDATIQ news" on public.updatiq_news;
create policy "Admins manage UPDATIQ news"
on public.updatiq_news for all to authenticated
using (public.updatiq_is_admin())
with check (public.updatiq_is_admin());

drop policy if exists "Public can read published UPDATIQ announcements" on public.updatiq_announcements;
create policy "Public can read published UPDATIQ announcements"
on public.updatiq_announcements for select to anon, authenticated
using (
  status = 'published'
  and (starts_at is null or starts_at <= now())
  and (ends_at is null or ends_at > now())
);

drop policy if exists "Admins manage UPDATIQ announcements" on public.updatiq_announcements;
create policy "Admins manage UPDATIQ announcements"
on public.updatiq_announcements for all to authenticated
using (public.updatiq_is_admin())
with check (public.updatiq_is_admin());

drop policy if exists "Public can read UPDATIQ content" on public.updatiq_content;
create policy "Public can read UPDATIQ content"
on public.updatiq_content for select to anon, authenticated
using (true);

drop policy if exists "Admins manage UPDATIQ content" on public.updatiq_content;
create policy "Admins manage UPDATIQ content"
on public.updatiq_content for all to authenticated
using (public.updatiq_is_admin())
with check (public.updatiq_is_admin());

-- IMPORTANT: after creating the admin auth user, assign app_metadata.role = "admin"
-- from a trusted server/admin interface. Never let users set app_metadata from the client.
