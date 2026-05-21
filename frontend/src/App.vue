<template>
  <div class="shell" :class="{ compact: isCompact }">
    <!-- Left rail — kawaii sidebar -->
    <aside class="rail">
      <router-link to="/" class="brand">
        <span class="brand-blossom">
          <svg viewBox="0 0 60 60" width="42" height="42" aria-hidden="true">
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
        <div class="brand-text">
          <span class="brand-zh">樱花辑</span>
          <span class="brand-en">XHS Monitor</span>
        </div>
      </router-link>

      <div class="rail-label">★ 菜单 / MENU ★</div>

      <nav class="rail-nav">
        <router-link v-for="item in navItems" :key="item.to"
          :to="item.to"
          class="rail-item"
          :class="{ active: isActive(item) }">
          <span class="rail-emoji">{{ item.emoji }}</span>
          <span class="rail-name">
            <span class="rail-zh">{{ item.zh }}</span>
            <span class="rail-en">{{ item.en }}</span>
          </span>
          <span v-if="isActive(item)" class="rail-heart">♥</span>
        </router-link>
      </nav>

      <div class="rail-foot">
        <div class="status-pill" :class="loginStatus ? 'is-ok' : 'is-off'">
          <span class="status-emoji">{{ loginStatus ? '🌸' : '💤' }}</span>
          <div class="status-text">
            <div class="status-title">{{ loginStatus ? '已登录啦~' : '尚未登录' }}</div>
            <div class="status-sub mono">{{ todayLabel }}</div>
          </div>
        </div>
      </div>
    </aside>

    <!-- Main column -->
    <main class="main" :class="{ compact: isCompact }">
      <!-- Cute masthead strip -->
      <div class="masthead">
        <div class="masthead-left">
          <span class="masthead-tag">{{ sectionLabel }}</span>
          <span class="masthead-dot">·</span>
          <span class="mono tabular text-dim">{{ todayLong }}</span>
        </div>
        <div class="masthead-right">
          <span class="live-pill" :class="{ off: !loginStatus }">
            <span class="live-dot"></span>
            {{ loginStatus ? 'LIVE' : 'OFFLINE' }}
          </span>
        </div>
      </div>

      <!-- Hero — hidden in compact (full-screen) pages -->
      <header v-if="!isCompact" class="hero">
        <div class="hero-eyebrow">
          <span class="hero-emoji">{{ pageTitle.emoji }}</span>
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

      <router-view />
    </main>

    <!-- Floating rocket scroll buttons -->
    <div class="rockets" v-show="showRockets && !isCompact">
      <button v-show="canScrollUp"
              class="rocket rocket-up"
              @click="scrollToTop"
              title="一键回顶">
        <span class="rocket-emoji">🚀</span>
        <span class="rocket-flame"></span>
      </button>
      <button v-show="canScrollDown"
              class="rocket rocket-down"
              @click="scrollToBottom"
              title="一键到底">
        <span class="rocket-emoji">🚀</span>
        <span class="rocket-flame"></span>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onBeforeUnmount, ref } from 'vue'
import { useRoute } from 'vue-router'
import axios from 'axios'

const route = useRoute()
const loginStatus = ref(false)

// ---- Scroll-to-top / bottom rockets ----
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
function scrollToTop()    { window.scrollTo({ top: 0, behavior: 'smooth' }) }
function scrollToBottom() { window.scrollTo({ top: document.documentElement.scrollHeight, behavior: 'smooth' }) }

interface NavItem { to: string; zh: string; en: string; emoji: string; match?: (path: string) => boolean }

const navItems: NavItem[] = [
  { to: '/', zh: '看板', en: 'Dashboard', emoji: '🏠', match: (p) => p === '/' },
  { to: '/tasks', zh: '任务', en: 'Tasks', emoji: '📋', match: (p) => p.startsWith('/tasks') && p !== '/tasks/create' },
  { to: '/tasks/create', zh: '新建', en: 'New', emoji: '✨', match: (p) => p === '/tasks/create' },
  { to: '/favorites', zh: '收藏', en: 'Favorites', emoji: '💝', match: (p) => p.startsWith('/favorites') },
  { to: '/bead-studio', zh: '拼豆', en: 'Bead Studio', emoji: '🧩', match: (p) => p.startsWith('/bead-studio') },
  { to: '/bilibili', zh: 'B 站', en: 'Bilibili', emoji: '📺', match: (p) => p === '/bilibili' },
]

function isActive(item: NavItem): boolean {
  return item.match ? item.match(route.path) : route.path === item.to
}

// Compact = full-viewport, no page scroll. Used by the task-detail page
// where the post / comment panels scroll internally instead.
const isCompact = computed(() => {
  const p = route.path
  return p.startsWith('/tasks/')
    && p !== '/tasks/create'
    && !p.endsWith('/edit')
    && !p.endsWith('/search')
})

