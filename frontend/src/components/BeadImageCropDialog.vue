<template>
  <div class="crop-overlay" @click.self="$emit('close')">
    <div class="crop-modal card">
      <div class="crop-head">
        <span class="crop-title">✂️ 裁剪图片</span>
        <button class="crop-x" @click="$emit('close')">✕</button>
      </div>
      <div class="crop-body">
        <div class="crop-stage">
          <canvas ref="cv" class="crop-canvas"
                  @mousedown="onDown" @mousemove="onMove"
                  @mouseup="onUp" @mouseleave="onUp"></canvas>
        </div>
        <div class="crop-info">
          裁剪范围 {{ Math.round(crop.r - crop.l) }} × {{ Math.round(crop.b - crop.t) }} px
          · 拖动边/角手柄调整大小，框内拖动可移动
        </div>
      </div>
      <div class="crop-foot">
        <button class="btn btn-ghost" @click="resetCrop">重置</button>
        <button class="btn btn-ghost" @click="$emit('close')">取消</button>
        <button class="btn btn-primary" @click="apply">应用裁剪</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'

const props = defineProps<{ src: string }>()
const emit = defineEmits<{ close: []; apply: [{ dataUrl: string }] }>()

const cv = ref<HTMLCanvasElement | null>(null)
const crop = reactive({ l: 0, t: 0, r: 1, b: 1 })   // image-pixel coordinates

let img: HTMLImageElement | null = null
let iw = 1, ih = 1          // natural image size
let scale = 1               // display scale (display px = image px * scale)
const MIN = 8               // minimum crop size, image px

// handle → which edges it moves: [left, top, right, bottom]
const HANDLE_EDGES = [
  [1, 1, 0, 0], [0, 1, 0, 0], [0, 1, 1, 0], [0, 0, 1, 0],
  [0, 0, 1, 1], [0, 0, 0, 1], [1, 0, 0, 1], [1, 0, 0, 0],
]

let drag: { mode: 'resize' | 'move'; handle: number; sx: number; sy: number;
            start: { l: number; t: number; r: number; b: number } } | null = null

onMounted(() => {
  const im = new Image()
  im.onload = () => {
    img = im
    iw = im.naturalWidth || im.width
    ih = im.naturalHeight || im.height
    crop.l = 0; crop.t = 0; crop.r = iw; crop.b = ih
    const maxW = 560, maxH = 420
    scale = Math.min(maxW / iw, maxH / ih)
    const c = cv.value!
    c.width = Math.round(iw * scale)
    c.height = Math.round(ih * scale)
    render()
  }
  im.src = props.src
})

function resetCrop() {
  crop.l = 0; crop.t = 0; crop.r = iw; crop.b = ih
  render()
}

/** Display-coord centres of the 8 resize handles (nw,n,ne,e,se,s,sw,w). */
function handlePositions(): [number, number][] {
  const l = crop.l * scale, t = crop.t * scale, r = crop.r * scale, b = crop.b * scale
  const mx = (l + r) / 2, my = (t + b) / 2
  return [[l, t], [mx, t], [r, t], [r, my], [r, b], [mx, b], [l, b], [l, my]]
}

function render() {
  const c = cv.value
  if (!c || !img) return
  const ctx = c.getContext('2d')!
  ctx.clearRect(0, 0, c.width, c.height)
  ctx.drawImage(img, 0, 0, c.width, c.height)
  const l = crop.l * scale, t = crop.t * scale, r = crop.r * scale, b = crop.b * scale
  // dim everything outside the crop rectangle
  ctx.fillStyle = 'rgba(30,20,30,0.55)'
  ctx.fillRect(0, 0, c.width, t)
  ctx.fillRect(0, b, c.width, c.height - b)
  ctx.fillRect(0, t, l, b - t)
  ctx.fillRect(r, t, c.width - r, b - t)
  // rule-of-thirds guides
  ctx.strokeStyle = 'rgba(255,255,255,0.45)'
  ctx.lineWidth = 1
  ctx.beginPath()
  for (let i = 1; i <= 2; i++) {
    const gx = l + (r - l) * i / 3, gy = t + (b - t) * i / 3
    ctx.moveTo(gx, t); ctx.lineTo(gx, b)
    ctx.moveTo(l, gy); ctx.lineTo(r, gy)
  }
  ctx.stroke()
  // crop border
  ctx.strokeStyle = '#ff6b9d'
  ctx.lineWidth = 2
  ctx.strokeRect(l, t, r - l, b - t)
  // 8 handles
  ctx.fillStyle = '#ffffff'
  ctx.strokeStyle = '#ff6b9d'
  ctx.lineWidth = 2
  for (const [hx, hy] of handlePositions()) {
    ctx.fillRect(hx - 5, hy - 5, 10, 10)
    ctx.strokeRect(hx - 5, hy - 5, 10, 10)
  }
}

