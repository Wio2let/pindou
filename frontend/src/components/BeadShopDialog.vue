<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal-card card">
      <div class="modal-head">
        <span class="modal-title">🛒 购买拼豆</span>
        <button class="modal-close" @click="$emit('close')">✕</button>
      </div>

      <div class="modal-body">
        <!-- Filter -->
        <label class="filter-inline">
          <input type="checkbox" v-model="filterUsed" />
          <span>仅显示包含图纸所用颜色的商品</span>
          <span class="mono filter-count" v-if="filterUsed">
            （{{ filteredItems.length }} / {{ SHOP_ITEMS.length }}）
          </span>
        </label>

        <!-- Platform tabs -->
        <div class="platform-tabs">
          <button v-for="p in PLATFORMS" :key="p.id"
                  class="plat-tab" :class="{ on: selectedPlatform === p.id }"
                  @click="selectedPlatform === p.id ? selectedPlatform = 'all' : selectedPlatform = p.id">
            {{ p.icon }} {{ p.label }}
          </button>
          <button class="plat-tab" :class="{ on: selectedPlatform === 'all' }"
                  @click="selectedPlatform = 'all'">全部</button>
        </div>

        <!-- Items -->
        <div class="shop-list">
          <div v-for="item in filteredItems" :key="item.id" class="shop-item">
            <div class="si-head">
              <span class="si-platform badge" :class="'badge-' + platformBadge(item.platform)">{{ item.platform }}</span>
              <span class="si-type badge badge-neutral">{{ typeLabel(item.type) }}</span>
              <span class="si-price mono">¥{{ item.price.toFixed(2) }}</span>
            </div>
            <div class="si-body">
              <div class="si-shop">{{ item.shopName }}</div>
              <div class="si-product">{{ item.productName }}</div>
              <div v-if="item.description" class="si-desc">{{ item.description }}</div>
              <div v-if="item.applicableCodes.length > 0 && item.applicableCodes.length < 50" class="si-codes">
                <span v-for="code in item.applicableCodes.slice(0, 12)" :key="code"
                      class="si-code-chip"
                      :style="{ background: mardColors[code]?.hex || '#ccc' }"
                      :title="`${code} ${mardColors[code]?.name || ''}`">{{ code }}</span>
                <span v-if="item.applicableCodes.length > 12" class="si-more">+{{ item.applicableCodes.length - 12 }} 色</span>
              </div>
            </div>
            <a class="btn btn-xs btn-primary si-link" :href="item.url" target="_blank" rel="noopener">
              去购买 →
            </a>
          </div>
          <div v-if="filteredItems.length === 0" class="shop-empty">
            没有匹配的商品
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { SHOP_ITEMS, PLATFORMS, filterByUsedColors, type ShopItem } from '../data/shopData'

const props = defineProps<{
  usedColors: Set<string>
  mardColors: Record<string, { name: string; hex: string; rgb: [number, number, number] }>
}>()

defineEmits<{ close: [] }>()

const filterUsed = ref(false)
const selectedPlatform = ref<string>('all')

const filteredItems = computed(() => {
  let items = filterUsed.value
    ? filterByUsedColors(SHOP_ITEMS, props.usedColors)
    : SHOP_ITEMS
  if (selectedPlatform.value !== 'all') {
    items = items.filter(i => i.platform === selectedPlatform.value)
  }
  return items
})

function platformBadge(p: string): string {
  const m: Record<string, string> = { 淘宝: 'warning', 天猫: 'danger', 拼多多: 'success', 京东: 'neutral' }
  return m[p] || 'neutral'
}
function typeLabel(t: ShopItem['type']): string {
  const m: Record<string, string> = { refill: '补充包', fullset: '全套', individual: '单颗', tool: '工具' }
  return m[t] || t
}
</script>

<style scoped>
.modal-overlay {
  position: fixed; inset: 0; background: rgba(74,54,69,0.35);
  display: flex; align-items: center; justify-content: center;
  z-index: 100; backdrop-filter: blur(4px);
}
.modal-card {
  width: min(600px, 92vw); max-height: 80vh; display: flex; flex-direction: column;
  padding: 1.25rem 1.5rem;
  animation: pop-in 0.3s cubic-bezier(0.34, 1.56, 0.64, 1) both;
}
.modal-head {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 0.75rem;
}
.modal-title { font-family: var(--font-display); font-size: 1.1rem; color: var(--plum-1); }
.modal-close { background: none; border: none; font-size: 1.2rem; cursor: pointer; color: var(--plum-3); }
.modal-close:hover { color: var(--plum-1); }
.modal-body { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 0.75rem; }

.filter-inline {
  display: flex; align-items: center; gap: 0.4rem;
  font-size: 0.8rem; color: var(--plum-2); cursor: pointer;
}
.filter-count { font-size: 0.7rem; color: var(--plum-3); }

.platform-tabs { display: flex; gap: 0.35rem; flex-wrap: wrap; }
.plat-tab {
  padding: 0.25rem 0.65rem; border: 2px solid var(--cream-4); border-radius: var(--radius-pill);
  background: #fff; font-size: 0.74rem; font-weight: 600; cursor: pointer;
  color: var(--plum-2); transition: all var(--transition-fast);
}
.plat-tab.on { border-color: var(--sakura); background: var(--sakura-glow); color: var(--sakura-deep); }
.plat-tab:hover:not(.on) { border-color: var(--sakura-light); }

.shop-list { display: flex; flex-direction: column; gap: 0.65rem; }
.shop-item {
  display: grid; grid-template-columns: 1fr auto; gap: 0.5rem;
  padding: 0.7rem 0.85rem; border: 1.5px solid var(--line-strong); border-radius: var(--radius-md);
  background: #fff; transition: all var(--transition-fast);
}
.shop-item:hover { border-color: var(--sakura-light); box-shadow: var(--shadow-soft); }
.si-head { display: flex; align-items: center; gap: 0.4rem; flex-wrap: wrap; }
.si-platform { font-size: 0.65rem; }
.si-type { font-size: 0.6rem; }
.si-price { margin-left: auto; font-size: 0.9rem; font-weight: 800; color: var(--bad); }
.si-body { display: flex; flex-direction: column; gap: 0.2rem; }
.si-shop { font-size: 0.72rem; font-weight: 700; color: var(--plum-2); }
.si-product { font-size: 0.84rem; color: var(--plum-1); }
.si-desc { font-size: 0.7rem; color: var(--plum-3); }
.si-codes { display: flex; gap: 2px; flex-wrap: wrap; margin-top: 0.2rem; }
.si-code-chip {
  font-size: 0.5rem; font-family: var(--font-mono); font-weight: 700;
  padding: 0.05rem 0.15rem; border-radius: 2px; border: 1px solid rgba(0,0,0,0.12);
  color: #000; text-shadow: 0 0 2px #fff;
}
.si-more { font-size: 0.6rem; color: var(--plum-3); padding-left: 0.2rem; }
.si-link { flex-shrink: 0; align-self: center; }
.shop-empty { text-align: center; color: var(--plum-3); padding: 2rem 0; font-size: 0.86rem; }
</style>
