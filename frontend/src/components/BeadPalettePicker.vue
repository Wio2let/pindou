<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal-card card pal-card">
      <div class="modal-head">
        <span class="modal-title">🎨 选择我的色板</span>
        <span class="pal-count mono">已选 {{ sel.size }} 色</span>
        <button class="modal-close" @click="$emit('close')">✕</button>
      </div>

      <!-- search + series tabs -->
      <div class="pal-toolbar">
        <input class="input pal-search" v-model="query" placeholder="搜索色号 / 颜色名…" />
        <div class="pal-series">
          <button class="series-tab" :class="{ on: activeSeries === '' }"
                  @click="activeSeries = ''">全部</button>
          <button v-for="g in groups" :key="g.key" class="series-tab"
                  :class="{ on: activeSeries === g.key }"
                  @click="activeSeries = g.key">{{ g.key }}</button>
        </div>
      </div>

      <!-- swatch groups -->
      <div class="pal-body">
        <div v-if="visibleGroups.length === 0" class="pal-empty">没有匹配的颜色</div>
        <div v-for="g in visibleGroups" :key="g.key" class="pal-group">
          <div class="pal-group-head">
            <span class="pal-group-key">{{ g.key }}</span>
            <span class="pal-group-name">{{ g.name }}</span>
            <span class="pal-group-n mono">{{ g.selCount }}/{{ g.colors.length }}</span>
            <button class="pal-group-all" @click="toggleGroup(g)">
              {{ g.selCount === g.colors.length ? '取消本系' : '全选本系' }}
            </button>
          </div>
          <div class="pal-grid">
            <button v-for="c in g.colors" :key="c.code"
                    class="pal-swatch" :class="{ on: sel.has(c.code) }"
                    :style="{ background: c.hex, color: textOn(c.rgb) }"
                    :title="`${c.code} ${c.name} ${c.hex}`"
                    @click="toggle(c.code)">
              <span class="pal-sw-code">{{ c.code }}</span>
              <span v-if="sel.has(c.code)" class="pal-sw-check">✓</span>
            </button>
          </div>
        </div>
      </div>

      <div class="modal-foot pal-foot">
        <button class="btn btn-ghost btn-sm" @click="selectNone">清空</button>
        <button class="btn btn-ghost btn-sm" @click="selectAll">全选 {{ allColors.length }} 色</button>
        <span class="pal-spacer"></span>
        <button class="btn btn-ghost" @click="$emit('close')">取消</button>
        <button class="btn btn-primary" @click="apply">确定 · {{ sel.size }} 色</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, reactive } from 'vue'
import { MARD_COLORS, MARD_GROUPS, type BeadColor } from '../data/mardPalettes'
import { textOn } from '../composables/usePerler'

const props = defineProps<{ codes: string[] }>()
const emit = defineEmits<{ close: []; apply: [string[]] }>()

// live selection — a reactive Set edited locally, committed on 确定
const sel = reactive(new Set<string>(props.codes))
const query = ref('')
const activeSeries = ref('')

const allColors = Object.values(MARD_COLORS)

function codeNum(code: string): number {
  return parseInt(code.replace(/^[A-Z]+/, ''), 10) || 0
}

// all MARD colors grouped by A/B/C… series, ordered numerically
const groups = computed(() => {
  const byKey = new Map<string, BeadColor[]>()
  for (const c of allColors) {
    const k = c.code.match(/^[A-Z]+/)?.[0] || c.code
    if (!byKey.has(k)) byKey.set(k, [])
    byKey.get(k)!.push(c)
  }
  for (const list of byKey.values()) list.sort((a, b) => codeNum(a.code) - codeNum(b.code))
  return MARD_GROUPS
    .map(g => ({ key: g.key, name: g.name, colors: byKey.get(g.key) || [] }))
    .filter(g => g.colors.length > 0)
})

// filtered by search + active series tab
const visibleGroups = computed(() => {
  const q = query.value.trim().toLowerCase()
  return groups.value
    .filter(g => !activeSeries.value || g.key === activeSeries.value)
    .map(g => {
      const colors = g.colors.filter(c =>
        !q || c.code.toLowerCase().includes(q)
           || c.name.toLowerCase().includes(q)
           || c.hex.toLowerCase().includes(q))
      return {
        key: g.key, name: g.name, colors,
        selCount: colors.reduce((n, c) => n + (sel.has(c.code) ? 1 : 0), 0),
      }
    })
    .filter(g => g.colors.length > 0)
})

function toggle(code: string) {
  if (sel.has(code)) sel.delete(code)
  else sel.add(code)
}
function toggleGroup(g: { colors: BeadColor[]; selCount: number }) {
  const all = g.selCount === g.colors.length
  for (const c of g.colors) {
    if (all) sel.delete(c.code)
    else sel.add(c.code)
  }
}
function selectNone() { sel.clear() }
function selectAll() { for (const c of allColors) sel.add(c.code) }
function apply() {
  // commit in canonical MARD series order for a tidy palette
  emit('apply', allColors.filter(c => sel.has(c.code)).map(c => c.code))
  emit('close')
}
</script>

