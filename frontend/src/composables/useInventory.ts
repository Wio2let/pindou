/**
 * useInventory — bead inventory storage.
 *
 * The user's "我的库存" is a flat map of `MARD code → quantity`. Each "+1"
 * click in the UI bumps the count by BULK (default 500). "完工" deducts the
 * canvas's colour counts in one go and reports which codes dropped below the
 * configurable low-stock threshold so the caller can show a reorder reminder.
 *
 * Persistence:
 *   • not logged in (or no Supabase configured) — localStorage only
 *   • logged in — Supabase row in user_inventories is authoritative;
 *     the local state is hydrated from it on sign-in, and every mutation
 *     is debounced-upserted back so the user's inventory follows their
 *     account across devices.
 */
import { ref, watch } from 'vue'
import { supabase, REMOTE_ENABLED } from '../lib/supabase'
import { useAuth } from './useAuth'

const STORAGE_KEY = 'bead-inventory-v1'
const THRESHOLD_KEY = 'bead-inventory-threshold-v1'
const TABLE = 'user_inventories'

export const BULK = 500
export const DEFAULT_THRESHOLD = 100

interface InventoryState {
  counts: Record<string, number>
  threshold: number
}

function loadState(): InventoryState {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    const counts = (raw ? JSON.parse(raw) : {}) as Record<string, number>
    const t = localStorage.getItem(THRESHOLD_KEY)
    const threshold = t == null ? DEFAULT_THRESHOLD : Math.max(0, Number(t) || 0)
    return { counts, threshold }
  } catch {
    return { counts: {}, threshold: DEFAULT_THRESHOLD }
  }
}

// Module-level singleton — same inventory whichever component reads it.
const state = ref<InventoryState>(loadState())

// Set to true while pulling from cloud, so the resulting state.value=... write
// doesn't trigger another push back up.
let suppressCloudPush = false

let saveTimer: number | null = null
let cloudSaveTimer: number | null = null
watch(state, () => {
  // localStorage save (always — works as offline cache too)
  if (saveTimer != null) clearTimeout(saveTimer)
  saveTimer = window.setTimeout(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state.value.counts))
      localStorage.setItem(THRESHOLD_KEY, String(state.value.threshold))
    } catch { /* quota / private mode — swallow */ }
  }, 150)
  // cloud upsert when logged in (debounced; suppressed during hydrate)
  if (suppressCloudPush) return
  if (cloudSaveTimer != null) clearTimeout(cloudSaveTimer)
  cloudSaveTimer = window.setTimeout(() => { pushToCloud() }, 800)
}, { deep: true })

async function pushToCloud() {
  if (!REMOTE_ENABLED || !supabase) return
  const { user } = useAuth()
  if (!user.value) return
  await supabase.from(TABLE).upsert({
    user_id: user.value.id,
    counts: state.value.counts,
    threshold: state.value.threshold,
    updated_at: new Date().toISOString(),
  })
}

async function hydrateFromCloud() {
  if (!REMOTE_ENABLED || !supabase) return
  const { user } = useAuth()
  if (!user.value) return
  try {
    const { data, error } = await supabase
      .from(TABLE)
      .select('counts, threshold')
      .eq('user_id', user.value.id)
      .maybeSingle()
    if (error) throw error
    if (data) {
      // cloud row exists → take it as authoritative
      suppressCloudPush = true
      state.value = {
        counts: (data.counts as Record<string, number>) || {},
        threshold: typeof data.threshold === 'number' ? data.threshold : DEFAULT_THRESHOLD,
      }
      // re-enable cloud sync after Vue's microtask flush
      setTimeout(() => { suppressCloudPush = false }, 50)
    } else {
      // no cloud row yet → push current local state up so this device's
      // pre-login work isn't lost
      await pushToCloud()
    }
  } catch {
    // network / RLS errors: stay on local state silently
  }
}

// Hook auth changes — re-hydrate when a user signs in; reset to localStorage
// on sign-out so the next visitor on this browser sees their own data.
if (REMOTE_ENABLED) {
  const { user } = useAuth()
  watch(user, (now, prev) => {
    if (now && now.id !== prev?.id) {
      hydrateFromCloud()
    } else if (!now && prev) {
      suppressCloudPush = true
      state.value = loadState()
      setTimeout(() => { suppressCloudPush = false }, 50)
    }
  }, { immediate: true })
}

export interface LowStockEntry { code: string; remaining: number }
export interface InsufficientEntry { code: string; needed: number; had: number }
export interface DeductResult {
  lowStock: LowStockEntry[]
  insufficient: InsufficientEntry[]
  totalDeducted: number
}

export function useInventory() {
  function getCount(code: string): number {
    return state.value.counts[code] || 0
  }
  function setCount(code: string, n: number) {
    const v = Math.max(0, Math.floor(Number(n)) || 0)
    if (v === 0) delete state.value.counts[code]
    else state.value.counts[code] = v
  }
  function add(code: string, amount = BULK) {
    setCount(code, getCount(code) + amount)
  }
  function remove(code: string, amount = BULK) {
    setCount(code, getCount(code) - amount)
  }
  function clearAll() {
    state.value.counts = {}
  }
  function setThreshold(n: number) {
    state.value.threshold = Math.max(0, Math.floor(Number(n)) || 0)
  }

  /**
   * Deduct one finished pattern's bead counts from inventory.
   * Returns the codes that ran short (`insufficient`) and the codes that
   * dropped below the low-stock threshold after deduction (`lowStock`).
   */
  function deductByCounts(used: Map<string, number>): DeductResult {
    const out: DeductResult = { lowStock: [], insufficient: [], totalDeducted: 0 }
    for (const [code, n] of used) {
      const had = getCount(code)
      const take = Math.max(0, n | 0)
      if (take > had) out.insufficient.push({ code, needed: take, had })
      const remaining = Math.max(0, had - take)
      out.totalDeducted += Math.min(had, take)
      setCount(code, remaining)
      if (remaining < state.value.threshold) {
        out.lowStock.push({ code, remaining })
      }
    }
    // sort low-stock for stable display: lowest first
    out.lowStock.sort((a, b) => a.remaining - b.remaining)
    return out
  }

  return {
    state,
    getCount, setCount, add, remove, clearAll, setThreshold, deductByCounts,
    BULK, DEFAULT_THRESHOLD,
  }
}