const pageTitle = computed(() => {
  const path = route.path
  if (path === '/') return { zh: '总览看板', en: 'Overview', emoji: '🌸' }
  if (path === '/tasks') return { zh: '任务列表', en: 'All Tasks', emoji: '🎀' }
  if (path === '/tasks/create') return { zh: '新建任务', en: 'New Task', emoji: '✨' }
  if (path === '/favorites') return { zh: '评论收藏夹', en: 'Favorites', emoji: '💝' }
  if (path === '/bead-studio') return { zh: '图像拼豆', en: 'Bead Studio', emoji: '🧩' }
  if (path === '/bead-studio/cards') return { zh: 'MARD 色卡', en: 'Palette Cards', emoji: '🎨' }
  if (path === '/bilibili') return { zh: 'B 站视频', en: 'Bilibili', emoji: '📺' }
  if (path.includes('/edit')) return { zh: '编辑任务', en: 'Edit Task', emoji: '✏️' }
  if (path.includes('/search')) return { zh: '评论搜索', en: 'Comments', emoji: '💬' }
  if (path.startsWith('/tasks/')) return { zh: '任务详情', en: 'Task Detail', emoji: '🌷' }
  return { zh: '未知', en: 'Unknown', emoji: '❔' }
})

const sectionLabel = computed(() => {
  const path = route.path
  if (path === '/') return 'Home'
  if (path.startsWith('/bilibili')) return 'Bilibili'
  if (path.startsWith('/favorites')) return 'Favorites'
  if (path.startsWith('/bead-studio')) return 'Bead'
  if (path.startsWith('/tasks')) return 'Tasks'
  return 'Home'
})

const todayLabel = computed(() => {
  const d = new Date()
  return `${d.getFullYear()}/${String(d.getMonth() + 1).padStart(2, '0')}/${String(d.getDate()).padStart(2, '0')}`
})

const todayLong = computed(() => {
  const d = new Date()
  const wd = ['日','一','二','三','四','五','六'][d.getDay()]
  return `周${wd} · ${todayLabel.value}`
})