<style scoped>
.modal-overlay {
  position: fixed; inset: 0; background: rgba(74,54,69,0.35);
  display: flex; align-items: center; justify-content: center;
  z-index: 100; backdrop-filter: blur(4px);
}
.pal-card {
  width: min(720px, 94vw);
  max-height: 88vh;
  padding: 1.1rem 1.25rem;
  display: flex; flex-direction: column;
  animation: pop-in 0.3s cubic-bezier(0.34, 1.56, 0.64, 1) both;
}
.modal-head {
  display: flex; align-items: center; gap: 0.6rem;
  margin-bottom: 0.85rem;
}
.modal-title { font-family: var(--font-display); font-size: 1.1rem; color: var(--plum-1); }
.pal-count {
  font-size: 0.72rem; color: var(--sakura-deep);
  background: var(--sakura-glow); padding: 0.1rem 0.55rem;
  border-radius: var(--radius-pill);
}
.modal-close {
  margin-left: auto; background: none; border: none;
  font-size: 1.2rem; cursor: pointer; color: var(--plum-3);
}
.modal-close:hover { color: var(--plum-1); }

/* toolbar */
.pal-toolbar {
  display: flex; align-items: center; gap: 0.7rem;
  margin-bottom: 0.7rem; flex-wrap: wrap;
}
.pal-search { width: 200px; }
.pal-series { display: flex; gap: 0.25rem; flex-wrap: wrap; }
.series-tab {
  min-width: 26px;
  padding: 0.22rem 0.5rem;
  border: 2px solid var(--cream-4);
  background: #fff;
  border-radius: var(--radius-pill);
  font-family: var(--font-mono);
  font-weight: 800;
  font-size: 0.72rem;
  color: var(--plum-2);
  cursor: pointer;
  transition: all var(--transition-fast);
}
.series-tab:hover { border-color: var(--sakura-light); }
.series-tab.on {
  background: var(--sakura); border-color: var(--sakura); color: #fff;
}

/* body */
.pal-body {
  overflow-y: auto;
  flex: 1;
  padding-right: 3px;
}
.pal-empty {
  text-align: center; color: var(--plum-3);
  font-size: 0.85rem; padding: 2rem 0;
}
.pal-group { margin-bottom: 0.85rem; }
.pal-group:last-child { margin-bottom: 0; }
.pal-group-head {
  display: flex; align-items: center; gap: 0.45rem;
  margin-bottom: 0.4rem;
  position: sticky; top: 0;
  background: #fff; padding: 0.2rem 0; z-index: 1;
}
.pal-group-key {
  font-family: var(--font-mono); font-weight: 800;
  color: var(--sakura-deep); background: var(--sakura-glow);
  border-radius: 4px; padding: 0 0.35rem; font-size: 0.78rem;
}
.pal-group-name { font-size: 0.82rem; color: var(--plum-1); font-weight: 700; }
.pal-group-n { font-size: 0.7rem; color: var(--plum-3); }
.pal-group-all {
  margin-left: auto;
  border: 1.5px solid var(--cream-4);
  background: #fff;
  border-radius: var(--radius-pill);
  font-size: 0.68rem; font-weight: 700;
  color: var(--plum-2);
  padding: 0.12rem 0.55rem;
  cursor: pointer;
  transition: all var(--transition-fast);
}
.pal-group-all:hover { border-color: var(--sakura); color: var(--sakura-deep); }

.pal-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(50px, 1fr));
  gap: 5px;
}
.pal-swatch {
  aspect-ratio: 1;
  border: 2px solid rgba(0,0,0,0.1);
  border-radius: var(--radius-sm);
  cursor: pointer;
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  gap: 1px;
  font-family: var(--font-mono);
  font-weight: 800;
  padding: 0;
  position: relative;
  transition: transform var(--transition-fast);
}
.pal-swatch:hover { transform: scale(1.1); z-index: 2; }
.pal-swatch.on {
  border-color: var(--sakura);
  box-shadow: 0 0 0 2px var(--sakura), 0 3px 8px var(--sakura-glow);
  z-index: 1;
}
.pal-sw-code { font-size: 0.66rem; line-height: 1; }
.pal-sw-check { font-size: 0.6rem; line-height: 1; }

/* footer */
.pal-foot {
  display: flex; align-items: center; gap: 0.55rem;
  margin-top: 0.85rem; padding-top: 0.75rem;
  border-top: 2px dashed var(--line-strong);
}
.pal-spacer { flex: 1; }
</style>
