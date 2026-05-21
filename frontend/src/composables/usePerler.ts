/* ================================================================
   usePerler — image → perler-bead grid conversion (pure, client-side)
   ================================================================ */

import { MARD_COLORS, type BeadColor } from '../data/mardPalettes'

export interface PerlerGrid {
  width: number
  height: number
  cells: (string | null)[]   // MARD code, or null for an empty (transparent) cell
}

/** Pixelation algorithms. */
export type ConvertAlgo = 'smooth' | 'avg' | 'sharp' | 'slic' | 'block' | 'floyd' | 'atkinson' | 'bayer' | 'native'

export const ALGO_OPTIONS: { id: ConvertAlgo; label: string; desc: string }[] = [
  { id: 'native',   label: '原图像素 · 1:1',  desc: '图片本身是像素画时，按原始像素直接导入，不缩放、不模糊（导入像素画会自动启用）' },
  { id: 'smooth',   label: '平滑取色',       desc: '双线性缩放后最近邻匹配，适合照片' },
  { id: 'avg',      label: '区域平均',        desc: '四倍中间帧降采样取均值，颜色过渡更柔和' },
  { id: 'sharp',    label: '锐利像素',        desc: '边缘保留降采样，线条与轮廓清晰不丢失，适合像素图/线稿/Logo' },
  { id: 'slic',     label: 'SLIC 像素',      desc: 'SLIC 超像素聚类，相似区域合并为干净色块，扁平像素画风' },
  { id: 'block',    label: '色块归并',       desc: '邻域多数表决迭代，相邻像素尽量同色，合并成大块平整色区' },
  { id: 'floyd',    label: '抖动 · Floyd',   desc: 'Floyd-Steinberg 误差扩散，渐变更细腻' },
  { id: 'atkinson', label: '抖动 · Atkinson', desc: 'Atkinson 抖动，轮廓清晰，颗粒感弱' },
  { id: 'bayer',    label: '抖动 · Bayer',   desc: '有序抖动，规则颗粒感，复古风格' },
]

/**
 * Color-matching ("平替") metric — decides which available palette color
 * substitutes for a color the chosen kit does not stock.
 */
export type MatchMetric = 'lab' | 'weighted' | 'hue' | 'luma'

export const MATCH_OPTIONS: { id: MatchMetric; label: string; desc: string }[] = [
  { id: 'lab',      label: '丝滑匹配',     desc: '感知均匀色彩空间匹配，渐变丝滑、色彩纯净不混杂（推荐）' },
  { id: 'weighted', label: '加权匹配',     desc: 'redmean 加权，综合最接近' },
  { id: 'hue',      label: '同色相优先',   desc: '优先保留色相，色系一致' },
  { id: 'luma',     label: '同明度优先',   desc: '优先保留明暗，层次清晰' },
]

// ---- RGB → HSL ----
function rgb2hsl(r: number, g: number, b: number): [number, number, number] {
  r /= 255; g /= 255; b /= 255
  const max = Math.max(r, g, b), min = Math.min(r, g, b)
  const d = max - min
  let h = 0
  const l = (max + min) / 2
  const s = d === 0 ? 0 : d / (1 - Math.abs(2 * l - 1))
  if (d > 0) {
    if (max === r) h = ((g - b) / d) % 6
    else if (max === g) h = (b - r) / d + 2
    else h = (r - g) / d + 4
    h *= 60
    if (h < 0) h += 360
  }
  return [h, s, l]
}

/** redmean weighted Euclidean distance. */
function redmean(
  r1: number, g1: number, b1: number,
  r2: number, g2: number, b2: number,
): number {
  const rm = (r1 + r2) / 2
  const dr = r1 - r2, dg = g1 - g2, db = b1 - b2
  return (2 + rm / 256) * dr * dr + 4 * dg * dg + (2 + (255 - rm) / 256) * db * db
}

