/* ================================================================
   usePixelFit — detect the true pixel grid of a pixel-styled image
   and resample it to a clean, grid-aligned color grid.

   Approach adapted from theamusing/perfectPixel (MIT):
     1. detect grid size  — Sobel-gradient peaks → median cell size
     2. refine grid lines — snap each line to the nearest Sobel edge
     3. sample each cell  — per-channel median color

   (The upstream project also has an FFT-magnitude detector; ported
   to JS it mis-locked onto frequency harmonics, so this uses the
   project's robust gradient-based detector instead.)
   ================================================================ */

export interface PixelFitResult {
  width: number
  height: number
  cells: ([number, number, number] | null)[]   // per-cell RGB, null = transparent
}

interface ImgData { w: number; h: number; data: Uint8ClampedArray }

// ---- pixel access -------------------------------------------------
function imageToRGBA(img: HTMLImageElement, maxSide = 1024): ImgData {
  let w = img.naturalWidth || img.width
  let h = img.naturalHeight || img.height
  const s = Math.min(1, maxSide / Math.max(w, h))
  w = Math.max(1, Math.round(w * s))
  h = Math.max(1, Math.round(h * s))
  const cv = document.createElement('canvas')
  cv.width = w; cv.height = h
  const ctx = cv.getContext('2d', { willReadFrequently: true })!
  ctx.imageSmoothingEnabled = false
  ctx.drawImage(img, 0, 0, w, h)
  return { w, h, data: ctx.getImageData(0, 0, w, h).data }
}

function toGray(im: ImgData): Float64Array {
  const g = new Float64Array(im.w * im.h)
  const d = im.data
  for (let i = 0; i < g.length; i++) {
    g[i] = 0.299 * d[i * 4] + 0.587 * d[i * 4 + 1] + 0.114 * d[i * 4 + 2]
  }
  return g
}

// ---- Sobel gradient projections ----------------------------------
/** gx[x] = Σ|SobelX| down each column ; gy[y] = Σ|SobelY| along each row. */
function sobelProfiles(gray: Float64Array, w: number, h: number): { gx: Float64Array; gy: Float64Array } {
  const gx = new Float64Array(w)
  const gy = new Float64Array(h)
  for (let y = 1; y < h - 1; y++) {
    const r0 = (y - 1) * w, r1 = y * w, r2 = (y + 1) * w
    for (let x = 1; x < w - 1; x++) {
      const tl = gray[r0 + x - 1], tc = gray[r0 + x], tr = gray[r0 + x + 1]
      const ml = gray[r1 + x - 1], mr = gray[r1 + x + 1]
      const bl = gray[r2 + x - 1], bc = gray[r2 + x], br = gray[r2 + x + 1]
      const sx = (tr + 2 * mr + br) - (tl + 2 * ml + bl)
      const sy = (bl + 2 * bc + br) - (tl + 2 * tc + tr)
      gx[x] += Math.abs(sx)
      gy[y] += Math.abs(sy)
    }
  }
  return { gx, gy }
}

// ---- grid-size estimation (gradient peaks → median interval) ------
function gridFromGradient(
  gx: Float64Array, gy: Float64Array, W: number, H: number, relThr = 0.2, minInterval = 4,
): { w: number | null; h: number | null } {
  // Plateau-aware peak finder: a clean pixel-art edge produces a Sobel ridge
  // that is often 2 px wide with *equal* values, so a strict `>` local-max
  // test misses it entirely. This treats a flat ridge as one peak.
  const findPeaks = (arr: Float64Array): number[] => {
    let mx = 0
    for (let i = 0; i < arr.length; i++) if (arr[i] > mx) mx = arr[i]
    const thr = relThr * mx
    const n = arr.length
    const peaks: number[] = []
    let i = 1
    while (i < n - 1) {
      if (arr[i] >= thr && arr[i] > arr[i - 1]) {
        let j = i
        while (j + 1 < n && arr[j + 1] === arr[i]) j++   // extend over a flat top
        if (j + 1 < n && arr[j + 1] < arr[i]) {          // rose in & falls out → peak
          const c = (i + j) >> 1
          if (peaks.length === 0 || c - peaks[peaks.length - 1] >= minInterval) peaks.push(c)
        }
        i = j + 1
      } else {
        i++
      }
    }
    return peaks
  }
  const median = (a: number[]): number => {
    const s = [...a].sort((p, q) => p - q)
    const m = s.length >> 1
    return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2
  }
  const px = findPeaks(gx), py = findPeaks(gy)
  if (px.length < 4 || py.length < 4) return { w: null, h: null }
  const intX: number[] = [], intY: number[] = []
  for (let i = 1; i < px.length; i++) intX.push(px[i] - px[i - 1])
  for (let i = 1; i < py.length; i++) intY.push(py[i] - py[i - 1])
  const cellW = median(intX), cellH = median(intY)
  if (cellW < 2 || cellH < 2) return { w: null, h: null }
  return { w: Math.round(W / cellW), h: Math.round(H / cellH) }
}

/** Detect grid (cols, rows). Normalizes to roughly-square cells. */
function detectGridScale(
  gx: Float64Array, gy: Float64Array, W: number, H: number, maxRatio = 1.5,
): { w: number | null; h: number | null } {
  const { w: gw, h: gh } = gridFromGradient(gx, gy, W, H)
  if (gw === null || gh === null || gw <= 0 || gh <= 0) return { w: null, h: null }
  const psx = W / gw, psy = H / gh
  const pixelSize = (psx / psy > maxRatio || psy / psx > maxRatio)
    ? Math.min(psx, psy)
    : (psx + psy) / 2
  return { w: Math.round(W / pixelSize), h: Math.round(H / pixelSize) }
}

