<template>
  <div class="shell">
    <aside class="rail">
      <router-link to="/bead-studio" class="brand">
        <span class="brand-mark" aria-hidden="true">
          <svg viewBox="0 0 60 60" width="42" height="42">
            <g fill="#ff6b9d">
              <ellipse cx="30" cy="14" rx="7" ry="10" />
              <ellipse cx="46" cy="22" rx="7" ry="10" transform="rotate(72 46 22)" />
              <ellipse cx="42" cy="42" rx="7" ry="10" transform="rotate(144 42 42)" />
              <ellipse cx="18" cy="42" rx="7" ry="10" transform="rotate(216 18 42)" />
              <ellipse cx="14" cy="22" rx="7" ry="10" transform="rotate(288 14 22)" />
              <circle cx="30" cy="30" r="5" fill="#ffd76b" />
            </g>
          </svg>
        </span>
        <span class="brand-text">
          <span class="brand-zh">拼豆</span>
          <span class="brand-en">Bead Studio</span>
        </span>
      </router-link>

      <div class="rail-label">BEAD MENU</div>

      <nav class="rail-nav">
        <router-link
          v-for="item in navItems"
          :key="item.to"
          :to="item.to"
          class="rail-item"
          :class="{ active: isActive(item) }"
        >
          <span class="rail-icon">{{ item.icon }}</span>
          <span class="rail-name">
            <span class="rail-zh">{{ item.zh }}</span>
            <span class="rail-en">{{ item.en }}</span>
          </span>
          <span v-if="isActive(item)" class="rail-heart">♥</span>
        </router-link>
      </nav>

      <div class="rail-foot">
        <div class="status-pill">
          <span class="status-dot"></span>
          <span>
            <strong>本地体验</strong>
            <em>{{ todayLabel }}</em>
          </span>
        </div>
      </div>
    </aside>

    <main class="main">
      <div class="masthead">
        <div class="masthead-left">
          <span class="masthead-tag">{{ sectionLabel }}</span>
          <span class="masthead-dot">·</span>
          <span class="mono tabular text-dim">{{ todayLong }}</span>
        </div>
        <div class="masthead-right">
          <span class="live-pill">
            <span class="live-dot"></span>
            BEAD
          </span>
        </div>
      </div>

      <header class="hero">
        <div class="hero-eyebrow">
          <span>{{ sectionLabel }}</span>
        </div>
        <h1 class="hero-title">
          <span class="hero-title-main">{{ pageTitle.zh }}</span>
          <span class="hero-title-sub">{{ pageTitle.en }}</span>
        </h1>
        <div class="hero-deco">
          <span class="deco-line"></span>
          <span class="deco-star">✦</span>
          <span class="deco-line"></span>
        </div>
      </header>

      <router-view v-slot="{ Component }">
        <keep-alive :include="['BeadStudio']">
          <component :is="Component" />
        </keep-alive>
      </router-view>
    </main>

    <div class="rockets" v-show="showRockets">
      <button v-show="canScrollUp" class="rocket" @click="scrollToTop" title="回到顶部">
        ↑
      </button>
      <button v-show="canScrollDown" class="rocket" @click="scrollToBottom" title="到达底部">
        ↓
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

interface NavItem {
  to: string
  zh: string
  en: string
  icon: string
  match: (path: string) => boolean
}

const navItems: NavItem[] = [
  { to: '/bead-studio', zh: '拼豆工坊', en: 'Studio', icon: '◇', match: (p) => p === '/bead-studio' },
  { to: '/bead-studio/cards', zh: 'MARD 色卡', en: 'Palette', icon: '▣', match: (p) => p === '/bead-studio/cards' },
]

function isActive(item: NavItem): boolean {
  return item.match(route.path)
}

const pageTitle = computed(() => {
  if (route.path === '/bead-studio/cards') {
    return { zh: 'MARD 色卡', en: 'Palette Cards' }
  }
  return { zh: '图像拼豆', en: 'Bead Studio' }
})

const sectionLabel = computed(() =>
  route.path === '/bead-studio/cards' ? 'Palette' : 'Studio',
)

const todayLabel = computed(() => {
  const d = new Date()
  return `${d.getFullYear()}/${String(d.getMonth() + 1).padStart(2, '0')}/${String(d.getDate()).padStart(2, '0')}`
})

const todayLong = computed(() => {
  const d = new Date()
  const wd = ['日', '一', '二', '三', '四', '五', '六'][d.getDay()]
  return `周${wd} · ${todayLabel.value}`
})