// ---- sRGB → CIELAB (D65) ----
function rgb2lab(r: number, g: number, b: number): [number, number, number] {
  // sRGB → linear
  let rl = r / 255, gl = g / 255, bl = b / 255
  rl = rl > 0.04045 ? Math.pow((rl + 0.055) / 1.055, 2.4) : rl / 12.92
  gl = gl > 0.04045 ? Math.pow((gl + 0.055) / 1.055, 2.4) : gl / 12.92
  bl = bl > 0.04045 ? Math.pow((bl + 0.055) / 1.055, 2.4) : bl / 12.92
  // linear RGB → XYZ → normalize to D65 white
  let x = (rl * 0.4124 + gl * 0.3576 + bl * 0.1805) / 0.95047
  let y = (rl * 0.2126 + gl * 0.7152 + bl * 0.0722)
  let z = (rl * 0.0193 + gl * 0.1192 + bl * 0.9505) / 1.08883
  const f = (t: number) => t > 0.008856 ? Math.cbrt(t) : (7.787 * t + 16 / 116)
  x = f(x); y = f(y); z = f(z)
  return [116 * y - 16, 500 * (x - y), 200 * (y - z)]
}

// memoized CIELAB for palette colors (computed once per code)
const _labCache = new Map<string, [number, number, number]>()
function labOf(c: BeadColor): [number, number, number] {
  let v = _labCache.get(c.code)
  if (!v) { v = rgb2lab(c.rgb[0], c.rgb[1], c.rgb[2]); _labCache.set(c.code, v) }
  return v
}

/**
 * Nearest bead color in a palette to an RGB triple, under the chosen
 * matching metric. This is the core of the "平替" (substitute) logic:
 * any color the kit lacks is replaced by its nearest stocked color.
 */
export function nearestColor(
  r: number, g: number, b: number, palette: BeadColor[],
  metric: MatchMetric = 'lab',
): BeadColor {
  let best = palette[0]
  let bestD = Infinity

  if (metric === 'lab') {
    // ΔE94-style distance in perceptually-uniform CIELAB.
    // Perceptual uniformity → gradients band smoothly ("丝滑");
    // hue is weighted up and de-saturation is penalized → no muddy
    // ("混杂") substitutes.
    const [pL, pa, pb] = rgb2lab(r, g, b)
    const pC = Math.sqrt(pa * pa + pb * pb)
    const sC = 1 + 0.045 * pC
    const sH = 1 + 0.015 * pC
    for (const c of palette) {
      const [cL, ca, cb] = labOf(c)
      const cC = Math.sqrt(ca * ca + cb * cb)
      const dL = pL - cL
      const dC = pC - cC
      const da = pa - ca, db = pb - cb
      let dH2 = da * da + db * db - dC * dC
      if (dH2 < 0) dH2 = 0
      let dCsq = (dC * dC) / (sC * sC)
      if (dC > 0) dCsq *= 1.6                       // duller candidate → muddy, penalize
      const d = dL * dL + dCsq + (dH2 / (sH * sH)) * 1.35
      if (d < bestD) { bestD = d; best = c }
    }
    return best
  }

  if (metric === 'weighted') {
    for (const c of palette) {
      const d = redmean(r, g, b, c.rgb[0], c.rgb[1], c.rgb[2])
      if (d < bestD) { bestD = d; best = c }
    }
    return best
  }

  // hue / luma metrics work in HSL space
  const [ph, ps, pl] = rgb2hsl(r, g, b)
  for (const c of palette) {
    const [ch, cs, cl] = c.hsl
    let dh = Math.abs(ph - ch)
    if (dh > 180) dh = 360 - dh
    const dhn = dh / 180
    const ds = ps - cs
    const dl = pl - cl
    let d: number
    if (metric === 'hue') {
      // hue dominates; saturation/lightness are tie-breakers
      d = dhn * dhn * 9 + ds * ds * 1.2 + dl * dl * 1.0
      // desaturated pixels have unstable hue → fall back to lightness
      if (ps < 0.12) d = dl * dl * 6 + ds * ds
    } else {
      // luma dominates
      d = dl * dl * 10 + ds * ds * 0.8 + dhn * dhn * 0.5
    }
    if (d < bestD) { bestD = d; best = c }
  }
  return best
}