function localPos(e: MouseEvent): { x: number; y: number } {
  const rect = cv.value!.getBoundingClientRect()
  return { x: e.clientX - rect.left, y: e.clientY - rect.top }
}

function onDown(e: MouseEvent) {
  if (!img) return
  const p = localPos(e)
  // hit-test handles first
  const hs = handlePositions()
  for (let i = 0; i < 8; i++) {
    if (Math.abs(p.x - hs[i][0]) <= 9 && Math.abs(p.y - hs[i][1]) <= 9) {
      drag = { mode: 'resize', handle: i, sx: p.x, sy: p.y,
               start: { l: crop.l, t: crop.t, r: crop.r, b: crop.b } }
      return
    }
  }
  // inside the crop → move
  const ix = p.x / scale, iy = p.y / scale
  if (ix >= crop.l && ix <= crop.r && iy >= crop.t && iy <= crop.b) {
    drag = { mode: 'move', handle: -1, sx: p.x, sy: p.y,
             start: { l: crop.l, t: crop.t, r: crop.r, b: crop.b } }
  }
}

function onMove(e: MouseEvent) {
  if (!drag || !img) return
  const p = localPos(e)
  const s = drag.start
  if (drag.mode === 'move') {
    let dx = (p.x - drag.sx) / scale
    let dy = (p.y - drag.sy) / scale
    dx = Math.max(-s.l, Math.min(iw - s.r, dx))
    dy = Math.max(-s.t, Math.min(ih - s.b, dy))
    crop.l = s.l + dx; crop.r = s.r + dx
    crop.t = s.t + dy; crop.b = s.b + dy
  } else {
    const ix = Math.max(0, Math.min(iw, p.x / scale))
    const iy = Math.max(0, Math.min(ih, p.y / scale))
    const ed = HANDLE_EDGES[drag.handle]
    if (ed[0]) crop.l = Math.min(ix, crop.r - MIN)
    if (ed[2]) crop.r = Math.max(ix, crop.l + MIN)
    if (ed[1]) crop.t = Math.min(iy, crop.b - MIN)
    if (ed[3]) crop.b = Math.max(iy, crop.t + MIN)
  }
  render()
}

function onUp() { drag = null }

function apply() {
  if (!img) return
  const w = Math.max(1, Math.round(crop.r - crop.l))
  const h = Math.max(1, Math.round(crop.b - crop.t))
  const out = document.createElement('canvas')
  out.width = w; out.height = h
  const ctx = out.getContext('2d')!
  ctx.drawImage(img, Math.round(crop.l), Math.round(crop.t), w, h, 0, 0, w, h)
  emit('apply', { dataUrl: out.toDataURL('image/png') })
}
</script>

<style scoped>
.crop-overlay {
  position: fixed; inset: 0; background: rgba(74,54,69,0.4);
  display: flex; align-items: center; justify-content: center;
  z-index: 100; backdrop-filter: blur(4px);
}
.crop-modal {
  padding: 1.1rem 1.3rem;
  max-width: 94vw;
  animation: pop-in 0.3s cubic-bezier(0.34, 1.56, 0.64, 1) both;
}
.crop-head {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 0.8rem;
}
.crop-title { font-family: var(--font-display); font-size: 1.05rem; color: var(--plum-1); }
.crop-x { background: none; border: none; font-size: 1.1rem; cursor: pointer; color: var(--plum-3); }
.crop-x:hover { color: var(--plum-1); }
.crop-body { display: flex; flex-direction: column; gap: 0.5rem; }
.crop-stage {
  display: flex; align-items: center; justify-content: center;
  background: var(--cream-2);
  border: 2px dashed var(--line-strong);
  border-radius: var(--radius-md);
  padding: 0.5rem;
}
.crop-canvas { display: block; cursor: crosshair; border-radius: var(--radius-sm); }
.crop-info { text-align: center; font-size: 0.72rem; color: var(--plum-3); }
.crop-foot {
  display: flex; justify-content: flex-end; gap: 0.6rem;
  margin-top: 0.9rem; padding-top: 0.8rem;
  border-top: 2px dashed var(--line-strong);
}
</style>
