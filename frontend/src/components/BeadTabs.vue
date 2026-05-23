<template>
  <div class="bead-tabs">
    <router-link to="/bead-studio" class="bead-tab"
                 :class="{ on: route.path === '/bead-studio' }">
      🧩 拼豆工坊
    </router-link>
    <router-link to="/bead-studio/cards" class="bead-tab"
                 :class="{ on: route.path === '/bead-studio/cards' }">
      🎨 MARD 色卡
    </router-link>
    <router-link to="/bead-studio/gallery" class="bead-tab"
                 :class="{ on: route.path === '/bead-studio/gallery' }">
      🖼️ 我的画廊
    </router-link>
  </div>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router'
const route = useRoute()
</script>

<style scoped>
.bead-tabs {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 0.25rem;
}
.bead-tab {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.4rem 1rem;
  border-radius: var(--radius-pill);
  font-family: var(--font-round);
  font-weight: 700;
  font-size: 0.84rem;
  color: var(--plum-2);
  background: #fff;
  border: 2px solid var(--cream-4);
  text-decoration: none;
  transition: all var(--transition-fast);
}
.bead-tab:hover {
  border-color: var(--sakura-light);
  color: var(--sakura-deep);
  transform: translateY(-1px);
}
.bead-tab.on {
  background: linear-gradient(180deg, var(--sakura), var(--sakura-deep));
  border-color: var(--sakura-deep);
  color: #fff;
  box-shadow: 0 3px 0 var(--sakura-deep), 0 5px 14px var(--sakura-glow);
}
</style>
