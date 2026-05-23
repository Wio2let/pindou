<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal-card card">
      <div class="modal-head">
        <span class="modal-title">🛒 去 pg.zwpyyds.com 买豆</span>
        <button class="modal-close" @click="$emit('close')">✕</button>
      </div>

      <div class="modal-body">
        <p class="intro">
          下单清单已根据当前画布的颜色自动整理，可以
          <b>调整数量</b>、<b>删除</b> 不要的色号，或者
          <b>添加</b> 没在画布上的色号。准备好后点「去下单」会复制清单并打开 pg.zwpyyds.com 的买豆页。
        </p>

        <!-- Summary chip -->
        <div class="summary">
          <span class="sum-chip"><b>{{ items.length }}</b> 种色号</span>
          <span class="sum-chip"><b>{{ totalQty }}</b> 颗豆</span>
          <span class="sum-spacer"></span>
          <button class="btn btn-xs btn-ghost" @click="resetFromCanvas"
                  title="按当前画布颜色重新统计">↺ 按画布重置</button>
        </div>

        <!-- Order list -->
        <div class="order-list" v-if="items.length > 0">
          <div v-for="(it, idx) in items" :key="it.code" class="order-row">
            <span class="swatch"
                  :style="{ background: mardColors[it.code]?.hex || '#ccc',
                            color: textOnFor(it.code) }">{{ it.code }}</span>
            <span class="cname">{{ mardColors[it.code]?.name || '未知色' }}</span>
            <input type="number" min="0" step="1" class="qty-input"
                   v-model.number="it.qty" @blur="onQtyBlur(idx)" />
            <span class="qty-suffix">颗</span>
            <button class="row-x" title="移除此色号" @click="removeAt(idx)">✕</button>
          </div>
        </div>
        <div v-else class="empty-row">清单为空 —— 加几个色号吧 ↓</div>

        <!-- Add new color -->
        <div class="add-section">
          <div class="add-head">
            <span>＋ 添加色号</span>
            <input type="text" v-model="searchTerm" class="search"
                   placeholder="按色号或名称搜索（如 A1 / 浅黄）" />
          </div>
          <div v-if="searchTerm.trim()" class="add-grid">
            <button v-for="c in searchResults" :key="c.code"
                    class="add-chip"
                    :disabled="hasCode(c.code)"
                    :style="{ background: c.hex, color: textOn(c.hex) }"
                    :title="hasCode(c.code) ? '已在清单中' : `添加 ${c.code} ${c.name}`"
                    @click="addCode(c.code)">
              <span class="ac-code">{{ c.code }}</span>
              <span class="ac-name">{{ c.name }}</span>
            </button>
            <div v-if="searchResults.length === 0" class="add-empty">没有匹配的色号</div>
          </div>
        </div>
      </div>

      <!-- Footer actions -->
      <div class="modal-foot">
        <button class="btn btn-ghost btn-sm" @click="copyList"
                :disabled="items.length === 0"
                title="把清单复制到剪贴板（方便粘贴到买豆页）">
          {{ copied ? '✓ 已复制' : '📋 复制清单' }}
        </button>
        <span class="foot-spacer"></span>
        <button class="btn btn-sm" @click="$emit('close')">取消</button>
        <button class="btn btn-primary btn-sm" :disabled="items.length === 0"
                @click="goShop">
          去下单 →
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { MARD_COLORS } from '../data/mardPalettes'

const props = defineProps<{
  /** auto-selected color codes → count, taken from the current canvas */
  colorCounts: Map<string, number>
  mardColors: Record<string, { name: string; hex: string; rgb: [number, number, number] }>
}>()

const emit = defineEmits<{ close: [] }>()

const BUY_URL = 'https://pg.zwpyyds.com/buyPindou'

type OrderItem = { code: string; qty: number }

function initialItems(): OrderItem[] {
  return [...props.colorCounts.entries()]
    .map(([code, qty]) => ({ code, qty }))
    .sort((a, b) => b.qty - a.qty)
}

const items = ref<OrderItem[]>(initialItems())
const searchTerm = ref('')
const copied = ref(false)

// Re-seed only when the source map identity changes (e.g. canvas edits while dialog is open).
watch(() => props.colorCounts, () => {
  items.value = initialItems()
})

const totalQty = computed(() => items.value.reduce((s, i) => s + (i.qty | 0), 0))

function hasCode(code: string) { return items.value.some(i => i.code === code) }

function addCode(code: string) {
  if (hasCode(code)) return
  const baseQty = props.colorCounts.get(code) || 1
  items.value.push({ code, qty: baseQty })
  searchTerm.value = ''
}
function removeAt(idx: number) {
  items.value.splice(idx, 1)
}
function onQtyBlur(idx: number) {
  const v = items.value[idx]
  if (!v) return
  v.qty = Math.max(0, Math.floor(Number(v.qty) || 0))
  if (v.qty === 0) items.value.splice(idx, 1)
}
function resetFromCanvas() {
  items.value = initialItems()
}

const ALL_COLORS = computed(() => Object.entries(MARD_COLORS).map(([code, v]) => ({ code, ...v })))

const searchResults = computed(() => {
  const q = searchTerm.value.trim().toLowerCase()
  if (!q) return []
  return ALL_COLORS.value
    .filter(c => c.code.toLowerCase().includes(q) || c.name.toLowerCase().includes(q))
    .slice(0, 60)
})

function textOn(hex: string): string {
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  return (r * 299 + g * 587 + b * 114) / 1000 > 145 ? '#000' : '#fff'
}
function textOnFor(code: string): string {
  return textOn(props.mardColors[code]?.hex || '#cccccc')
}

