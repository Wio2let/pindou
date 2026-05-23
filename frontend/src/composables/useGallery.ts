/**
 * useGallery — shared bead-pattern gallery.
 *
 * When Supabase env vars are set (VITE_SUPABASE_URL + VITE_SUPABASE_ANON_KEY):
 *   • thumbnails go into the `gallery-thumbs` storage bucket (public read)
 *   • metadata goes into the `gallery_works` table
 *   • the state ref hydrates from a single SELECT on first use; published
 *     works are appended after a successful insert, so other devices that
 *     reload see them too
 *
 * Without those env vars we fall back to a local-only gallery in
 * localStorage so the static site keeps working in dev / preview.
 *
 * Either way the public API is the same: state ref + publish/remove/clearAll.
 */
import { ref } from 'vue'
import { supabase, REMOTE_ENABLED, GALLERY_TABLE, GALLERY_BUCKET } from '../lib/supabase'
import { useAuth } from './useAuth'

export const MAX_WORKS = 500

export interface GalleryWork {
  id: string
  title: string
  createdAt: number       // epoch ms
  width: number
  height: number
  totalBeads: number
  uniqueColors: number
  beadShape: 'circle' | 'square' | 'fill'
  thumbnail: string       // resolved URL (or data: URL in local mode)
  thumbPath?: string      // remote-only: storage object path, used to also delete the file
  userId?: string | null  // remote-only: who published it (auth user id)
}

interface DBRow {
  id: string
  created_at: string
  title: string
  width: number
  height: number
  total_beads: number
  unique_colors: number
  bead_shape: 'circle' | 'square' | 'fill'
  thumb_path: string
  user_id: string | null
}

const LOCAL_STORAGE_KEY = 'bead-gallery-v1'

// ---- local fallback persistence -------------------------------------------
function loadLocal(): GalleryWork[] {
  try {
    const raw = localStorage.getItem(LOCAL_STORAGE_KEY)
    const arr = raw ? JSON.parse(raw) : []
    return Array.isArray(arr) ? arr : []
  } catch { return [] }
}
function saveLocal(items: GalleryWork[]) {
  try {
    localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(items))
  } catch (e) {
    // quota — drop the oldest half and retry once
    if (items.length > 1) {
      const half = items.slice(0, Math.floor(items.length / 2))
      try { localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(half)) } catch {}
    }
  }
}

// ---- module-singleton state ------------------------------------------------
const state = ref<GalleryWork[]>(REMOTE_ENABLED ? [] : loadLocal())
const loading = ref<boolean>(REMOTE_ENABLED)
const error = ref<string | null>(null)
let hydrated = !REMOTE_ENABLED


function publicUrlFor(path: string): string {
  if (!supabase) return path
  const { data } = supabase.storage.from(GALLERY_BUCKET).getPublicUrl(path)
  return data.publicUrl
}

function rowToWork(r: DBRow): GalleryWork {
  return {
    id: r.id,
    title: r.title,
    createdAt: new Date(r.created_at).getTime(),
    width: r.width,
    height: r.height,
    totalBeads: r.total_beads,
    uniqueColors: r.unique_colors,
    beadShape: r.bead_shape,
    thumbnail: publicUrlFor(r.thumb_path),
    thumbPath: r.thumb_path,
    userId: r.user_id,
  }
}

/** Pull the latest works from Supabase into state. No-op in local mode. */
async function refresh(): Promise<void> {
  if (!supabase) return
  loading.value = true
  error.value = null
  try {
    const { data, error: dbErr } = await supabase
      .from(GALLERY_TABLE)
      .select('*')
      .order('created_at', { ascending: false })
      .limit(MAX_WORKS)
    if (dbErr) throw dbErr
    state.value = (data || []).map(rowToWork)
  } catch (e: any) {
    error.value = e?.message || String(e)
  } finally {
    loading.value = false
    hydrated = true
  }
}

/** Hydrate the state once. Subsequent calls are no-ops unless `force` is set. */
async function ensureHydrated(force = false): Promise<void> {
  if (!REMOTE_ENABLED) return
  if (hydrated && !force) return
  await refresh()
}

// ---- helpers ---------------------------------------------------------------
function dataUrlToBlob(dataUrl: string): Blob {
  const [head, b64] = dataUrl.split(',')
  const mime = /data:([^;]+)/.exec(head)?.[1] || 'application/octet-stream'
  const bin = atob(b64)
  const arr = new Uint8Array(bin.length)
  for (let i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i)
  return new Blob([arr], { type: mime })
}

function randSlug(): string {
  return Date.now().toString(36) + '_' + Math.random().toString(36).slice(2, 8)
}

