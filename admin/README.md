# UPDATIQ Control Center

Mobile-first admin website for UPDATIQ. This folder is intended to be deployed as a separate Cloudflare Pages site.

## Current state

- Responsive Russian-language admin UI
- Navigation for overview, news, heroes, counters, meta/builds, announcements and settings
- Supabase email/password sign-in scaffold
- No content writes are implemented yet; the dashboard deliberately does not pretend that server content is already connected.

## Configure Supabase

1. Create or select a Supabase project.
2. Enable Email authentication and create an administrator user.
3. Set `supabaseUrl` and the public publishable/anon key in `config.js`.
4. Do not use the `service_role` key in browser code.
5. Before enabling content editing, create tables and Row Level Security policies that permit writes only to authenticated administrators. Do not rely on hiding buttons as security.

## Deploy on Cloudflare Pages

- Connect the GitHub repository `raeffsky/UPDATIQ`.
- Production branch: `main` (or choose `development` while testing).
- Build command: leave empty.
- Build output directory: `admin`.
- After deployment, add the deployed domain to Supabase Auth URL configuration.

Deploying the folder does not change the APK. The Android app will only receive server-driven content after its relevant sections are connected to the database.
