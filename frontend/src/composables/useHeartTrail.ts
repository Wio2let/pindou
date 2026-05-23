/**
 * useHeartTrail — colourful little hearts that drift up from the cursor as
 * it moves. Used to give the kawaii pages (Studio / Gallery / MARD Cards)
 * the same playful particle effect.
 *
 * - Throttled to ~one heart per 90 ms so even fast cursor motion stays calm.
 * - Skips spawning when the cursor is hovering inside any element returned
 *   by `skipWhenInside()` — used in the Studio view to keep the drawing
 *   canvas itself heart-free.
 * - Auto-binds on `onActivated` / `onMounted` and unbinds on `onDeactivated`
 *   / `onBeforeUnmount` so it plays nicely with <keep-alive>.
 * - Stray hearts left in the DOM are swept when the view becomes inactive.
 *
 * The keyframes + .cursor-heart class live in App.vue's global stylesheet
 * so injected divs (appended to <body>) pick them up everywhere.
 */
import { onActivated, onBeforeUnmount, onDeactivated, onMounted } from 'vue'

const HEART_COLORS = [
  '#ff8fb8', '#ffb3c8', '#ffd0a3', '#ffe9a3',
  '#b8e6c1', '#a8d8ea', '#c4b5fd', '#f0a8d8',
]

export interface HeartTrailOptions {
  /**
   * If provided, returns an Element the trail should NOT spawn hearts on top
   * of. Hearts skip when `e.target` lives inside that element.
   */
  skipWhenInside?: () => Element | null | undefined
  /** Throttle in ms between hearts. Defaults to 90. */
  throttleMs?: number
}

export function useHeartTrail(opts: HeartTrailOptions = {}) {
  const throttle = opts.throttleMs ?? 90
  let lastAt = 0

  function spawnHeart(e: MouseEvent) {
    const skipEl = opts.skipWhenInside?.()
    if (skipEl) {
      const t = e.target as Node | null
      if (t && skipEl.contains(t)) return
    }
    const now = performance.now()
    if (now - lastAt < throttle) return
    lastAt = now

    const h = document.createElement('div')
    h.className = 'cursor-heart'
    h.textContent = '♥'
    const color = HEART_COLORS[(Math.random() * HEART_COLORS.length) | 0]
    const size = 12 + Math.random() * 12      // 12–24 px
    const drift = (Math.random() - 0.5) * 60  // ±30 px horizontal
    const rot = (Math.random() - 0.5) * 50    // ±25 deg
    h.style.left = (e.clientX - size / 2) + 'px'
    h.style.top = (e.clientY - size / 2) + 'px'
    h.style.color = color
    h.style.fontSize = size + 'px'
    h.style.setProperty('--heart-dx', drift + 'px')
    h.style.setProperty('--heart-rot', rot + 'deg')
    document.body.appendChild(h)
    window.setTimeout(() => { h.remove() }, 1200)
  }

  function bind() {
    window.addEventListener('mousemove', spawnHeart, { passive: true })
  }
  function unbind() {
    window.removeEventListener('mousemove', spawnHeart)
    document.querySelectorAll('.cursor-heart').forEach(n => n.remove())
  }

  // <keep-alive> friendly + works on plain views too
  onMounted(bind)
  onActivated(bind)
  onBeforeUnmount(unbind)
  onDeactivated(unbind)
}