onMounted(async () => {
  try {
    const res = await axios.get('/api/system/login-status')
    loginStatus.value = res.data.logged_in
  } catch { loginStatus.value = false }
  setInterval(async () => {
    try {
      const res = await axios.get('/api/system/login-status')
      loginStatus.value = res.data.logged_in
    } catch {}
  }, 30000)

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
/* ============ Shell ============ */
.shell {
  display: grid;
  grid-template-columns: 240px 1fr;
  min-height: 100vh;
  position: relative;
}
.shell.compact {
  height: 100vh;
  min-height: 0;
  overflow: hidden;
}
@media (max-width: 900px) {
  .shell { grid-template-columns: 1fr; }
  .rail { position: static !important; height: auto !important; }
}

/* ============ Rail ============ */
.rail {
  position: sticky;
  top: 0;
  height: 100vh;
  display: flex;
  flex-direction: column;
  padding: 1.5rem 1.1rem 1.25rem;
  background:
    linear-gradient(180deg, #fff9fb 0%, #fff5f0 60%, #fef0e8 100%);
  border-right: 2px solid var(--line);
  box-shadow: 4px 0 24px rgba(255, 107, 157, 0.06);
  z-index: 10;
  overflow: hidden;
}
.rail::before {
  /* decorative cloud blob top-right */
  content: '';
  position: absolute;
  top: -40px; right: -40px;
  width: 140px; height: 140px;
  background: radial-gradient(circle, var(--sakura-glow), transparent 70%);
  pointer-events: none;
}
.rail::after {
  content: '❀';
  position: absolute;
  bottom: 110px; right: 18px;
  font-size: 28px;
  color: var(--sakura-light);
  opacity: 0.5;
  animation: drift 6s ease-in-out infinite;
}
@keyframes drift {
  0%, 100% { transform: translateY(0) rotate(0); }
  50% { transform: translateY(-8px) rotate(20deg); }
}

.brand {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  text-decoration: none;
  padding: 0.5rem 0.4rem 1.1rem;
  position: relative;
  z-index: 1;
}
.brand-blossom {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  animation: blossom-spin 12s linear infinite;
  filter: drop-shadow(0 4px 8px rgba(255, 107, 157, 0.35));
}
@keyframes blossom-spin {
  from { transform: rotate(0); }
  to   { transform: rotate(360deg); }
}
.brand-text { display: flex; flex-direction: column; line-height: 1.1; }
.brand-zh {
  font-family: var(--font-display);
  font-size: 1.55rem;
  color: var(--plum-1);
  letter-spacing: 0.06em;
}
.brand-en {
  font-family: var(--font-round);
  font-weight: 700;
  font-size: 0.7rem;
  letter-spacing: 0.12em;
  color: var(--sakura);
  margin-top: 0.15rem;
}

.rail-label {
  text-align: center;
  font-family: var(--font-display);
  font-size: 0.84rem;
  letter-spacing: 0.18em;
  color: var(--sakura);
  margin: 0.5rem 0 0.8rem;
  position: relative;
  z-index: 1;
}

.rail-nav {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  position: relative;
  z-index: 1;
}
.rail-item {
  display: grid;
  grid-template-columns: 32px 1fr 18px;
  align-items: center;
  gap: 0.5rem;
  padding: 0.7rem 0.85rem;
  border-radius: var(--radius-md);
  text-decoration: none;
  color: var(--plum-2);
  background: transparent;
  border: 2px solid transparent;
  transition: all var(--transition-fast);
  position: relative;
}
.rail-item:hover {
  background: #fff;
  border-color: var(--sakura-light);
  color: var(--plum-1);
  transform: translateX(2px);
}
.rail-emoji {
  font-size: 1.15rem;
  filter: saturate(1.1);
  transition: transform var(--transition-fast);
}
.rail-item:hover .rail-emoji { transform: scale(1.2) rotate(-8deg); }
.rail-name { display: flex; flex-direction: column; line-height: 1.15; }
.rail-zh {
  font-family: var(--font-display);
  font-size: 1.05rem;
  letter-spacing: 0.04em;
}
.rail-en {
  font-family: var(--font-round);
  font-weight: 600;
  font-size: 0.68rem;
  color: var(--plum-3);
  margin-top: 0.1rem;
  letter-spacing: 0.05em;
}
.rail-item.active {
  background: linear-gradient(135deg, #ffe6ef, #fff0f5);
  border-color: var(--sakura);
  color: var(--plum-1);
  box-shadow: 0 4px 14px var(--sakura-glow);
}
.rail-item.active .rail-zh { color: var(--sakura-deep); }
.rail-item.active .rail-en { color: var(--sakura); }
.rail-heart {
  color: var(--sakura);
  font-size: 0.95rem;
  animation: heart-beat 1.2s ease-in-out infinite;
}
@keyframes heart-beat {
  0%, 100% { transform: scale(1); }
  25% { transform: scale(1.25); }
  50% { transform: scale(0.9); }
}

.rail-foot {
  margin-top: auto;
  padding-top: 1rem;
  position: relative;
  z-index: 1;
}
.status-pill {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  padding: 0.7rem 0.85rem;
  background: #fff;
  border: 2px solid var(--sakura-light);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-soft);
}
.status-pill.is-off { border-color: var(--cream-4); opacity: 0.85; }
.status-emoji { font-size: 1.3rem; }
.status-text { display: flex; flex-direction: column; line-height: 1.2; }
.status-title {
  font-family: var(--font-display);
  font-size: 0.92rem;
  color: var(--plum-1);
}
.is-ok .status-title { color: var(--sakura-deep); }
.status-sub {
  font-size: 0.7rem;
  color: var(--plum-3);
  letter-spacing: 0.05em;
  margin-top: 0.1rem;
}

/* ============ Main ============ */
.main {
  padding: 1.75rem 2.5rem 4rem;
  max-width: none;          /* use full available width */
  width: 100%;
  min-width: 0;
  position: relative;
  z-index: 2;
}
@media (max-width: 720px) {
  .main { padding: 1.25rem; }
}

/* Compact mode — lock to viewport height, no page scroll.
   The page's own panels handle scrolling internally. */
.main.compact {
  height: 100vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  padding: 1.1rem 2rem 1.1rem;
  gap: 0;
}
.main.compact .masthead { flex: 0 0 auto; margin-bottom: 1rem; }
/* The routed component (task detail) fills the rest and manages its own scroll */
.main.compact > :last-child { flex: 1 1 auto; min-height: 0; }
@media (max-width: 720px) {
  .main.compact { padding: 0.75rem 1rem; }
}

/* ============ Masthead ============ */
.masthead {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.65rem 1.1rem;
  margin-bottom: 1.4rem;
  background: #ffffff;
  border: 2px dashed var(--sakura-light);
  border-radius: var(--radius-pill);
  box-shadow: var(--shadow-soft);
  font-size: 0.78rem;
}
.masthead-left, .masthead-right {
  display: flex;
  align-items: center;
  gap: 0.55rem;
}
.masthead-tag {
  background: var(--sakura);
  color: #fff;
  font-family: var(--font-round);
  font-weight: 700;
  padding: 0.15rem 0.7rem;
  border-radius: var(--radius-pill);
  font-size: 0.72rem;
  letter-spacing: 0.05em;
}
.masthead-dot { color: var(--sakura-light); }

.live-pill {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.18rem 0.7rem;
  background: var(--ok-glow);
  border: 1.5px solid var(--ok);
  border-radius: var(--radius-pill);
  font-family: var(--font-round);
  font-weight: 700;
  font-size: 0.7rem;
  color: var(--ok);
  letter-spacing: 0.1em;
}
.live-pill .live-dot {
  width: 7px; height: 7px; border-radius: 50%;
  background: var(--ok);
  box-shadow: 0 0 8px var(--ok);
  animation: live-blink 1.4s ease-in-out infinite;
}
.live-pill.off {
  background: var(--cream-2);
  border-color: var(--cream-4);
  color: var(--plum-3);
}
.live-pill.off .live-dot { background: var(--plum-3); box-shadow: none; animation: none; }
@keyframes live-blink {
  0%, 100% { opacity: 1; box-shadow: 0 0 8px var(--ok); }
  50% { opacity: 0.4; box-shadow: 0 0 2px var(--ok); }
}

/* ============ Hero ============ */
.hero {
  margin-bottom: 2rem;
  text-align: center;
}
.hero-eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.25rem 0.85rem;
  background: var(--lavender-glow);
  border: 1.5px solid var(--lavender);
  color: #6b4f96;
  border-radius: var(--radius-pill);
  font-family: var(--font-round);
  font-weight: 700;
  font-size: 0.74rem;
  letter-spacing: 0.05em;
  margin-bottom: 0.85rem;
}
.hero-emoji { font-size: 1rem; }
.hero-title {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.25rem;
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
  font-family: var(--font-round);
  font-weight: 700;
  font-size: clamp(0.9rem, 1.5vw, 1.1rem);
  color: var(--sakura);
  letter-spacing: 0.12em;
  text-transform: uppercase;
  margin-top: 0.35rem;
}
.hero-deco {
  display: flex;
  align-items: center;
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
  color: var(--sakura);
  font-size: 1.1rem;
  animation: spin-slow 3s ease-in-out infinite;
}

/* ============ Rocket buttons ============ */
.rockets {
  position: fixed;
  right: 1.6rem;
  bottom: 1.6rem;
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
  z-index: 50;
}
.rocket {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  border: 2px solid var(--sakura);
  background: linear-gradient(180deg, #fff, var(--cream-2));
  cursor: pointer;
  font-size: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  box-shadow: 0 4px 18px var(--sakura-glow), 0 2px 0 var(--sakura-light);
  transition: transform var(--transition-fast), box-shadow var(--transition-fast);
  overflow: visible;
}
.rocket:hover {
  transform: translateY(-3px) scale(1.06);
  box-shadow: 0 10px 26px var(--sakura-ring), 0 3px 0 var(--sakura);
  border-color: var(--sakura-deep);
}
.rocket:active { transform: translateY(0) scale(0.96); }
.rocket-emoji {
  display: inline-block;
  line-height: 1;
  transition: transform var(--transition-base);
  filter: drop-shadow(0 2px 4px rgba(255, 107, 157, 0.4));
}
.rocket-down .rocket-emoji { transform: rotate(180deg); }
.rocket:hover .rocket-emoji { animation: rocket-wiggle 0.6s ease-in-out infinite; }
.rocket-down:hover .rocket-emoji { animation: rocket-wiggle-down 0.6s ease-in-out infinite; }

@keyframes rocket-wiggle {
  0%, 100% { transform: translateY(0) rotate(0); }
  25% { transform: translateY(-3px) rotate(-6deg); }
  75% { transform: translateY(-3px) rotate(6deg); }
}
@keyframes rocket-wiggle-down {
  0%, 100% { transform: translateY(0) rotate(180deg); }
  25% { transform: translateY(3px) rotate(174deg); }
  75% { transform: translateY(3px) rotate(186deg); }
}

/* Rocket flame trail on hover */
.rocket-flame {
  position: absolute;
  width: 4px;
  border-radius: 2px;
  background: linear-gradient(180deg, transparent, var(--honey), var(--sakura), transparent);
  opacity: 0;
  transition: opacity 0.2s, height 0.2s;
  pointer-events: none;
}
.rocket-up .rocket-flame    { bottom: -8px; left: 50%; transform: translateX(-50%); height: 0; }
.rocket-down .rocket-flame  { top: -8px; left: 50%; transform: translateX(-50%); height: 0; }
.rocket:hover .rocket-flame { opacity: 1; height: 18px; }

@media (max-width: 720px) {
  .rockets { right: 0.9rem; bottom: 0.9rem; }
  .rocket { width: 42px; height: 42px; font-size: 18px; }
}
</style>
