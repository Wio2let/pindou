<template>
  <div class="mard-cards">
    <BeadTabs />

    <!-- Toolbar -->
    <div class="card toolbar-card">
      <div class="tier-pills">
        <button v-for="t in tiers" :key="t"
                class="tier-pill" :class="{ on: tier === t }"
                @click="tier = t">
          {{ t }} 色
        </button>
      </div>
      <div class="toolbar-right">
        <span class="count-tag mono">{{ tierColors.length }} 色</span>
        <input class="input search" v-model="query"
               placeholder="搜索色号 / 颜色名…" />
      </div>
    </div>

    <!-- Empty -->
    <div v-if="visibleGroups.length === 0" class="empty-state" style="margin-top:2rem;">
      <div class="empty-icon">🔍</div>
      <div class="empty-text">没有匹配的颜色</div>
    </div>

    <!-- Color groups -->
    <div v-for="grp in visibleGroups" :key="grp.key" class="card group-card">
      <div class="group-head">
        <span class="group-name">{{ grp.name }}</span>
        <span class="group-count mono">{{ grp.colors.length }}</span>
      </div>
      <div class="swatch-grid">
        <div v-for="c in grp.colors" :key="c.code" class="swatch"
             :title="`${c.code} ${c.name} ${c.hex}`">
          <div class="sw-color" :style="{ background: c.hex }">
            <span class="sw-kit" :class="`kit-${minKitFor.get(c.code)}`"
                  :title="`最小含此色套装：MARD ${minKitFor.get(c.code)} 色`">
              {{ minKitFor.get(c.code) }}
            </span>
          </div>
          <div class="sw-code mono">{{ c.code }}</div>
          <div class="sw-name">{{ c.name }}</div>
          <div class="sw-hex mono">{{ c.hex }}</div>
        </div>
      </div>
    </div>

    <p class="data-note">
      📕 MARD 官方色卡 263 色，套装档位：24 / 48 / 72 / 96 / 120 / 144 / 216 / 264 色累进套装。
      色块左上角标注该颜色首次出现的最小套装档位。
    </p>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import BeadTabs from '../components/BeadTabs.vue'
import { useHeartTrail } from '../composables/useHeartTrail'

// Same cursor-heart particle effect as the studio page
useHeartTrail()
import {
  MARD_COLORS, MARD_TIERS, MARD_GROUPS, TIER_LABELS, TIER_ORDER,
  type Tier, type BeadColor,
} from '../data/mardPalettes'

const tiers: Tier[] = TIER_ORDER
const tier = ref<Tier>('264')
const query = ref('')

// Compute which tier is the smallest one that contains each code (for badge display)
const minKitFor = computed(() => {
  const map = new Map<string, Tier>()
  for (const t of TIER_ORDER) {
    for (const code of MARD_TIERS[t]) {
      if (!map.has(code)) map.set(code, t)
    }
  }
  return map
})

// Colors of the selected tier
const tierColors = computed<BeadColor[]>(() =>
  MARD_TIERS[tier.value].map(c => MARD_COLORS[c]).filter(Boolean),
)

// Grouped by hue family, filtered by search query
const visibleGroups = computed(() => {
  const q = query.value.trim().toLowerCase()
  const codeSet = new Set(MARD_TIERS[tier.value])
  return MARD_GROUPS
    .map(grp => {
      const list = Object.values(MARD_COLORS)
        .filter(c => {
          if (!codeSet.has(c.code)) return false
          if (codePrefix(c.code) !== grp.key) return false
          if (q && !c.code.toLowerCase().includes(q)
               && !c.name.toLowerCase().includes(q)
               && !c.hex.toLowerCase().includes(q)) return false
          return true
        })
        .sort((a, b) => tierIndex(a.code) - tierIndex(b.code))
      return { key: grp.key, name: grp.name, colors: list }
    })
    .filter(g => g.colors.length > 0)
})