function clamp255(v: number): number {
  return v < 0 ? 0 : v > 255 ? 255 : v
}

// 4×4 Bayer threshold matrix (values 0–15)
const BAYER4 = [
  [0,  8,  2, 10],
  [12, 4, 14,  6],
  [3,  11, 1,  9],
  [15, 7, 13,  5],
]

export interface PixelArtInfo {
  isPixelArt: boolean
  nativeW: number
  nativeH: number
  scaleX: number
  scaleY: number
}

/**
 * Detect whether an image is pixel art and, if so, its native pixel
 * resolution. Upscaled pixel art (a small sprite saved large) is found by
 * run-length analysis — every run of identical pixels is an integer multiple
 * of the upscale factor. Native-resolution pixel art is recognised by being
 * small with few distinct colors.
 */
export function detectPixelArt(img: HTMLImageElement): PixelArtInfo {
  const w0 = img.naturalWidth || img.width
  const h0 = img.naturalHeight || img.height
  const fail: PixelArtInfo = { isPixelArt: false, nativeW: w0, nativeH: h0, scaleX: 1, scaleY: 1 }
  // too large to be a practical 1:1 bead pattern → don't treat as pixel art
  if (w0 < 2 || h0 < 2 || Math.max(w0, h0) > 1024) return fail

  const cv = document.createElement('canvas')
  cv.width = w0
  cv.height = h0
  const ctx = cv.getContext('2d', { willReadFrequently: true })!
  ctx.imageSmoothingEnabled = false
  ctx.drawImage(img, 0, 0)
  const d = ctx.getImageData(0, 0, w0, h0).data

  const same = (i: number, j: number) =>
    d[i] === d[j] && d[i + 1] === d[j + 1] && d[i + 2] === d[j + 2] && d[i + 3] === d[j + 3]

  // smallest interior run length along one axis (= the upscale factor, if any)
  const blockSize = (axis: 'x' | 'y'): number => {
    const runs: number[] = []
    const major = axis === 'x' ? w0 : h0
    const minor = axis === 'x' ? h0 : w0
    const step = Math.max(1, Math.floor(minor / 64))   // sample ~64 lines
    for (let m = 0; m < minor; m += step) {
      let runStart = 0
      for (let k = 1; k <= major; k++) {
        const cur  = axis === 'x' ? (m * w0 + k) * 4 : (k * w0 + m) * 4
        const prev = axis === 'x' ? (m * w0 + (k - 1)) * 4 : ((k - 1) * w0 + m) * 4
        if (k === major || !same(cur, prev)) {
          // drop edge runs (partial blocks) and full-line runs (no info)
          if (runStart > 0 && k < major) runs.push(k - runStart)
          runStart = k
        }
      }
    }
    if (runs.length < 16) return 1
    let minRun = Infinity
    for (const r of runs) if (r < minRun) minRun = r
    if (minRun < 2 || minRun > major / 2) return 1
    // confirm: nearly all runs are integer multiples of the smallest one
    let ok = 0
    for (const r of runs) if (r % minRun === 0) ok++
    return ok / runs.length >= 0.92 ? minRun : 1
  }

  const scaleX = blockSize('x')
  const scaleY = blockSize('y')
  const nativeW = Math.max(1, Math.round(w0 / scaleX))
  const nativeH = Math.max(1, Math.round(h0 / scaleY))

  // count distinct opaque colors (cap the scan once clearly past the threshold)
  const colors = new Set<number>()
  for (let i = 0; i < d.length && colors.size <= 260; i += 4) {
    if (d[i + 3] < 128) continue
    colors.add((d[i] << 16) | (d[i + 1] << 8) | d[i + 2])
  }

  const isUpscaled = scaleX >= 2 && scaleY >= 2
  const isSmallFlat = Math.max(w0, h0) <= 160 && colors.size <= 256
  let isPixelArt = isUpscaled || isSmallFlat
  // a 1:1 bead grid larger than this is impractical
  if (nativeW > 220 || nativeH > 220) isPixelArt = false

  return { isPixelArt, nativeW, nativeH, scaleX, scaleY }
}

