<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal-card card">
      <div class="modal-head">
        <span class="modal-title">📦 我的库存</span>
        <button class="modal-close" @click="$emit('close')">✕</button>
      </div>

      <div class="modal-body">
        <p class="intro">
          管理你手上所有的拼豆。「<b>＋</b>」一次加 {{ BULK }} 颗（默认一袋的量），
          「<b>－</b>」减 {{ BULK }} 颗，也能直接改数字。库存自动保存在本地。
        </p>

        <!-- Controls bar -->
        <div class="ctrl-bar">
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
        </div>

        <!-- Tier presets — one-click add a full kit (X colours × N each) -->
        <div class="tier-bar">
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

        <!-- Series filter — A/B/C/D/... chips -->
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

        <!-- Quick stats -->
        <div class="stats">
          <span class="stat-chip"><b>{{ ownedCount }}</b> 色已记录</span>
          <span class="stat-chip"><b>{{ totalBeads.toLocaleString() }}</b> 颗总数</span>
          <span class="stat-chip warn" v-if="lowCount > 0">
            ⚠ <b>{{ lowCount }}</b> 色低于阈值
          </span>
          <span class="stat-spacer"></span>
          <button class="btn btn-ghost btn-xs danger-text" @click="onClearAll"
                  title="把库存清零（不能撤销）">🗑 清空全部</button>
        </div>

        <!-- Color grid -->
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

      <div class="modal-foot">
        <span class="foot-hint">改动会自动保存到这台设备</span>
        <button class="btn btn-primary btn-sm" @click="$emit('close')">完成</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  MARD_COLORS, MARD_TIERS, TIER_ORDER, TIER_LABELS, MARD_GROUPS,
  type Tier,
} from '../data/mardPalettes'
import { useInventory, BULK } from '../composables/useInventory'

defineEmits<{ close: [] }>()

const { state, getCount, setCount, add, remove, clearAll, setThreshold } = useInventory()

const searchTerm = ref('')
const filter = ref<'all' | 'low' | 'owned'>('all')
const seriesFilter = ref<string>('')          // '' = all series; otherwise an A/B/C/... key
const tierPerColor = ref<number>(BULK)        // beads added per code when a tier preset is clicked

const allColors = computed(() => Object.entries(MARD_COLORS).map(([code, v]) => ({ code, ...v })))

// Only show series chips for keys that actually exist in MARD_COLORS.
const availableGroups = computed(() =>
  MARD_GROUPS.filter(g => allColors.value.some(c => c.code.startsWith(g.key)))
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

/** Add a tier preset to inventory — N beads per code in that tier, in one go. */
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
  } catch { return /* user cancelled */ }
  for (const code of codes) setCount(code, getCount(code) + per)
  ElMessage.success(`已加入 ${TIER_LABELS[tier]}：${codes.length} 色 × ${per} 颗`)
}

const ownedCount = computed(() => allColors.value.filter(c => getCount(c.code) > 0).length)
const totalBeads = computed(() =>
  Object.values(state.value.counts).reduce((s, n) => s + (n | 0), 0)
)
const lowCount = computed(() => allColors.value.filter(c => isLow(c.code)).length)