function codePrefix(code: string): string {
  const m = code.match(/^[A-Z]+/)
  return m ? m[0] : code
}
function tierIndex(code: string): number {
  return MARD_TIERS['264'].indexOf(code)
}
</script>

<style scoped>
.mard-cards { display: flex; flex-direction: column; gap: 1rem; }

.toolbar-card {
  padding: 0.7rem 1rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  flex-wrap: wrap;
}
.tier-pills { display: flex; gap: 0.4rem; }
.tier-pill {
  padding: 0.35rem 0.9rem;
  border-radius: var(--radius-pill);
  border: 2px solid var(--cream-4);
  background: #fff;
  font-family: var(--font-round);
  font-weight: 700;
  font-size: 0.8rem;
  color: var(--plum-2);
  cursor: pointer;
  transition: all var(--transition-fast);
}
.tier-pill:hover { border-color: var(--sakura-light); color: var(--sakura-deep); }
.tier-pill.on {
  background: var(--sakura);
  border-color: var(--sakura);
  color: #fff;
}
.toolbar-right { display: flex; align-items: center; gap: 0.6rem; }
.count-tag {
  font-size: 0.74rem;
  color: var(--plum-2);
  background: var(--cream-2);
  padding: 0.2rem 0.6rem;
  border-radius: var(--radius-pill);
}
.search { width: 200px; }

.group-card { padding: 0.85rem 1rem 1rem; }
.group-head {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.7rem;
}
.group-name {
  font-family: var(--font-display);
  font-size: 1.05rem;
  color: var(--plum-1);
}
.group-count {
  font-size: 0.7rem;
  color: var(--plum-3);
  background: var(--cream-2);
  padding: 0.1rem 0.5rem;
  border-radius: var(--radius-pill);
}

.swatch-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(86px, 1fr));
  gap: 0.6rem;
}
.swatch {
  border: 1.5px solid var(--line);
  border-radius: var(--radius-md);
  overflow: hidden;
  background: #fff;
  transition: transform var(--transition-fast), box-shadow var(--transition-fast);
}
.swatch:hover {
  transform: translateY(-3px);
  box-shadow: var(--shadow-soft);
  border-color: var(--sakura-light);
}
.sw-color {
  height: 58px;
  position: relative;
  display: flex;
  align-items: flex-start;
  justify-content: flex-end;
  gap: 2px;
  padding: 4px;
}
.sw-kit {
  font-size: 0.56rem;
  font-weight: 800;
  font-family: var(--font-mono);
  padding: 0.05rem 0.3rem;
  border-radius: var(--radius-pill);
  color: #fff;
  line-height: 1.4;
}
.kit-24  { background: rgba(232,  82,  82, 0.90); }
.kit-48  { background: rgba(232, 140,  50, 0.90); }
.kit-72  { background: rgba(200, 175,  30, 0.90); }
.kit-96  { background: rgba(100, 180,  70, 0.90); }
.kit-120 { background: rgba( 60, 175, 140, 0.90); }
.kit-144 { background: rgba( 60, 140, 200, 0.90); }
.kit-216 { background: rgba(110,  90, 200, 0.90); }
.kit-264 { background: rgba(160,  80, 180, 0.90); }
.sw-code {
  font-size: 0.74rem;
  font-weight: 700;
  color: var(--plum-1);
  padding: 0.25rem 0.4rem 0;
}
.sw-name {
  font-size: 0.68rem;
  color: var(--plum-2);
  padding: 0 0.4rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.sw-hex {
  font-size: 0.62rem;
  color: var(--plum-3);
  padding: 0.05rem 0.4rem 0.35rem;
}

.data-note {
  font-size: 0.74rem;
  color: var(--plum-3);
  line-height: 1.6;
  padding: 0.5rem 0.25rem;
}
.data-note code {
  font-family: var(--font-mono);
  background: var(--cream-2);
  padding: 0.05rem 0.35rem;
  border-radius: 4px;
}
</style>