// ---- public API ------------------------------------------------------------
export function useGallery() {
  /**
   * Publish a new work. `thumbnailDataUrl` is the `data:image/jpeg;base64,...`
   * encoded image; in remote mode it gets uploaded to storage and the row
   * insert references its public URL.
   */
  async function publish(work: {
    title: string
    width: number
    height: number
    totalBeads: number
    uniqueColors: number
    beadShape: 'circle' | 'square' | 'fill'
    thumbnailDataUrl: string
  }): Promise<GalleryWork> {
    if (REMOTE_ENABLED && supabase) {
      // 1. require a signed-in user — RLS will reject the insert otherwise
      const { user } = useAuth()
      const uid = user.value?.id
      if (!uid) throw new Error('请先登录后再发布')
      // 2. upload the thumbnail blob under <uid>/<slug>.png (matches the
      //    storage RLS policy that limits writes to your own uid folder)
      const blob = dataUrlToBlob(work.thumbnailDataUrl)
      const ext = blob.type.includes('png') ? 'png' : 'jpg'
      const path = `${uid}/${randSlug()}.${ext}`
      const { error: upErr } = await supabase.storage
        .from(GALLERY_BUCKET)
        .upload(path, blob, { contentType: blob.type, cacheControl: '31536000' })
      if (upErr) throw upErr
      // 3. insert the metadata row with user_id = self
      const { data, error: insErr } = await supabase
        .from(GALLERY_TABLE)
        .insert({
          title: work.title,
          width: work.width,
          height: work.height,
          total_beads: work.totalBeads,
          unique_colors: work.uniqueColors,
          bead_shape: work.beadShape,
          thumb_path: path,
          user_id: uid,
        })
        .select('*')
        .single()
      if (insErr || !data) throw insErr || new Error('insert returned no row')
      const entry = rowToWork(data as DBRow)
      state.value.unshift(entry)
      while (state.value.length > MAX_WORKS) state.value.pop()
      return entry
    }
    // local fallback
    const entry: GalleryWork = {
      id: 'g_' + randSlug(),
      title: work.title,
      createdAt: Date.now(),
      width: work.width,
      height: work.height,
      totalBeads: work.totalBeads,
      uniqueColors: work.uniqueColors,
      beadShape: work.beadShape,
      thumbnail: work.thumbnailDataUrl,
    }
    state.value.unshift(entry)
    while (state.value.length > MAX_WORKS) state.value.pop()
    saveLocal(state.value)
    return entry
  }

  /** Local-only remove (used by the legacy local-storage fallback). */
  function remove(id: string) {
    const idx = state.value.findIndex(w => w.id === id)
    if (idx >= 0) state.value.splice(idx, 1)
    if (!REMOTE_ENABLED) saveLocal(state.value)
  }

  /**
   * Does the current signed-in user own this work?
   * In remote mode: matches the row's user_id against the auth session.
   * In local-only mode: every local work counts as mine.
   */
  function isMine(id: string): boolean {
    if (!REMOTE_ENABLED) return true
    const work = state.value.find(w => w.id === id)
    if (!work) return false
    const { user } = useAuth()
    return !!user.value && work.userId === user.value.id
  }

  /**
   * Take a work down from the gallery. In remote mode this deletes both the
   * row and the storage file; in local mode it just drops the entry. We only
   * call this for works the current browser actually published — the gallery
   * UI hides the button otherwise.
   */
  async function unpublish(id: string): Promise<void> {
    if (REMOTE_ENABLED && supabase) {
      const work = state.value.find(w => w.id === id)
      const idx = state.value.findIndex(w => w.id === id)
      if (idx >= 0) state.value.splice(idx, 1)
      try {
        const { error: delErr } = await supabase
          .from(GALLERY_TABLE)
          .delete()
          .eq('id', id)
        if (delErr) throw delErr
        if (work?.thumbPath) {
          await supabase.storage.from(GALLERY_BUCKET).remove([work.thumbPath])
        }
      } catch (e: any) {
        // restore on failure so the user sees their work is still up
        if (work && idx >= 0) state.value.splice(idx, 0, work)
        throw e
      }
      return
    }
    remove(id)
  }

  function clearAll() {
    state.value = []
    if (!REMOTE_ENABLED) saveLocal(state.value)
  }
  function get(id: string): GalleryWork | undefined {
    return state.value.find(w => w.id === id)
  }

  return {
    state, loading, error,
    publish, remove, unpublish, isMine, clearAll, get,
    refresh, ensureHydrated,
    MAX_WORKS, REMOTE_ENABLED,
  }
}