function textOn(hex: string): string {
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  return (r * 299 + g * 587 + b * 114) / 1000 > 145 ? '#000' : '#fff'
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
.modal-overlay {
  position: fixed; inset: 0; background: rgba(74,54,69,0.35);
  display: flex; align-items: center; justify-content: center;
  z-index: 100; backdrop-filter: blur(4px);
}
.modal-card {
  width: min(680px, 94vw); max-height: 88vh; display: flex; flex-direction: column;
  padding: 1.1rem 1.35rem 0.85rem;
  animation: pop-in 0.3s cubic-bezier(0.34, 1.56, 0.64, 1) both;
}
.modal-head {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 0.55rem;
}
.modal-title { font-family: var(--font-display); font-size: 1.1rem; color: var(--plum-1); }
.modal-close { background: none; border: none; font-size: 1.2rem; cursor: pointer; color: var(--plum-3); }
.modal-close:hover { color: var(--plum-1); }
.modal-body { flex: 1; overflow: hidden; display: flex; flex-direction: column; gap: 0.55rem; min-height: 0; }
.modal-foot {
  display: flex; align-items: center; gap: 0.5rem;
  padding-top: 0.55rem; border-top: 1.5px dashed var(--line-strong); margin-top: 0.35rem;
}
.foot-hint { font-size: 0.72rem; color: var(--plum-3); flex: 1; }

.intro { font-size: 0.78rem; color: var(--plum-2); margin: 0; line-height: 1.5; }
.intro b { color: var(--sakura-deep); font-family: var(--font-mono); }

.ctrl-bar {
  display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap;
  padding: 0.4rem 0.55rem; background: var(--cream-2);
  border: 1.5px dashed var(--line-strong); border-radius: var(--radius-md);
}
.ctrl-cell { display: flex; align-items: center; gap: 0.35rem; font-size: 0.74rem; color: var(--plum-2); }
.ctrl-label { font-weight: 700; }
.ctrl-num {
  width: 64px; padding: 0.15rem 0.4rem;
  border: 1.5px solid var(--cream-4); border-radius: var(--radius-sm);
  font-family: var(--font-mono); font-weight: 700; text-align: right;
  background: #fff; outline: none;
}
.ctrl-num:focus { border-color: var(--sakura); }
.ctrl-suffix { color: var(--plum-3); font-size: 0.72rem; }
.ctrl-spacer { flex: 1; }
.search {
  width: 160px;
  padding: 0.22rem 0.5rem; border: 1.5px solid var(--cream-4);
  border-radius: var(--radius-sm); font-size: 0.78rem; outline: none;
  background: #fff;
}
.search:focus { border-color: var(--sakura); }

/* tier-preset bar — one-click add a full kit */
.tier-bar {
  display: flex; align-items: center; gap: 0.45rem; flex-wrap: wrap;
  padding: 0.45rem 0.6rem; background: var(--sakura-glow);
  border: 1.5px dashed var(--sakura-light); border-radius: var(--radius-md);
}
.tier-label { font-size: 0.76rem; font-weight: 700; color: var(--plum-1); }
.tier-input-cell {
  display: inline-flex; align-items: center; gap: 0.25rem;
  background: #fff; border: 1.5px solid var(--cream-4);
  border-radius: var(--radius-sm); padding: 0.05rem 0.5rem;
  font-size: 0.74rem; color: var(--plum-2);
}
.ti-pre, .ti-suf { font-weight: 600; }
.tier-input {
  width: 58px; border: none; outline: none;
  font-family: var(--font-mono); font-weight: 700; text-align: right;
  background: transparent; color: var(--plum-1);
}
.tier-btns { display: flex; gap: 0.3rem; flex-wrap: wrap; }
.tier-btn {
  padding: 0.2rem 0.6rem; border: 1.5px solid var(--sakura);
  background: #fff; color: var(--sakura-deep);
  border-radius: var(--radius-pill);
  font-family: var(--font-mono); font-weight: 800; font-size: 0.74rem;
  cursor: pointer; transition: all var(--transition-fast);
}
.tier-btn:hover {
  background: var(--sakura); color: #fff;
  transform: translateY(-1px); box-shadow: 0 2px 0 var(--sakura-deep);
}

/* series filter chips */
.series-bar {
  display: flex; align-items: center; gap: 0.3rem; flex-wrap: wrap;
  font-size: 0.74rem;
}
.series-label { font-weight: 700; color: var(--plum-2); }
.series-chip {
  min-width: 1.85rem; padding: 0.2rem 0.55rem;
  border: 1.5px solid var(--cream-4); background: #fff;
  border-radius: var(--radius-pill);
  font-family: var(--font-mono); font-weight: 800; font-size: 0.72rem;
  color: var(--plum-2); cursor: pointer; transition: all var(--transition-fast);
}
.series-chip:hover:not(.on) { border-color: var(--sakura-light); color: var(--plum-1); }
.series-chip.on {
  background: var(--sakura); border-color: var(--sakura-deep);
  color: #fff; box-shadow: 0 2px 0 var(--sakura-deep);
}

.stats { display: flex; align-items: center; gap: 0.4rem; font-size: 0.74rem; flex-wrap: wrap; }
.stat-chip {
  background: #fff; border: 1.5px solid var(--line-strong);
  border-radius: var(--radius-pill); padding: 0.18rem 0.6rem; color: var(--plum-2);
}
.stat-chip b { font-family: var(--font-mono); color: var(--plum-1); }
.stat-chip.warn { background: var(--warn-glow); border-color: var(--warn); color: #c87b1f; }
.stat-chip.warn b { color: #c87b1f; }
.stat-spacer { flex: 1; }
.danger-text { color: var(--bad); }
.danger-text:hover { background: var(--bad-glow); }

.color-list {
  flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 3px;
  padding: 2px;
}
.inv-row {
  display: grid; grid-template-columns: auto 1fr auto auto auto auto;
  align-items: center; gap: 0.4rem;
  padding: 0.3rem 0.55rem; border: 1.5px solid var(--line-strong);
  border-radius: var(--radius-sm); background: #fff;
}
.inv-row.is-low { border-color: var(--warn); background: var(--warn-glow); }
.inv-row.is-zero { opacity: 0.55; }
.swatch {
  display: inline-flex; align-items: center; justify-content: center;
  min-width: 2.4rem; height: 1.5rem; padding: 0 0.4rem;
  border-radius: 5px; font-family: var(--font-mono); font-weight: 800;
  font-size: 0.7rem; border: 1.5px solid rgba(0,0,0,0.15);
}
.cname { font-size: 0.78rem; color: var(--plum-1); }
.step-btn {
  width: 1.7rem; height: 1.5rem;
  border: 1.5px solid var(--cream-4); background: #fff;
  border-radius: var(--radius-sm); cursor: pointer;
  font-weight: 800; color: var(--plum-1); font-size: 0.85rem;
  transition: all var(--transition-fast);
}
.step-btn:hover:not(:disabled) { border-color: var(--sakura); background: var(--sakura-glow); }
.step-btn:disabled { opacity: 0.35; cursor: not-allowed; }
.step-btn.minus { color: var(--bad); }
.step-btn.plus { color: var(--ok); }
.qty {
  width: 72px; padding: 0.15rem 0.4rem;
  border: 1.5px solid var(--cream-4); border-radius: var(--radius-sm);
  font-family: var(--font-mono); font-weight: 700; text-align: right;
  background: #fff; outline: none;
}
.qty:focus { border-color: var(--sakura); }
.row-tag {
  font-size: 0.62rem; font-weight: 800; padding: 0.1rem 0.4rem;
  border-radius: var(--radius-pill); background: var(--warn-glow); color: #c87b1f;
  border: 1px solid var(--warn);
}
.row-tag.empty {
  background: var(--cream-2); color: var(--plum-3); border-color: var(--line-strong);
}
.empty { text-align: center; padding: 1.5rem 0; color: var(--plum-3); font-size: 0.85rem; }
</style>