// ---- grid-line refinement (snap to Sobel edges) -------------------
function findBestGrid(
  origin: number, rangeMin: number, rangeMax: number, grad: Float64Array,
): number {
  const best = Math.round(origin)
  let mx = 0
  for (let i = 0; i < grad.length; i++) if (grad[i] > mx) mx = grad[i]
  if (mx < 1e-6) return best
  const floor = mx * 0.05   // ignore flat (edge-free) regions
  const peaks: { v: number; idx: number }[] = []
  for (let i = -Math.round(rangeMin); i <= Math.round(rangeMax); i++) {
    const c = Math.round(origin + i)
    if (c <= 0 || c >= grad.length - 1) continue
    // non-strict so a flat-topped ridge still counts; pick the strongest below
    if (grad[c] >= grad[c - 1] && grad[c] >= grad[c + 1] && grad[c] > floor) {
      peaks.push({ v: grad[c], idx: c })
    }
  }
  if (peaks.length === 0) return best
  peaks.sort((a, b) => b.v - a.v)
  return peaks[0].idx
}

function refineGrids(
  gx: Float64Array, gy: Float64Array, W: number, H: number,
  gridX: number, gridY: number, refineIntensity = 0.25,
): { xs: number[]; ys: number[] } {
  const cellW = W / gridX, cellH = H / gridY
  const xs: number[] = [], ys: number[] = []
  // march outward from the image centre, snapping each line to the nearest edge
  let x = findBestGrid(W / 2, cellW, cellW, gx)
  while (x < W + cellW / 2) {
    x = findBestGrid(x, cellW * refineIntensity, cellW * refineIntensity, gx)
    xs.push(x); x += cellW
  }
  x = findBestGrid(W / 2, cellW, cellW, gx) - cellW
  while (x > -cellW / 2) {
    x = findBestGrid(x, cellW * refineIntensity, cellW * refineIntensity, gx)
    xs.push(x); x -= cellW
  }
  let y = findBestGrid(H / 2, cellH, cellH, gy)
  while (y < H + cellH / 2) {
    y = findBestGrid(y, cellH * refineIntensity, cellH * refineIntensity, gy)
    ys.push(y); y += cellH
  }
  y = findBestGrid(H / 2, cellH, cellH, gy) - cellH
  while (y > -cellH / 2) {
    y = findBestGrid(y, cellH * refineIntensity, cellH * refineIntensity, gy)
    ys.push(y); y -= cellH
  }
  xs.sort((a, b) => a - b)
  ys.sort((a, b) => a - b)
  return { xs, ys }
}

// ---- per-cell sampling (per-channel median) ----------------------
function sampleCells(im: ImgData, xs: number[], ys: number[]): PixelFitResult {
  const nx = xs.length - 1, ny = ys.length - 1
  const cells: ([number, number, number] | null)[] = new Array(nx * ny)
  const d = im.data, W = im.w, H = im.h
  const med = (a: number[]): number => {
    a.sort((p, q) => p - q)
    const m = a.length >> 1
    return a.length % 2 ? a[m] : (a[m - 1] + a[m]) / 2
  }
  for (let j = 0; j < ny; j++) {
    let y0 = Math.round(ys[j]), y1 = Math.round(ys[j + 1])
    y0 = Math.max(0, Math.min(H, y0)); y1 = Math.max(0, Math.min(H, y1))
    if (y1 <= y0) y1 = Math.min(y0 + 1, H)
    for (let i = 0; i < nx; i++) {
      let x0 = Math.round(xs[i]), x1 = Math.round(xs[i + 1])
      x0 = Math.max(0, Math.min(W, x0)); x1 = Math.max(0, Math.min(W, x1))
      if (x1 <= x0) x1 = Math.min(x0 + 1, W)
      const rs: number[] = [], gs: number[] = [], bs: number[] = [], as: number[] = []
      for (let y = y0; y < y1; y++) {
        for (let x = x0; x < x1; x++) {
          const p = (y * W + x) * 4
          rs.push(d[p]); gs.push(d[p + 1]); bs.push(d[p + 2]); as.push(d[p + 3])
        }
      }
      if (rs.length === 0) { cells[j * nx + i] = null; continue }
      cells[j * nx + i] = med(as) < 128
        ? null
        : [Math.round(med(rs)), Math.round(med(gs)), Math.round(med(bs))]
    }
  }
  return { width: nx, height: ny, cells }
}

/**
 * Detect the true pixel grid of a pixel-styled image and resample it.
 * Returns null if no usable grid could be detected (caller should fall back).
 */
export function pixelFitGrid(img: HTMLImageElement): PixelFitResult | null {
  try {
    const im = imageToRGBA(img, 1024)
    if (im.w < 8 || im.h < 8) return null
    const gray = toGray(im)
    const { gx, gy } = sobelProfiles(gray, im.w, im.h)
    const scale = detectGridScale(gx, gy, im.w, im.h)
    if (scale.w === null || scale.h === null) return null
    const gridX = Math.round(scale.w), gridY = Math.round(scale.h)
    if (gridX < 2 || gridY < 2 || gridX > 400 || gridY > 400) return null
    const { xs, ys } = refineGrids(gx, gy, im.w, im.h, gridX, gridY)
    if (xs.length < 2 || ys.length < 2) return null
    return sampleCells(im, xs, ys)
  } catch {
    return null
  }
}