const scrollY = ref(0)
const docHeight = ref(0)
const winHeight = ref(0)
const showRockets = computed(() => docHeight.value > winHeight.value + 200)
const canScrollUp = computed(() => scrollY.value > 200)
const canScrollDown = computed(() => scrollY.value + winHeight.value < docHeight.value - 200)

function onScroll() {
  scrollY.value = window.scrollY || document.documentElement.scrollTop
  docHeight.value = document.documentElement.scrollHeight
  winHeight.value = window.innerHeight
}

function scrollToTop() {
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

function scrollToBottom() {
  window.scrollTo({ top: document.documentElement.scrollHeight, behavior: 'smooth' })
}

onMounted(() => {
  onScroll()
  window.addEventListener('scroll', onScroll, { passive: true })
  window.addEventListener('resize', onScroll)
})

onBeforeUnmount(() => {
  window.removeEventListener('scroll', onScroll)
  window.removeEventListener('resize', onScroll)
})
</script>

<style scoped>
.shell {
  display: grid;
  grid-template-columns: 240px 1fr;
  min-height: 100vh;
}

.rail {
  position: sticky;
  top: 0;
  z-index: 10;
  display: flex;
  flex-direction: column;
  height: 100vh;
  padding: 1.5rem 1.1rem 1.25rem;
  overflow: hidden;
  background: linear-gradient(180deg, #fff9fb 0%, #fff5f0 60%, #fef0e8 100%);
  border-right: 2px solid var(--line);
  box-shadow: 4px 0 24px rgba(255, 107, 157, 0.06);
}

.brand {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.5rem 0.4rem 1.1rem;
  color: inherit;
  text-decoration: none;
}

.brand-mark {
  display: inline-flex;
  filter: drop-shadow(0 4px 8px rgba(255, 107, 157, 0.35));
}

.brand-text,
.rail-name,
.status-pill span {
  display: flex;
  flex-direction: column;
}

.brand-zh {
  font-family: var(--font-display);
  font-size: 1.55rem;
  color: var(--plum-1);
  letter-spacing: 0.06em;
}

.brand-en {
  margin-top: 0.15rem;
  font-family: var(--font-round);
  font-size: 0.7rem;
  font-weight: 700;
  color: var(--sakura);
  letter-spacing: 0.12em;
}

.rail-label {
  margin: 0.5rem 0 0.8rem;
  font-family: var(--font-display);
  font-size: 0.84rem;
  color: var(--sakura);
  text-align: center;
  letter-spacing: 0.18em;
}

.rail-nav {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.rail-item {
  display: grid;
  grid-template-columns: 32px 1fr 18px;
  gap: 0.5rem;
  align-items: center;
  padding: 0.7rem 0.85rem;
  color: var(--plum-2);
  text-decoration: none;
  border: 2px solid transparent;
  border-radius: var(--radius-md);
  transition: all var(--transition-fast);
}

.rail-item:hover {
  color: var(--plum-1);
  background: #fff;
  border-color: var(--sakura-light);
  transform: translateX(2px);
}

.rail-item.active {
  color: var(--plum-1);
  background: linear-gradient(135deg, #ffe6ef, #fff0f5);
  border-color: var(--sakura);
  box-shadow: 0 4px 14px var(--sakura-glow);
}

.rail-icon {
  font-size: 1.2rem;
  color: var(--sakura);
}

.rail-zh {
  font-family: var(--font-display);
  font-size: 1.05rem;
  letter-spacing: 0.04em;
}

.rail-en {
  margin-top: 0.1rem;
  font-family: var(--font-round);
  font-size: 0.68rem;
  font-weight: 600;
  color: var(--plum-3);
  letter-spacing: 0.05em;
}

.rail-heart {
  color: var(--sakura);
}

.rail-foot {
  margin-top: auto;
  padding-top: 1rem;
}

.status-pill {
  display: flex;
  gap: 0.65rem;
  align-items: center;
  padding: 0.7rem 0.85rem;
  background: #fff;
  border: 2px solid var(--sakura-light);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-soft);
}

.status-dot {
  width: 0.7rem;
  height: 0.7rem;
  background: var(--ok);
  border-radius: 999px;
  box-shadow: 0 0 8px var(--ok);
}

.status-pill strong {
  font-family: var(--font-display);
  font-size: 0.92rem;
  color: var(--sakura-deep);
  font-style: normal;
}

.status-pill em {
  margin-top: 0.1rem;
  font-size: 0.7rem;
  color: var(--plum-3);
  font-style: normal;
}

.main {
  position: relative;
  z-index: 2;
  width: 100%;
  min-width: 0;
  padding: 1.75rem 2.5rem 4rem;
}

.masthead {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.65rem 1.1rem;
  margin-bottom: 1.4rem;
  font-size: 0.78rem;
  background: #fff;
  border: 2px dashed var(--sakura-light);
  border-radius: var(--radius-pill);
  box-shadow: var(--shadow-soft);
}

.masthead-left,
.masthead-right,
.live-pill,
.hero-eyebrow,
.hero-deco {
  display: flex;
  align-items: center;
}

.masthead-left,
.masthead-right {
  gap: 0.55rem;
}

.masthead-tag {
  padding: 0.15rem 0.7rem;
  font-family: var(--font-round);
  font-size: 0.72rem;
  font-weight: 700;
  color: #fff;
  background: var(--sakura);
  border-radius: var(--radius-pill);
  letter-spacing: 0.05em;
}

.masthead-dot {
  color: var(--sakura-light);
}

.live-pill {
  gap: 0.4rem;
  padding: 0.18rem 0.7rem;
  font-family: var(--font-round);
  font-size: 0.7rem;
  font-weight: 700;
  color: var(--ok);
  background: var(--ok-glow);
  border: 1.5px solid var(--ok);
  border-radius: var(--radius-pill);
  letter-spacing: 0.1em;
}

.live-dot {
  width: 7px;
  height: 7px;
  background: var(--ok);
  border-radius: 50%;
  box-shadow: 0 0 8px var(--ok);
}

.hero {
  margin-bottom: 2rem;
  text-align: center;
}

.hero-eyebrow {
  display: inline-flex;
  gap: 0.4rem;
  padding: 0.25rem 0.85rem;
  margin-bottom: 0.85rem;
  font-family: var(--font-round);
  font-size: 0.74rem;
  font-weight: 700;
  color: #6b4f96;
  background: var(--lavender-glow);
  border: 1.5px solid var(--lavender);
  border-radius: var(--radius-pill);
  letter-spacing: 0.05em;
}

.hero-title {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  align-items: center;
  line-height: 1;
}

.hero-title-main {
  font-family: var(--font-display);
  font-size: clamp(2.4rem, 4.5vw, 3.6rem);
  color: var(--plum-1);
  letter-spacing: 0.04em;
  text-shadow: 0 2px 0 var(--sakura-light), 0 6px 22px rgba(255, 107, 157, 0.18);
}

.hero-title-sub {
  margin-top: 0.35rem;
  font-family: var(--font-round);
  font-size: clamp(0.9rem, 1.5vw, 1.1rem);
  font-weight: 700;
  color: var(--sakura);
  text-transform: uppercase;
  letter-spacing: 0.12em;
}

.hero-deco {
  justify-content: center;
  gap: 0.5rem;
  margin-top: 1rem;
}

.deco-line {
  width: 60px;
  height: 1px;
  background: repeating-linear-gradient(90deg, var(--sakura-light) 0 4px, transparent 4px 8px);
}

.deco-star {
  font-size: 1.1rem;
  color: var(--sakura);
}

.rockets {
  position: fixed;
  right: 1.6rem;
  bottom: 1.6rem;
  z-index: 50;
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
}

.rocket {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  font-size: 1.25rem;
  color: var(--sakura-deep);
  cursor: pointer;
  background: linear-gradient(180deg, #fff, var(--cream-2));
  border: 2px solid var(--sakura);
  border-radius: 50%;
  box-shadow: 0 4px 18px var(--sakura-glow), 0 2px 0 var(--sakura-light);
  transition: transform var(--transition-fast), box-shadow var(--transition-fast);
}

.rocket:hover {
  border-color: var(--sakura-deep);
  box-shadow: 0 10px 26px var(--sakura-ring), 0 3px 0 var(--sakura);
  transform: translateY(-3px) scale(1.06);
}

@media (max-width: 900px) {
  .shell {
    grid-template-columns: 1fr;
  }

  .rail {
    position: static;
    height: auto;
  }
}

@media (max-width: 720px) {
  .main {
    padding: 1.25rem;
  }

  .masthead {
    align-items: flex-start;
    flex-direction: column;
    gap: 0.6rem;
    border-radius: var(--radius-md);
  }

  .rockets {
    right: 0.9rem;
    bottom: 0.9rem;
  }

  .rocket {
    width: 42px;
    height: 42px;
  }
}
</style>
