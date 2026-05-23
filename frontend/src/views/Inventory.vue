<template>
  <div class="page">
    <BeadTabs />

    <div class="header card">
      <div class="head-left">
        <span class="title">📦 我的库存</span>
        <span class="sub">
          {{ auth.user.value
            ? `登录账号下的库存会自动云端同步，换设备登录也能继续用`
            : '现在没登录 · 库存只存在这台设备上，登录后会自动云端同步' }}
        </span>
      </div>
      <div class="head-right">
        <span class="stat-chip"><b>{{ ownedCount }}</b> 色</span>
        <span class="stat-chip"><b>{{ totalBeads.toLocaleString() }}</b> 颗</span>
        <span class="stat-chip warn" v-if="lowCount > 0">⚠ <b>{{ lowCount }}</b> 色缺货</span>
      </div>
    </div>

    <!-- Controls bar -->
    <div class="card ctrl-card">
      <label class="ctrl-cell">
        <span class="ctrl-label">提醒阈值</span>
        <input type="number" min="0" step="10" class="ctrl-num"
               :value="state.threshold"
               @input="setThreshold(($event.target as HTMLInputElement).valueAsNumber)" />
        <span class="ctrl-suffix">颗以下提醒补货</span>
      </label>
      <span class="ctrl-spacer"></span>
      <button class="btn btn-ghost btn-xs" @click="filter = filter === 'low' ? 'all' : 'low'">
        {{ filter === 'low' ? '✓ 仅看缺货' : '⚠ 仅看缺货' }}
      </button>
      <button class="btn btn-ghost btn-xs" @click="filter = filter === 'owned' ? 'all' : 'owned'">
        {{ filter === 'owned' ? '✓ 仅看已有' : '📦 仅看已有' }}
      </button>
      <input type="text" v-model="searchTerm" class="search"
             placeholder="搜色号/名称…" />
      <button class="btn btn-ghost btn-xs danger-text" @click="onClearAll"
              title="把库存清零（不能撤销）">🗑 清空</button>
    </div>

    <!-- Tier presets -->
    <div class="card tier-card">
      <span class="tier-label">套装一键加：</span>
      <span class="tier-input-cell">
        <span class="ti-pre">每色</span>
        <input type="number" min="1" step="50" class="tier-input"
               v-model.number="tierPerColor" />
        <span class="ti-suf">颗</span>
      </span>
      <div class="tier-btns">
        <button v-for="t in TIER_ORDER" :key="t"
                class="tier-btn" @click="addTier(t)"
                :title="`给 ${TIER_LABELS[t]}（${MARD_TIERS[t].length} 色）每色加 ${tierPerColor} 颗`">
          {{ t }} 色
        </button>
      </div>
    </div>

    <!-- Series filter -->
    <div class="series-bar">
      <span class="series-label">按系列：</span>
      <button class="series-chip" :class="{ on: seriesFilter === '' }"
              @click="seriesFilter = ''">全部</button>
      <button v-for="g in availableGroups" :key="g.key"
              class="series-chip" :class="{ on: seriesFilter === g.key }"
              :title="g.name"
              @click="seriesFilter = seriesFilter === g.key ? '' : g.key">
        {{ g.key }}
      </button>
    </div>

    <!-- Colour grid -->
    <div class="card color-card">
      <div class="color-list">
        <div v-for="c in filteredColors" :key="c.code" class="inv-row"
             :class="{ 'is-low': isLow(c.code), 'is-zero': getCount(c.code) === 0 }">
          <span class="swatch" :style="{ background: c.hex, color: textOn(c.hex) }">{{ c.code }}</span>
          <span class="cname">{{ c.name }}</span>
          <button class="step-btn minus" @click="remove(c.code)"
                  :disabled="getCount(c.code) === 0"
                  :title="`减 ${BULK} 颗`">－</button>
          <input type="number" min="0" step="1" class="qty"
                 :value="getCount(c.code)"
                 @input="setCount(c.code, ($event.target as HTMLInputElement).valueAsNumber || 0)" />
          <button class="step-btn plus" @click="add(c.code)" :title="`加 ${BULK} 颗`">＋</button>
          <span class="row-tag" v-if="isLow(c.code) && getCount(c.code) > 0">缺货</span>
          <span class="row-tag empty" v-else-if="getCount(c.code) === 0">未拥有</span>
        </div>
        <div v-if="filteredColors.length === 0" class="empty">没有匹配的色号</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import BeadTabs from '../components/BeadTabs.vue'
import {
  MARD_COLORS, MARD_TIERS, TIER_ORDER, TIER_LABELS, MARD_GROUPS,
  type Tier,
} from '../data/mardPalettes'
import { useInventory, BULK } from '../composables/useInventory'
import { useAuth } from '../composables/useAuth'
import { useHeartTrail } from '../composables/useHeartTrail'