/**
 * Convert an image to a bead grid restricted to `palette` (the selected kit).
 * `algo` = pixelation strategy, `metric` = how out-of-kit colors are matched.
 */
export function imageToGrid(
  img: HTMLImageElement,
  targetWidth: number,
  palette: BeadColor[],
  algo: ConvertAlgo = 'smooth',
  metric: MatchMetric = 'lab',
): PerlerGrid {
  // ---- native: 1:1 pixel-art import — each source pixel → one bead,
  // nearest-neighbour (no blur), grid size from the image (ignores targetWidth)
  if (algo === 'native') {
    const pa = detectPixelArt(img)
    const nw = pa.nativeW, nh = pa.nativeH
    const cv = document.createElement('canvas')
    cv.width = nw
    cv.height = nh
    const ctx = cv.getContext('2d', { willReadFrequently: true })!
    ctx.imageSmoothingEnabled = false
    ctx.clearRect(0, 0, nw, nh)
    ctx.drawImage(img, 0, 0, nw, nh)
    const data = ctx.getImageData(0, 0, nw, nh).data
    const ncells: (string | null)[] = new Array(nw * nh)
    for (let i = 0; i < nw * nh; i++) {
      if (data[i * 4 + 3] < 128) { ncells[i] = null; continue }
      ncells[i] = nearestColor(data[i * 4], data[i * 4 + 1], data[i * 4 + 2], palette, metric).code
    }
    return { width: nw, height: nh, cells: ncells }
  }

  const ratio = (img.naturalHeight || img.height) / (img.naturalWidth || img.width)
  const w = Math.max(1, Math.round(targetWidth))
  const h = Math.max(1, Math.round(w * ratio))

  const cells: (string | null)[] = new Array(w * h)

  // ---- avg: two-pass area-average downsampling ----
  if (algo === 'avg') {
    // render at 4× resolution first, then downsample to final size
    const tmp = document.createElement('canvas')
    tmp.width = w * 4
    tmp.height = h * 4
    const tctx = tmp.getContext('2d', { willReadFrequently: true })!
    tctx.imageSmoothingEnabled = true
    tctx.imageSmoothingQuality = 'high'
    tctx.clearRect(0, 0, tmp.width, tmp.height)
    tctx.drawImage(img, 0, 0, tmp.width, tmp.height)

    const cv = document.createElement('canvas')
    cv.width = w
    cv.height = h
    const ctx = cv.getContext('2d', { willReadFrequently: true })!
    ctx.imageSmoothingEnabled = true
    ctx.imageSmoothingQuality = 'high'
    ctx.clearRect(0, 0, w, h)
    ctx.drawImage(tmp, 0, 0, w, h)

    const data = ctx.getImageData(0, 0, w, h).data
    for (let i = 0; i < w * h; i++) {
      if (data[i * 4 + 3] < 128) { cells[i] = null; continue }
      cells[i] = nearestColor(data[i * 4], data[i * 4 + 1], data[i * 4 + 2], palette, metric).code
    }
    return { width: w, height: h, cells }
  }

  // ---- sharp: edge-preserving downsample ----
  // Nearest-neighbor downsampling drops thin outlines and aliases hard edges.
  // Instead, render the source at a higher resolution and, for every output
  // cell, detect whether a strong edge runs through it. On an edge cell the
  // darker pixel cluster wins — so contours / 线条 stay crisp, connected and
  // fully recognizable; flat regions keep their clean average color.
  if (algo === 'sharp') {
    const scale = 5
    const sw = w * scale, sh = h * scale
    const tmp = document.createElement('canvas')
    tmp.width = sw
    tmp.height = sh
    const tctx = tmp.getContext('2d', { willReadFrequently: true })!
    tctx.imageSmoothingEnabled = true
    tctx.imageSmoothingQuality = 'high'
    tctx.clearRect(0, 0, sw, sh)
    tctx.drawImage(img, 0, 0, sw, sh)
    const sd = tctx.getImageData(0, 0, sw, sh).data
    const lumaOf = (r: number, g: number, b: number) => 0.299 * r + 0.587 * g + 0.114 * b
    // luminance-contrast threshold for "an edge runs through this cell"
    const EDGE = 42

    for (let cy = 0; cy < h; cy++) {
      for (let cx = 0; cx < w; cx++) {
        // pass 1 — block average + luminance range
        let aR = 0, aG = 0, aB = 0, opaque = 0
        let minL = 256, maxL = -1
        for (let dy = 0; dy < scale; dy++) {
          for (let dx = 0; dx < scale; dx++) {
            const i = ((cy * scale + dy) * sw + (cx * scale + dx)) * 4
            if (sd[i + 3] < 128) continue
            opaque++
            aR += sd[i]; aG += sd[i + 1]; aB += sd[i + 2]
            const l = lumaOf(sd[i], sd[i + 1], sd[i + 2])
            if (l < minL) minL = l
            if (l > maxL) maxL = l
          }
        }
        const cell = cy * w + cx
        if (opaque * 2 < scale * scale) { cells[cell] = null; continue }
        aR /= opaque; aG /= opaque; aB /= opaque

        let r = aR, g = aG, b = aB
        if (maxL - minL >= EDGE) {
          // pass 2 — an edge runs through; average only the darker cluster
          // so the outline color wins and stays connected
          const mid = (minL + maxL) / 2
          let dR = 0, dG = 0, dB = 0, dN = 0
          for (let dy = 0; dy < scale; dy++) {
            for (let dx = 0; dx < scale; dx++) {
              const i = ((cy * scale + dy) * sw + (cx * scale + dx)) * 4
              if (sd[i + 3] < 128) continue
              if (lumaOf(sd[i], sd[i + 1], sd[i + 2]) <= mid) {
                dR += sd[i]; dG += sd[i + 1]; dB += sd[i + 2]; dN++
              }
            }
          }
          if (dN > 0) { r = dR / dN; g = dG / dN; b = dB / dN }
        }
        cells[cell] = nearestColor(r, g, b, palette, metric).code
      }
    }
    return { width: w, height: h, cells }
  }

  // ---- slic: SLIC superpixel clustering ----
  // Cluster cells into superpixels in CIELAB+xy space, then flatten each
  // superpixel to one averaged color. Merges similar regions into clean flat
  // patches — a tidy, poster-like pixel-art look.
  if (algo === 'slic') {
    const cv = document.createElement('canvas')
    cv.width = w
    cv.height = h
    const ctx = cv.getContext('2d', { willReadFrequently: true })!
    ctx.imageSmoothingEnabled = true
    ctx.imageSmoothingQuality = 'high'
    ctx.clearRect(0, 0, w, h)
    ctx.drawImage(img, 0, 0, w, h)
    const data = ctx.getImageData(0, 0, w, h).data
    const N = w * h

    // per-cell CIELAB + opacity
    const labL = new Float32Array(N), labA = new Float32Array(N), labB = new Float32Array(N)
    const opaque = new Uint8Array(N)
    for (let i = 0; i < N; i++) {
      if (data[i * 4 + 3] < 128) continue
      opaque[i] = 1
      const lab = rgb2lab(data[i * 4], data[i * 4 + 1], data[i * 4 + 2])
      labL[i] = lab[0]; labA[i] = lab[1]; labB[i] = lab[2]
    }

    const S = 3                       // superpixel grid step (cells)
    const m = 12                      // compactness (color vs. shape balance)
    const spatial = (m * m) / (S * S) // weight of the xy term

    // init cluster centers on a regular grid
    const cL: number[] = [], cA: number[] = [], cB: number[] = [], cX: number[] = [], cY: number[] = []
    for (let cy = (S >> 1); cy < h; cy += S) {
      for (let cx = (S >> 1); cx < w; cx += S) {
        const i = cy * w + cx
        cL.push(labL[i]); cA.push(labA[i]); cB.push(labB[i]); cX.push(cx); cY.push(cy)
      }
    }
    const K = cL.length
    const label = new Int32Array(N).fill(-1)
    const dist = new Float32Array(N)

    for (let iter = 0; iter < 10; iter++) {
      dist.fill(Infinity)
      for (let k = 0; k < K; k++) {
        const kx = cX[k], ky = cY[k]
        const x0 = Math.max(0, Math.floor(kx - S)), x1 = Math.min(w - 1, Math.ceil(kx + S))
        const y0 = Math.max(0, Math.floor(ky - S)), y1 = Math.min(h - 1, Math.ceil(ky + S))
        for (let y = y0; y <= y1; y++) {
          for (let x = x0; x <= x1; x++) {
            const i = y * w + x
            if (!opaque[i]) continue
            const dl = labL[i] - cL[k], da = labA[i] - cA[k], db = labB[i] - cB[k]
            const dx = x - kx, dy = y - ky
            const D = dl * dl + da * da + db * db + (dx * dx + dy * dy) * spatial
            if (D < dist[i]) { dist[i] = D; label[i] = k }
          }
        }
      }
      // recompute centers as the mean of their assigned cells
      const sL = new Float64Array(K), sA = new Float64Array(K), sB = new Float64Array(K)
      const sX = new Float64Array(K), sY = new Float64Array(K), cnt = new Int32Array(K)
      for (let y = 0; y < h; y++) {
        for (let x = 0; x < w; x++) {
          const i = y * w + x
          const k = label[i]
          if (k < 0) continue
          sL[k] += labL[i]; sA[k] += labA[i]; sB[k] += labB[i]
          sX[k] += x; sY[k] += y; cnt[k]++
        }
      }
      for (let k = 0; k < K; k++) {
        if (!cnt[k]) continue
        cL[k] = sL[k] / cnt[k]; cA[k] = sA[k] / cnt[k]; cB[k] = sB[k] / cnt[k]
        cX[k] = sX[k] / cnt[k]; cY[k] = sY[k] / cnt[k]
      }
    }

    // each superpixel → its mean RGB → nearest bead color
    const sR = new Float64Array(K), sG = new Float64Array(K), sBl = new Float64Array(K), cn = new Int32Array(K)
    for (let i = 0; i < N; i++) {
      const k = label[i]
      if (k < 0) continue
      sR[k] += data[i * 4]; sG[k] += data[i * 4 + 1]; sBl[k] += data[i * 4 + 2]; cn[k]++
    }
    const clusterCode: (string | null)[] = new Array(K)
    for (let k = 0; k < K; k++) {
      clusterCode[k] = cn[k]
        ? nearestColor(sR[k] / cn[k], sG[k] / cn[k], sBl[k] / cn[k], palette, metric).code
        : null
    }
    for (let i = 0; i < N; i++) {
      if (!opaque[i]) { cells[i] = null; continue }
      const k = label[i]
      cells[i] = k >= 0
        ? clusterCode[k]
        : nearestColor(data[i * 4], data[i * 4 + 1], data[i * 4 + 2], palette, metric).code
    }
    return { width: w, height: h, cells }
  }

  // ---- block: region-coalescing majority filter ----
  // Quantize, then iteratively set each cell to the most common color in its
  // 3×3 neighbourhood. Adjacent cells converge to the same color, so the
  // result is built from large, flat color patches.
  if (algo === 'block') {
    const cv = document.createElement('canvas')
    cv.width = w
    cv.height = h
    const ctx = cv.getContext('2d', { willReadFrequently: true })!
    ctx.imageSmoothingEnabled = true
    ctx.imageSmoothingQuality = 'high'
    ctx.clearRect(0, 0, w, h)
    ctx.drawImage(img, 0, 0, w, h)
    const data = ctx.getImageData(0, 0, w, h).data
    const N = w * h

    // initial quantization
    let cur: (string | null)[] = new Array(N)
    for (let i = 0; i < N; i++) {
      if (data[i * 4 + 3] < 128) { cur[i] = null; continue }
      cur[i] = nearestColor(data[i * 4], data[i * 4 + 1], data[i * 4 + 2], palette, metric).code
    }

    // iterative 3×3 majority vote — the center cell is weighted, so a cell
    // only flips when a neighbouring color clearly dominates
    for (let pass = 0; pass < 4; pass++) {
      const next: (string | null)[] = new Array(N)
      let changed = 0
      for (let y = 0; y < h; y++) {
        for (let x = 0; x < w; x++) {
          const i = y * w + x
          const center = cur[i]
          if (center === null) { next[i] = null; continue }
          const tally = new Map<string, number>()
          for (let dy = -1; dy <= 1; dy++) {
            for (let dx = -1; dx <= 1; dx++) {
              const nx = x + dx, ny = y + dy
              if (nx < 0 || nx >= w || ny < 0 || ny >= h) continue
              const code = cur[ny * w + nx]
              if (code === null) continue
              const wgt = (dx === 0 && dy === 0) ? 2 : 1
              tally.set(code, (tally.get(code) || 0) + wgt)
            }
          }
          let best = center
          let bestN = tally.get(center) || 0
          for (const [code, n] of tally) {
            if (n > bestN) { bestN = n; best = code }
          }
          next[i] = best
          if (best !== center) changed++
        }
      }
      cur = next
      if (!changed) break
    }
    return { width: w, height: h, cells: cur }
  }

  // ---- all other algorithms: render to a single canvas ----
  const cv = document.createElement('canvas')
  cv.width = w
  cv.height = h
  const ctx = cv.getContext('2d', { willReadFrequently: true })!
  ctx.imageSmoothingEnabled = true
  ctx.imageSmoothingQuality = 'high'
  ctx.clearRect(0, 0, w, h)
  ctx.drawImage(img, 0, 0, w, h)

  const data = ctx.getImageData(0, 0, w, h).data

  if (algo === 'floyd') {
    // Floyd-Steinberg error diffusion
    const buf = new Float32Array(w * h * 3)
    for (let i = 0; i < w * h; i++) {
      buf[i * 3]     = data[i * 4]
      buf[i * 3 + 1] = data[i * 4 + 1]
      buf[i * 3 + 2] = data[i * 4 + 2]
    }
    const spread = (idx: number, er: number, eg: number, eb: number, f: number) => {
      buf[idx * 3]     += er * f
      buf[idx * 3 + 1] += eg * f
      buf[idx * 3 + 2] += eb * f
    }
    for (let y = 0; y < h; y++) {
      for (let x = 0; x < w; x++) {
        const idx = y * w + x
        if (data[idx * 4 + 3] < 128) { cells[idx] = null; continue }
        const r = clamp255(buf[idx * 3])
        const g = clamp255(buf[idx * 3 + 1])
        const b = clamp255(buf[idx * 3 + 2])
        const nc = nearestColor(r, g, b, palette, metric)
        cells[idx] = nc.code
        const er = r - nc.rgb[0], eg = g - nc.rgb[1], eb = b - nc.rgb[2]
        // Floyd-Steinberg: right 7/16, bottom-left 3/16, below 5/16, bottom-right 1/16
        if (x + 1 < w)           spread(idx + 1,     er, eg, eb, 7 / 16)
        if (y + 1 < h) {
          if (x > 0)             spread(idx + w - 1, er, eg, eb, 3 / 16)
          /*                */   spread(idx + w,     er, eg, eb, 5 / 16)
          if (x + 1 < w)        spread(idx + w + 1, er, eg, eb, 1 / 16)
        }
      }
    }
  } else if (algo === 'atkinson') {
    // Atkinson dithering: 6 neighbors each get 1/8 of error (2/8 discarded)
    const buf = new Float32Array(w * h * 3)
    for (let i = 0; i < w * h; i++) {
      buf[i * 3]     = data[i * 4]
      buf[i * 3 + 1] = data[i * 4 + 1]
      buf[i * 3 + 2] = data[i * 4 + 2]
    }
    const spread = (idx: number, er: number, eg: number, eb: number) => {
      if (idx < 0 || idx >= w * h) return
      buf[idx * 3]     += er / 8
      buf[idx * 3 + 1] += eg / 8
      buf[idx * 3 + 2] += eb / 8
    }
    for (let y = 0; y < h; y++) {
      for (let x = 0; x < w; x++) {
        const idx = y * w + x
        if (data[idx * 4 + 3] < 128) { cells[idx] = null; continue }
        const r = clamp255(buf[idx * 3])
        const g = clamp255(buf[idx * 3 + 1])
        const b = clamp255(buf[idx * 3 + 2])
        const nc = nearestColor(r, g, b, palette, metric)
        cells[idx] = nc.code
        const er = r - nc.rgb[0], eg = g - nc.rgb[1], eb = b - nc.rgb[2]
        // Atkinson: right×2, bottom-left, below, bottom-right, 2-below
        if (x + 1 < w)            spread(idx + 1,         er, eg, eb)
        if (x + 2 < w)            spread(idx + 2,         er, eg, eb)
        if (y + 1 < h) {
          if (x > 0)              spread(idx + w - 1,     er, eg, eb)
          /*                */    spread(idx + w,         er, eg, eb)
          if (x + 1 < w)         spread(idx + w + 1,     er, eg, eb)
        }
        if (y + 2 < h)            spread(idx + w * 2,     er, eg, eb)
      }
    }
  } else if (algo === 'bayer') {
    // Ordered Bayer dithering (4×4 matrix)
    const strength = 40
    for (let y = 0; y < h; y++) {
      for (let x = 0; x < w; x++) {
        const idx = y * w + x
        if (data[idx * 4 + 3] < 128) { cells[idx] = null; continue }
        const t = (BAYER4[y & 3][x & 3] / 16 - 0.5) * strength
        const br = clamp255(data[idx * 4]     + t)
        const bg = clamp255(data[idx * 4 + 1] + t)
        const bb = clamp255(data[idx * 4 + 2] + t)
        cells[idx] = nearestColor(br, bg, bb, palette, metric).code
      }
    }
  } else {
    // smooth — bilinear-scaled per-pixel nearest match
    for (let i = 0; i < w * h; i++) {
      if (data[i * 4 + 3] < 128) { cells[i] = null; continue }
      cells[i] = nearestColor(data[i * 4], data[i * 4 + 1], data[i * 4 + 2], palette, metric).code
    }
  }

  return { width: w, height: h, cells }
}

/** Count beads used per MARD code. */
export function countColors(grid: PerlerGrid): Map<string, number> {
  const m = new Map<string, number>()
  for (const c of grid.cells) {
    if (!c) continue
    m.set(c, (m.get(c) || 0) + 1)
  }
  return m
}

/**
 * Codes used by the pattern that a given tier does NOT contain
 * (= colors you'd be missing if you only owned that kit).
 */
export function paletteGaps(usedCodes: Iterable<string>, tierCodes: string[]): BeadColor[] {
  const tierSet = new Set(tierCodes)
  const gaps: BeadColor[] = []
  for (const code of usedCodes) {
    if (!tierSet.has(code) && MARD_COLORS[code]) gaps.push(MARD_COLORS[code])
  }
  return gaps
}

/** The substitute (平替) color for `color` within a given palette. */
export function substituteFor(
  color: BeadColor, palette: BeadColor[], metric: MatchMetric = 'lab',
): BeadColor {
  return nearestColor(color.rgb[0], color.rgb[1], color.rgb[2], palette, metric)
}

/** Pick black or white text for legibility on a given bead color. */
export function textOn(rgb: [number, number, number]): string {
  const lum = 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]
  return lum > 150 ? '#2a2030' : '#ffffff'
}
