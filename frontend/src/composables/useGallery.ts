/**
 * useGallery — local "画廊" for published bead patterns.
 *
 * Each work stores a thumbnail PNG (with colour-code labels) plus enough
 * metadata to display in the gallery view. Persisted in localStorage on the
 * user's device — there's no server backing this in the static build.
 *
 * Capacity is capped (oldest evicted) to stay well under the typical
 * 5-10 MB localStorage quota.
 */
import { ref, watch } from 'vue'

const STORAGE_KEY = 'bead-gallery-v1'
const MAX_WORKS = 60

export interface GalleryWork {
  id: string
  title: string
  createdAt: number       // epoch ms
  width: number
  height: number
  totalBeads: number
  uniqueColors: number
  beadShape: 'circle' | 'square' | 'fill'
  thumbnail: string       // data:image/png;base64,...
}

function load(): GalleryWork[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    const arr = raw ? JSON.parse(raw) : []
    return Array.isArray(arr) ? arr : []
  } catch { return [] }
}

const state = ref<GalleryWork[]>(load())

let saveTimer: number | null = null
watch(state, () => {
  if (saveTimer != null) clearTimeout(saveTimer)
  saveTimer = window.setTimeout(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state.value))
    } catch (e) {
      // quota — drop the oldest work and retry once
      if (state.value.length > 1) {
        state.value = state.value.slice(0, Math.floor(state.value.length / 2))
        try { localStorage.setItem(STORAGE_KEY, JSON.stringify(state.value)) } catch {}
      }
    }
  }, 150)
}, { deep: true })

export function useGallery() {
  function publish(work: Omit<GalleryWork, 'id' | 'createdAt'>): GalleryWork {
    const entry: GalleryWork = {
      ...work,
      id: 'g_' + Date.now() + '_' + Math.random().toString(36).slice(2, 7),
      createdAt: Date.now(),
    }
    state.value.unshift(entry)              // newest first
    while (state.value.length > MAX_WORKS) state.value.pop()
    return entry
  }
  function remove(id: string) {
    const idx = state.value.findIndex(w => w.id === id)
    if (idx >= 0) state.value.splice(idx, 1)
  }
  function clearAll() { state.value = [] }
  function get(id: string): GalleryWork | undefined {
    return state.value.find(w => w.id === id)
  }
  return { state, publish, remove, clearAll, get, MAX_WORKS }
}