function formatList(): string {
  return items.value.map(i => `${i.code} ${i.qty}`).join('\n')
}

async function copyList() {
  try {
    await navigator.clipboard.writeText(formatList())
    copied.value = true
    setTimeout(() => { copied.value = false }, 1800)
  } catch (e) {
    // older browsers — fall back to textarea trick
    const ta = document.createElement('textarea')
    ta.value = formatList(); document.body.appendChild(ta)
    ta.select(); document.execCommand('copy'); ta.remove()
    copied.value = true
    setTimeout(() => { copied.value = false }, 1800)
  }
}

async function goShop() {
  await copyList()
  window.open(BUY_URL, '_blank', 'noopener')
}
</script>

<style scoped>
.modal-overlay {
  position: fixed; inset: 0; background: rgba(74,54,69,0.35);
  display: flex; align-items: center; justify-content: center;
  z-index: 100; backdrop-filter: blur(4px);
}
.modal-card {
  width: min(580px, 94vw); max-height: 86vh; display: flex; flex-direction: column;
  padding: 1.1rem 1.35rem 0.85rem;
  animation: pop-in 0.3s cubic-bezier(0.34, 1.56, 0.64, 1) both;
}
.modal-head {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 0.6rem;
}
.modal-title { font-family: var(--font-display); font-size: 1.1rem; color: var(--plum-1); }
.modal-close { background: none; border: none; font-size: 1.2rem; cursor: pointer; color: var(--plum-3); }
.modal-close:hover { color: var(--plum-1); }
.modal-body { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 0.65rem; min-height: 0; }
.modal-foot {
  display: flex; align-items: center; gap: 0.45rem;
  padding-top: 0.6rem; border-top: 1.5px dashed var(--line-strong); margin-top: 0.4rem;
}
.foot-spacer { flex: 1; }

.intro { font-size: 0.78rem; color: var(--plum-2); margin: 0; line-height: 1.55; }
.intro b { color: var(--plum-1); }

.summary {
  display: flex; align-items: center; gap: 0.4rem;
  font-size: 0.74rem; color: var(--plum-2);
}
.sum-chip {
  background: var(--cream-2); border: 1.5px solid var(--line-strong);
  border-radius: var(--radius-pill); padding: 0.18rem 0.6rem;
}
.sum-chip b { color: var(--sakura-deep); font-family: var(--font-mono); }
.sum-spacer { flex: 1; }

.order-list { display: flex; flex-direction: column; gap: 0.3rem; }
.order-row {
  display: grid; grid-template-columns: auto 1fr auto auto auto;
  align-items: center; gap: 0.5rem;
  padding: 0.35rem 0.55rem; border: 1.5px solid var(--line-strong);
  border-radius: var(--radius-sm); background: #fff;
}
.swatch {
  display: inline-flex; align-items: center; justify-content: center;
  min-width: 2.4rem; height: 1.6rem; padding: 0 0.4rem;
  border-radius: 5px; font-family: var(--font-mono); font-weight: 800;
  font-size: 0.72rem; border: 1.5px solid rgba(0,0,0,0.15);
}
.cname { font-size: 0.8rem; color: var(--plum-1); }
.qty-input {
  width: 64px; padding: 0.2rem 0.4rem;
  border: 1.5px solid var(--cream-4); border-radius: var(--radius-sm);
  font-family: var(--font-mono); font-weight: 700; text-align: right;
  background: #fff; color: var(--plum-1); outline: none;
}
.qty-input:focus { border-color: var(--sakura); }
.qty-suffix { font-size: 0.72rem; color: var(--plum-3); }
.row-x {
  width: 1.5rem; height: 1.5rem; border: none; background: transparent;
  color: var(--plum-3); cursor: pointer; border-radius: 50%;
  font-size: 0.8rem; transition: all var(--transition-fast);
}
.row-x:hover { background: var(--bad-glow); color: var(--bad); }
.empty-row { text-align: center; color: var(--plum-3); padding: 0.8rem 0; font-size: 0.8rem; }

.add-section {
  border: 1.5px dashed var(--line-strong); border-radius: var(--radius-md);
  padding: 0.55rem 0.7rem; background: var(--cream-1);
}
.add-head {
  display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap;
  font-size: 0.78rem; font-weight: 700; color: var(--plum-2);
}
.search {
  flex: 1; min-width: 140px;
  padding: 0.28rem 0.55rem; border: 1.5px solid var(--cream-4);
  border-radius: var(--radius-sm); font-size: 0.78rem; outline: none;
  background: #fff;
}
.search:focus { border-color: var(--sakura); }
.add-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(78px, 1fr));
  gap: 4px; margin-top: 0.5rem; max-height: 200px; overflow-y: auto;
  padding: 2px;
}
.add-chip {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 1px; padding: 0.25rem 0.3rem;
  border: 1.5px solid rgba(0,0,0,0.12); border-radius: var(--radius-sm);
  cursor: pointer; transition: transform var(--transition-fast);
  font-family: var(--font-mono); font-weight: 700;
}
.add-chip:hover:not(:disabled) { transform: scale(1.04); }
.add-chip:disabled { opacity: 0.45; cursor: not-allowed; }
.ac-code { font-size: 0.72rem; line-height: 1; }
.ac-name { font-size: 0.56rem; line-height: 1; opacity: 0.85; }
.add-empty { grid-column: 1 / -1; text-align: center; color: var(--plum-3); font-size: 0.74rem; padding: 0.6rem 0; }
</style>
