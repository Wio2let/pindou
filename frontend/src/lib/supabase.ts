/**
 * Supabase client wrapper.
 *
 * Reads URL + anon key from Vite env (VITE_SUPABASE_URL / VITE_SUPABASE_ANON_KEY).
 * If neither is set the module exports `supabase = null`, and callers should
 * fall back to a local-only path (e.g. localStorage). This way the static site
 * keeps working out of the box even before backend keys are configured.
 *
 * Set up:
 *   1. Create a Supabase project (free tier is fine).
 *   2. In `frontend/.env.local` (dev) and the GitHub Pages build secrets (prod):
 *        VITE_SUPABASE_URL=https://<project-ref>.supabase.co
 *        VITE_SUPABASE_ANON_KEY=<the public "anon" key>
 *   3. In Supabase SQL editor run the bootstrap script
 *      (see scripts/supabase_bootstrap.sql) to create the gallery table +
 *      storage bucket + RLS policies for anonymous read/insert.
 */
import { createClient, type SupabaseClient } from '@supabase/supabase-js'

const URL = import.meta.env.VITE_SUPABASE_URL as string | undefined
const ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined

export const supabase: SupabaseClient | null =
  URL && ANON_KEY ? createClient(URL, ANON_KEY) : null

export const REMOTE_ENABLED = supabase !== null

export const GALLERY_TABLE = 'gallery_works'
export const GALLERY_BUCKET = 'gallery-thumbs'
