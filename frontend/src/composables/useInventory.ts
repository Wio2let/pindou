/**
 * useInventory — local bead inventory, persisted in localStorage.
 *
 * The user's "我的库存" is a flat map of `MARD code → quantity`. Each "+1"
 * click in the UI bumps the count by BULK (default 500) — typical pack size.
 * "此作品已拼完" deducts the canvas's colour counts from inventory in one go
 * and reports which codes dropped below the user-configurable low-stock
 * threshold so the caller can show a reorder reminder.
 */
import { ref, watch } from 'vue'

const STORAGE_KEY = 'bead-inventory-v1'
const THRESHOLD_KEY = 'bead-inventory-threshold-v1'

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

let saveTimer: number | null = null
watch(state, () => {
  if (saveTimer != null) clearTimeout(saveTimer)
  saveTimer = window.setTimeout(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state.value.counts))
      localStorage.setItem(THRESHOLD_KEY, String(state.value.threshold))
    } catch { /* quota / private mode — swallow */ }
  }, 150)
}, { deep: true })

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