useHeartTrail()

const { state, getCount, setCount, add, remove, clearAll, setThreshold } = useInventory()
const auth = useAuth()

const searchTerm = ref('')
const filter = ref<'all' | 'low' | 'owned'>('all')
const seriesFilter = ref<string>('')
const tierPerColor = ref<number>(BULK)

const allColors = computed(() => Object.entries(MARD_COLORS).map(([code, v]) => ({ code, ...v })))

const availableGroups = computed(() =>
  MARD_GROUPS.filter(g => allColors.value.some(c => c.code.startsWith(g.key))),
)

function isLow(code: string): boolean {
  const c = getCount(code)
  return c > 0 && c < state.value.threshold
}

const filteredColors = computed(() => {
  const q = searchTerm.value.trim().toLowerCase()
  const series = seriesFilter.value
  return allColors.value.filter(c => {
    if (series && !c.code.startsWith(series)) return false
    if (q && !c.code.toLowerCase().includes(q) && !c.name.toLowerCase().includes(q)) return false
    if (filter.value === 'low') return isLow(c.code)
    if (filter.value === 'owned') return getCount(c.code) > 0
    return true
  })
})

const ownedCount = computed(() => allColors.value.filter(c => getCount(c.code) > 0).length)
const totalBeads = computed(() =>
  Object.values(state.value.counts).reduce((s, n) => s + (n | 0), 0),
)
const lowCount = computed(() => allColors.value.filter(c => isLow(c.code)).length)

function textOn(hex: string): string {
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  return (r * 299 + g * 587 + b * 114) / 1000 > 145 ? '#000' : '#fff'
}

async function addTier(tier: Tier) {
  const codes = MARD_TIERS[tier]
  const per = Math.max(1, Math.floor(Number(tierPerColor.value)) || BULK)
  try {
    await ElMessageBox.confirm(
      `给「${TIER_LABELS[tier]}」的 ${codes.length} 个色号每色加 ${per} 颗？\n` +
      `总共 +${(codes.length * per).toLocaleString()} 颗`,
      '加套装到库存',
      { confirmButtonText: '加入', cancelButtonText: '取消', type: 'info' },
    )
  } catch { return }
  for (const code of codes) setCount(code, getCount(code) + per)
  ElMessage.success(`已加入 ${TIER_LABELS[tier]}：${codes.length} 色 × ${per} 颗`)
}

async function onClearAll() {
  try {
    await ElMessageBox.confirm('清空所有库存数量？这个操作不能撤销。', '清空库存', {
      confirmButtonText: '清空',
      cancelButtonText: '取消',
      type: 'warning',
    })
    clearAll()
  } catch { /* cancelled */ }
}
</script>

<style scoped>
.page { padding: 1rem 1.2rem; max-width: 1300px; margin: 0 auto; }

.header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0.9rem 1.2rem; margin-bottom: 0.9rem; gap: 0.8rem; flex-wrap: wrap;
}
.head-left { display: flex; flex-direction: column; gap: 0.15rem; }
.title { font-family: var(--font-display); font-size: 1.3rem; color: var(--plum-1); }
.sub { font-size: 0.78rem; color: var(--plum-3); }
.head-right { display: flex; align-items: center; gap: 0.5rem; }
.stat-chip {
  background: var(--cream-2); border: 1.5px solid var(--line-strong);
  border-radius: var(--radius-pill); padding: 0.2rem 0.65rem;
  font-size: 0.74rem; color: var(--plum-2);
}
.stat-chip b { color: var(--sakura-deep); font-family: var(--font-mono); }
.stat-chip.warn { background: var(--warn-glow); border-color: var(--warn); color: #c87b1f; }
.stat-chip.warn b { color: #c87b1f; }

.ctrl-card {
  padding: 0.6rem 0.9rem; margin-bottom: 0.7rem;
  display: flex; align-items: center; gap: 0.55rem; flex-wrap: wrap;
}
.ctrl-cell { display: flex; align-items: center; gap: 0.35rem; font-size: 0.78rem; color: var(--plum-2); }
.ctrl-label { font-weight: 700; }
.ctrl-num {
  width: 68px; padding: 0.2rem 0.45rem;
  border: 1.5px solid var(--cream-4); border-radius: var(--radius-sm);
  font-family: var(--font-mono); font-weight: 700; text-align: right;
  background: #fff; outline: none;
}
.ctrl-num:focus { border-color: var(--sakura); }
.ctrl-suffix { color: var(--plum-3); font-size: 0.74rem; }
.ctrl-spacer { flex: 1; }
.search {
  width: 200px;
  padding: 0.3rem 0.55rem; border: 1.5px solid var(--cream-4);
  border-radius: var(--radius-sm); font-size: 0.82rem; outline: none;
  background: #fff;
}
.search:focus { border-color: var(--sakura); }
.danger-text { color: var(--bad); }
.danger-text:hover { background: var(--bad-glow); }

.tier-card {
  padding: 0.55rem 0.9rem; margin-bottom: 0.7rem;
  background: var(--sakura-glow);
  border: 1.5px dashed var(--sakura-light);
  display: flex; align-items: center; gap: 0.55rem; flex-wrap: wrap;
}
.tier-label { font-size: 0.8rem; font-weight: 700; color: var(--plum-1); }
.tier-input-cell {
  display: inline-flex; align-items: center; gap: 0.25rem;
  background: #fff; border: 1.5px solid var(--cream-4);
  border-radius: var(--radius-sm); padding: 0.05rem 0.55rem;
  font-size: 0.78rem; color: var(--plum-2);
}
.ti-pre, .ti-suf { font-weight: 600; }
.tier-input {
  width: 64px; border: none; outline: none;
  font-family: var(--font-mono); font-weight: 700; text-align: right;
  background: transparent; color: var(--plum-1);
}
.tier-btns { display: flex; gap: 0.35rem; flex-wrap: wrap; }
.tier-btn {
  padding: 0.25rem 0.7rem; border: 1.5px solid var(--sakura);
  background: #fff; color: var(--sakura-deep);
  border-radius: var(--radius-pill);
  font-family: var(--font-mono); font-weight: 800; font-size: 0.78rem;
  cursor: pointer; transition: all var(--transition-fast);
}
.tier-btn:hover {
  background: var(--sakura); color: #fff;
  transform: translateY(-1px); box-shadow: 0 2px 0 var(--sakura-deep);
}

.series-bar {
  display: flex; align-items: center; gap: 0.3rem; flex-wrap: wrap;
  font-size: 0.78rem; margin-bottom: 0.6rem;
}
.series-label { font-weight: 700; color: var(--plum-2); }
.series-chip {
  min-width: 1.85rem; padding: 0.22rem 0.6rem;
  border: 1.5px solid var(--cream-4); background: #fff;
  border-radius: var(--radius-pill);
  font-family: var(--font-mono); font-weight: 800; font-size: 0.74rem;
  color: var(--plum-2); cursor: pointer; transition: all var(--transition-fast);
}
.series-chip:hover:not(.on) { border-color: var(--sakura-light); color: var(--plum-1); }
.series-chip.on {
  background: var(--sakura); border-color: var(--sakura-deep);
  color: #fff; box-shadow: 0 2px 0 var(--sakura-deep);
}

.color-card { padding: 0.7rem 0.9rem; }
.color-list { display: flex; flex-direction: column; gap: 3px; }
.inv-row {
  display: grid; grid-template-columns: auto 1fr auto auto auto auto;
  align-items: center; gap: 0.4rem;
  padding: 0.32rem 0.55rem; border: 1.5px solid var(--line-strong);
  border-radius: var(--radius-sm); background: #fff;
}
.inv-row.is-low { border-color: var(--warn); background: var(--warn-glow); }
.inv-row.is-zero { opacity: 0.6; }
.swatch {
  display: inline-flex; align-items: center; justify-content: center;
  min-width: 2.5rem; height: 1.55rem; padding: 0 0.45rem;
  border-radius: 5px; font-family: var(--font-mono); font-weight: 800;
  font-size: 0.72rem; border: 1.5px solid rgba(0,0,0,0.15);
}
.cname { font-size: 0.82rem; color: var(--plum-1); }
.step-btn {
  width: 1.8rem; height: 1.6rem;
  border: 1.5px solid var(--cream-4); background: #fff;
  border-radius: var(--radius-sm); cursor: pointer;
  font-weight: 800; color: var(--plum-1); font-size: 0.9rem;
  transition: all var(--transition-fast);
}
.step-btn:hover:not(:disabled) { border-color: var(--sakura); background: var(--sakura-glow); }
.step-btn:disabled { opacity: 0.35; cursor: not-allowed; }
.step-btn.minus { color: var(--bad); }
.step-btn.plus { color: var(--ok); }
.qty {
  width: 80px; padding: 0.18rem 0.45rem;
  border: 1.5px solid var(--cream-4); border-radius: var(--radius-sm);
  font-family: var(--font-mono); font-weight: 700; text-align: right;
  background: #fff; outline: none;
}
.qty:focus { border-color: var(--sakura); }
.row-tag {
  font-size: 0.64rem; font-weight: 800; padding: 0.12rem 0.45rem;
  border-radius: var(--radius-pill); background: var(--warn-glow); color: #c87b1f;
  border: 1px solid var(--warn);
}
.row-tag.empty {
  background: var(--cream-2); color: var(--plum-3); border-color: var(--line-strong);
}
.empty { text-align: center; padding: 1.5rem 0; color: var(--plum-3); font-size: 0.85rem; }
</style>
