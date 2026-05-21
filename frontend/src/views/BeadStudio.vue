<template>
  <div class="bead-studio">
    <BeadTabs />

    <!-- ===== Step 1: source + params ===== -->
    <div class="card setup-card">
      <div class="setup-grid">
        <!-- Upload zone -->
        <div class="upload-zone"
             :class="{ dragging: isDragging, filled: !!sourcePreview }"
             @click="pickFile"
             @dragover.prevent="isDragging = true"
             @dragleave.prevent="isDragging = false"
             @drop.prevent="onDrop">
          <img v-if="sourcePreview" :src="sourcePreview" class="upload-preview" alt="原图" />
          <div v-else class="upload-hint">
            <div class="upload-emoji">🖼️</div>
            <div class="upload-text">点击或拖入图片</div>
            <div class="upload-sub">JPG / PNG / GIF · 仅本地</div>
          </div>
          <input ref="fileInput" type="file" accept="image/*" hidden @change="onFileChange" />
        </div>

        <!-- Params -->
        <div class="params">
          <div class="form-row">
            <label>网格宽度（横向豆数）</label>
            <div class="flex items-center gap-3">
              <input type="range" min="16" max="180" step="1"
                     v-model.number="gridWidth" class="slider" />
              <input type="number" min="8" max="220"
                     v-model.number="gridWidth" class="input" style="width:80px;" />
            </div>
            <span class="form-hint" v-if="sourceImg">
              成品约 {{ gridWidth }} × {{ estHeight }} 颗豆
            </span>
          </div>

          <div class="form-row">
            <label>网格高度（纵向豆数）</label>
            <div class="flex items-center gap-3">
              <input type="range" min="16" max="180" step="1"
                     v-model.number="blankHeight" class="slider" />
              <input type="number" min="8" max="220"
                     v-model.number="blankHeight" class="input" style="width:80px;" />
            </div>
            <span class="form-hint">仅用于「新建空白画布」；导入图片时高度按比例自动计算</span>
          </div>

          <div class="form-row">
            <label>生成算法</label>
            <select class="select" v-model="algo">
              <option v-for="a in ALGO_OPTIONS" :key="a.id" :value="a.id">{{ a.label }}</option>
            </select>
            <span class="form-hint">{{ algoDesc }}</span>
          </div>

          <div class="form-row">
            <label>平替算法</label>
            <select class="select" v-model="matchMetric">
              <option v-for="m in MATCH_OPTIONS" :key="m.id" :value="m.id">{{ m.label }}</option>
            </select>
            <span class="form-hint">{{ matchDesc }}</span>
          </div>

          <div class="form-row">
            <label>色板模式</label>
            <div class="mode-toggle">
              <button class="mode-btn" :class="{ on: palMode === 'tier' }" @click="palMode = 'tier'">套装色板</button>
              <button class="mode-btn" :class="{ on: palMode === 'custom' }" @click="palMode = 'custom'">我的色板</button>
            </div>
          </div>

          <div class="form-row" v-if="palMode === 'tier'">
            <label>工作色板</label>
            <select class="select" v-model="tier">
              <option v-for="t in TIER_ORDER" :key="t" :value="t">{{ TIER_LABELS[t] }}</option>
            </select>
            <span class="form-hint">转换与画笔都使用此色板（共 {{ workingPalette.length }} 色）</span>
          </div>
          <div class="form-row" v-else>
            <label>我的色板</label>
            <span class="form-hint">{{ workingPalette.length > 0 ? `已选 ${workingPalette.length} 色，可在右侧「我的色板」面板管理` : '⚠ 尚未添加任何颜色，请在右侧面板添加' }}</span>
          </div>

          <button class="btn btn-primary convert-btn"
                  :disabled="!sourceImg || converting"
                  @click="convert(true)">
            {{ converting ? '转换中…' : grid ? '🔄 重新转换' : '✨ 转换成拼豆图纸' }}
          </button>
          <button class="btn btn-ghost convert-btn"
                  @click="newBlankGrid">
            ✏️ 新建空白画布（{{ gridWidth }} × {{ blankHeight }}）
          </button>
        </div>
      </div>
    </div>

    <!-- ===== Empty state ===== -->
    <div v-if="!grid" class="empty-state" style="margin-top:2rem;">
      <div class="empty-icon">🧩</div>
      <div class="empty-text">上传图片转换，或点上方「✏️ 新建空白画布」直接开画~</div>
    </div>

    <!-- ===== Workspace ===== -->
    <div v-else class="workspace">
      <!-- Canvas column -->
      <div class="canvas-col card">
        <!-- Toolbar -->
        <div class="toolbar">
          <div class="tool-group">
            <button v-for="t in tools" :key="t.id"
                    class="tool-btn" :class="{ on: tool === t.id }"
                    :title="`${t.label} (${t.key})`"
                    @click="tool = t.id">{{ t.icon }}</button>
          </div>
          <!-- brush / eraser size — Shift + wheel -->
          <div class="size-tag" v-show="tool === 'paint' || tool === 'erase'"
               title="按住 Shift + 滚轮调整大小">
            {{ tool === 'paint' ? '画笔' : '橡皮' }}
            <b class="mono">{{ activeBrushSize }}×{{ activeBrushSize }}</b>
            <span class="size-hint">⇧滚轮</span>
          </div>
          <!-- mirror-copy config -->
          <div class="mirror-cfg" v-show="tool === 'mirror'">
            <button class="tool-btn mini-btn" :class="{ on: mirrorAxis === 'v' }"
                    title="竖直对称线（左右镜像）" @click="mirrorAxis = 'v'">竖轴</button>
            <button class="tool-btn mini-btn" :class="{ on: mirrorAxis === 'h' }"
                    title="水平对称线（上下镜像）" @click="mirrorAxis = 'h'">横轴</button>
            <button class="tool-btn mini-btn" :class="{ on: mirrorDir === 1 }"
                    @click="mirrorDir = 1">{{ mirrorAxis === 'v' ? '左→右' : '上→下' }}</button>
            <button class="tool-btn mini-btn" :class="{ on: mirrorDir === -1 }"
                    @click="mirrorDir = -1">{{ mirrorAxis === 'v' ? '右→左' : '下→上' }}</button>
          </div>
          <div class="tool-divider"></div>
          <div class="tool-group">
            <button class="tool-btn" title="撤销 (Ctrl+Z)"
                    :disabled="!canUndo" @click="undo">↶</button>
            <button class="tool-btn" title="重做 (Ctrl+Shift+Z)"
                    :disabled="!canRedo" @click="redo">↷</button>
          </div>
          <div class="tool-divider"></div>
          <div class="tool-group">
            <button class="tool-btn" title="左右镜像" @click="flipH">⇄</button>
            <button class="tool-btn" title="上下翻转" @click="flipV">⇅</button>
            <button class="tool-btn" :class="{ on: transforming }"
                    title="自由变换（缩放 / 任意角度旋转）" @click="startTransform">⤢</button>
          </div>
          <div class="tool-divider"></div>
          <div class="cur-color">
            <span class="cur-swatch" :style="{ background: curColorHex }"></span>
            <span class="cur-label mono">{{ currentCode || '—' }}</span>
          </div>
          <button class="btn btn-ghost btn-sm" @click="outlineShape"
                  title="一键描边：沿图案外缘描一圈「当前色」（先在调色板选好颜色）">
            🖍 描边
          </button>
          <button class="btn btn-ghost btn-sm" @click="removeBackground"
                  title="一键去背景：从图纸四边洪水填充，清除与边缘相连、接近背景色的格子">
            ✂️ 去背景
          </button>
          <div class="tool-divider"></div>
          <div class="tool-group">
            <button class="tool-btn" title="缩小 (-)" @click="zoomBy(-1)">－</button>
            <span class="zoom-label mono">{{ Math.round(zoom * 100) }}%</span>
            <button class="tool-btn" title="放大 (+)" @click="zoomBy(1)">＋</button>
            <button class="tool-btn" title="适应窗口 (0)" @click="fitView">⊡</button>
          </div>
          <div class="tool-divider"></div>
          <span class="grid-size mono">{{ grid.width }} × {{ grid.height }}</span>
          <span class="grid-size mono" title="按豆径换算的成品尺寸">
            ≈ {{ finishedSize }}
          </span>
          <span class="kbd-hint" title="B 画笔 · E 橡皮 · G 魔棒画笔 · D 魔棒橡皮 · R 替换 · M 镜像复制 · I 取色 · H/空格 移动 · ⇧+滚轮 笔刷大小 · +/- 缩放 · 0 适应 · Ctrl+Z 撤销">⌨ 快捷键</span>
          <label class="export-opt" style="margin-left:auto;" title="在画布每颗豆上显示 MARD 色号">
            <input type="checkbox" v-model="showLabels" />
            <span>标色号</span>
          </label>
          <button class="btn btn-ghost btn-sm" @click="showExportDialog = true">
            ⬇ 导出
          </button>
          <button class="btn btn-ghost btn-sm" @click="showShopDialog = true">
            🛒 购买
          </button>
        </div>

        <!-- Live params — adjustable while editing -->
        <div class="param-bar">
          <label class="pb-cell pb-wide">
            <span class="pb-label">网格宽度 · {{ grid.width }}×{{ grid.height }}</span>
            <input type="range" min="16" max="180" step="1"
                   v-model.number="gridWidth" class="slider" />
          </label>
          <label class="pb-cell">
            <span class="pb-label">豆数</span>
            <input type="number" min="16" max="180"
                   v-model.number="gridWidth" class="input" />
          </label>
          <label class="pb-cell">
            <span class="pb-label">算法</span>
            <select class="select" v-model="algo">
              <option v-for="a in ALGO_OPTIONS" :key="a.id" :value="a.id">{{ a.label }}</option>
            </select>
          </label>
          <label class="pb-cell">
            <span class="pb-label">平替</span>
            <select class="select" v-model="matchMetric">
              <option v-for="m in MATCH_OPTIONS" :key="m.id" :value="m.id">{{ m.label }}</option>
            </select>
          </label>
          <label class="pb-cell">
            <span class="pb-label">色板</span>
            <select class="select" v-model="tier" :disabled="palMode === 'custom'">
              <option v-for="t in TIER_ORDER" :key="t" :value="t">{{ t }} 色</option>
            </select>
          </label>
          <label class="pb-cell">
            <span class="pb-label">豆型</span>
            <select class="select" v-model="beadShape">
              <option value="circle">圆形</option>
              <option value="square">方形</option>
              <option value="fill">填满</option>
            </select>
          </label>
          <label class="pb-cell">
            <span class="pb-label">豆径</span>
            <div class="bead-size-toggle">
              <button class="pill-btn" :class="{ on: beadSize === 2.6 }" @click="beadSize = 2.6">2.6mm</button>
              <button class="pill-btn" :class="{ on: beadSize === 5 }" @click="beadSize = 5">5mm</button>
              <button class="pill-btn pill-sub" :class="{ on: beadSize === 3 }" @click="beadSize = 3" title="3mm（少量使用）">3</button>
            </div>
          </label>
          <span class="pb-hint" :class="{ busy: converting }">
            {{ converting ? '重新生成中…' : '改宽度/算法/色板会从原图重新生成 · 可 Ctrl+Z 撤销' }}
          </span>
        </div>

        <!-- Reference image overlay -->
        <div class="ref-section">
          <div class="ref-toggle" @click="showRefSection = !showRefSection">
            <span class="ref-toggle-icon">{{ showRefSection ? '▼' : '▶' }}</span>
            <span>参考图叠加</span>
            <span v-if="refImage" class="ref-badge">已加载</span>
          </div>
          <div v-if="showRefSection" class="ref-body">
            <div v-if="!refImage" class="ref-upload"
                 @click="refFileInput?.click()" @dragover.prevent
                 @drop.prevent="onRefDrop">
              <span>＋ 拖入或点击添加参考图</span>
              <input ref="refFileInput" type="file" accept="image/*" hidden @change="onRefFileChange" />
            </div>
            <div v-else class="ref-controls">
              <img :src="refPreview" class="ref-thumb" alt="参考图" />
              <label class="ref-slider-label">
                <span>透明度</span>
                <input type="range" min="0" max="1" step="0.05"
                       v-model.number="refOpacity" class="slider ref-slider" @input="render" />
                <span class="mono">{{ Math.round(refOpacity * 100) }}%</span>
              </label>
              <button class="ref-lock-btn" :class="{ locked: refLocked }"
                      @click="refLocked = !refLocked"
                      :title="refLocked ? '已锁定' : '点击锁定参考图'">
                {{ refLocked ? '🔒' : '🔓' }}
              </button>
              <button class="btn btn-ghost btn-xs" :disabled="refLocked" @click="removeRef">
                移除
              </button>
            </div>
          </div>
        </div>

        <!-- Canvas -->
        <div ref="wrapRef" class="canvas-wrap" :class="{ xforming: transforming }"
             @wheel.prevent="onWheel"
             @mousedown="onDown"
             @mousemove="onMove"
             @mouseup="onUp"
             @mouseleave="onLeave"
             @dragover.prevent
             @drop.prevent="onDrop">
          <canvas ref="canvasRef"></canvas>
          <div v-if="hoverTip && !transforming" class="hover-tip" :style="hoverTipStyle">
            {{ hoverTip }}
          </div>
          <!-- free-transform action bar -->
          <div v-if="transforming" class="xform-bar">
            <span class="xform-title">自由变换</span>
            <span class="xform-info mono">缩放 {{ xformScalePct }}% · 旋转 {{ xformAngleDeg }}°</span>
            <button class="btn btn-sm btn-primary" @click="applyTransform">✓ 应用</button>
            <button class="btn btn-sm btn-ghost" @click="cancelTransform">✕ 取消</button>
          </div>
        </div>
      </div>

      <!-- Side column -->
      <div class="side-col">
        <!-- Palette — grouped by A/B/C… series, scrollable -->
        <div class="card side-card">
          <div class="side-head">
            调色板 · {{ palMode === 'custom' ? '我的色板' : TIER_LABELS[tier] }}
            <span class="side-count">{{ workingPalette.length }} 色</span>
          </div>
          <div class="palette-scroll">
            <div v-for="grp in paletteGroups" :key="grp.key" class="pal-group">
              <div class="pal-group-label">
                <span class="pal-group-key">{{ grp.key }}</span>
                <span>{{ grp.name }}</span>
                <span class="pal-group-n">{{ grp.colors.length }}</span>
              </div>
              <div class="palette-grid">
                <button v-for="c in grp.colors" :key="c.code"
                        class="pal-swatch"
                        :class="{ on: currentCode === c.code, used: usedCodes.has(c.code) }"
                        :style="{ background: c.hex }"
                        :title="`${c.code} ${c.name}`"
                        @click="selectColor(c.code)"></button>
              </div>
            </div>
          </div>
        </div>

        <!-- My palette management -->
        <div class="card side-card my-pal-card">
          <div class="side-head">
            我的色板
            <span class="side-count">{{ myPaletteCodes.length }} 色</span>
          </div>
          <div class="my-pal-mode">
            <button class="mode-btn" :class="{ on: palMode === 'tier' }" @click="palMode = 'tier'">套装模式</button>
            <button class="mode-btn" :class="{ on: palMode === 'custom' }" @click="palMode = 'custom'">自定义模式</button>
          </div>
          <button class="btn btn-primary btn-sm my-pal-pick-btn" @click="showPalettePicker = true">
            🎨 打开色卡选择
          </button>
          <div class="my-pal-add">
            <input class="input my-pal-input" v-model="myPaletteInput"
                   placeholder="或输入色号，如 A4"
                   @keydown.enter="addToMyPalette" />
            <button class="btn btn-sm btn-ghost" @click="addToMyPalette">添加</button>
          </div>
          <div class="my-pal-actions">
            <button class="btn btn-ghost btn-xs" @click="importFromUsed" title="把当前图纸用到的色号全导入">从图纸导入</button>
            <button class="btn btn-ghost btn-xs" @click="clearMyPalette" :disabled="myPaletteCodes.length === 0">清空</button>
          </div>
          <div v-if="myPaletteCodes.length === 0" class="side-empty">
            尚未添加色号，点击上方「打开色卡选择」挑选颜色
          </div>
          <div v-else class="my-pal-grid">
            <button v-for="code in myPaletteCodes" :key="code"
                    class="my-pal-chip"
                    :style="{ background: MARD_COLORS[code]?.hex || '#ccc',
                              color: textOn(MARD_COLORS[code]?.rgb || [200,200,200]) }"
                    :title="`${code} ${MARD_COLORS[code]?.name || ''} — 点击移除`"
                    @click="removeFromMyPalette(code)">
              <span class="chip-code">{{ code }}</span>
              <span class="chip-x">✕</span>
            </button>
          </div>
        </div>

        <!-- Color usage list -->
        <div class="card side-card">
          <div class="side-head">
            颜色用量
            <span class="side-count">{{ colorList.length }} 色 / {{ totalBeads }} 颗</span>
          </div>
          <div v-if="colorList.length === 0" class="side-empty">图纸还是空的</div>
          <div v-else class="color-list">
            <div v-for="row in colorList" :key="row.code" class="color-row"
                 @click="selectColor(row.code)">
              <span class="cl-swatch" :style="{ background: row.hex }"></span>
              <span class="cl-code mono">{{ row.code }}</span>
              <span class="cl-name">{{ row.name }}</span>
              <span class="cl-count mono">{{ row.count }}</span>
            </div>
          </div>
        </div>

        <!-- Gap analysis — missing colors + their 平替 substitute -->
        <div class="card side-card">
          <div class="side-head">MARD 套装缺色对比</div>
          <div class="side-sub">缺色 → 该套装内的平替色（按「{{ matchDesc }}」）</div>
          <div v-for="g in gapRows" :key="g.tier" class="gap-block">
            <div class="gap-head">
              <span class="gap-tier">{{ g.label }}</span>
              <span class="gap-stat" :class="{ ok: g.gaps.length === 0 }">
                {{ g.gaps.length === 0 ? '✓ 全部覆盖' : `缺 ${g.gaps.length} 色` }}
              </span>
            </div>
            <div v-if="g.gaps.length" class="gap-pairs">
              <div v-for="p in g.gaps" :key="p.color.code" class="gap-pair"
                   :title="`缺 ${p.color.code} ${p.color.name} → 平替 ${p.sub.code} ${p.sub.name}`">
                <span class="gap-swatch miss" :style="{ background: p.color.hex }"></span>
                <span class="gap-arrow">→</span>
                <span class="gap-swatch" :style="{ background: p.sub.hex }"></span>
                <span class="gap-sub-code mono">{{ p.sub.code }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- Export Dialog -->
  <BeadExportDialog v-if="showExportDialog && grid"
    :grid="grid!" :bead-shape="beadShape" :total-beads="totalBeads"
    :mard-colors="MARD_COLORS"
    @close="showExportDialog = false"
    @export-png="handleExportPng"
    @export-jpg="handleExportJpg"
    @export-svg="handleExportSvg"
    @export-csv="handleExportCsv" />

  <!-- Shop Dialog -->
  <BeadShopDialog v-if="showShopDialog && grid"
    :used-colors="usedCodes" :mard-colors="MARD_COLORS"
    @close="showShopDialog = false" />

  <!-- Custom palette picker -->
  <BeadPalettePicker v-if="showPalettePicker"
    :codes="myPaletteCodes"
    @apply="onPaletteApply"
    @close="showPalettePicker = false" />
</template>

<script lang="ts">
// explicit name so <keep-alive :include="['BeadStudio']"> matches this view
export default { name: 'BeadStudio' }
</script>

<script setup lang="ts">
import { ref, computed, shallowRef, onBeforeUnmount, onActivated, onDeactivated, watch, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import {
  MARD_COLORS, MARD_TIERS, TIER_LABELS, TIER_ORDER, MARD_GROUPS,
  type Tier, type BeadColor,
} from '../data/mardPalettes'
import {
  imageToGrid, countColors, paletteGaps, substituteFor, textOn,
  ALGO_OPTIONS, MATCH_OPTIONS, type PerlerGrid, type ConvertAlgo, type MatchMetric,
} from '../composables/usePerler'
import BeadTabs from '../components/BeadTabs.vue'
import BeadExportDialog from '../components/BeadExportDialog.vue'
import BeadShopDialog from '../components/BeadShopDialog.vue'
import BeadPalettePicker from '../components/BeadPalettePicker.vue'

type Tool = 'paint' | 'erase' | 'wand' | 'wanderase' | 'replace' | 'pick' | 'pan' | 'mirror'
type BeadShape = 'circle' | 'square' | 'fill'

// ---- state ----
const fileInput = ref<HTMLInputElement | null>(null)
const wrapRef = ref<HTMLDivElement | null>(null)
const canvasRef = ref<HTMLCanvasElement | null>(null)

const sourceImg = shallowRef<HTMLImageElement | null>(null)
const sourcePreview = ref('')
const isDragging = ref(false)

const gridWidth = ref(56)
const blankHeight = ref(56)                // height for "new blank canvas"
const tier = ref<Tier>('264')
const algo = ref<ConvertAlgo>('smooth')
const matchMetric = ref<MatchMetric>('lab')
const showLabels = ref(false)   // show MARD codes on every bead (canvas + export)
const beadShape = ref<BeadShape>('circle')
const beadSize = ref(2.6)                 // physical bead diameter, mm
const brushSize = ref(1)                  // paint brush diameter in cells (Shift+wheel)
const eraserSize = ref(1)                 // eraser diameter in cells (Shift+wheel)

// ---- custom palette (persisted to localStorage) ----
const palMode = ref<'tier' | 'custom'>('tier')
const myPaletteCodes = ref<string[]>(
  JSON.parse(localStorage.getItem('bead-my-palette') || '[]'),
)
const myPaletteInput = ref('')

const grid = shallowRef<PerlerGrid | null>(null)
const gridVersion = ref(0)
const converting = ref(false)

// reference image overlay
const refImage = shallowRef<HTMLImageElement | null>(null)
const refPreview = ref('')
const refOpacity = ref(0.35)
const refLocked = ref(false)
const showRefSection = ref(false)
const refFileInput = ref<HTMLInputElement | null>(null)

// dialogs
const showExportDialog = ref(false)
const showShopDialog = ref(false)
const showPalettePicker = ref(false)

// ---- undo / redo history ----
interface GridSnap { width: number; height: number; cells: (string | null)[] }
const undoStack: GridSnap[] = []
const redoStack: GridSnap[] = []
const histVer = ref(0)
const canUndo = computed(() => { void histVer.value; return undoStack.length > 0 })
const canRedo = computed(() => { void histVer.value; return redoStack.length > 0 })

const algoDesc = computed(() =>
  ALGO_OPTIONS.find(a => a.id === algo.value)?.desc || '',
)
const matchDesc = computed(() =>
  MATCH_OPTIONS.find(m => m.id === matchMetric.value)?.desc || '',
)

const tool = ref<Tool>('paint')
const currentCode = ref('')
const zoom = ref(1)
const offset = ref({ x: 28, y: 28 })
const hover = ref<{ x: number; y: number } | null>(null)

const tools: { id: Tool; icon: string; label: string; key: string }[] = [
  { id: 'paint',     icon: '🖌', label: '画笔', key: 'B' },
  { id: 'erase',     icon: '🧽', label: '橡皮', key: 'E' },
  { id: 'wand',      icon: '🪄', label: '魔棒画笔', key: 'G' },
  { id: 'wanderase', icon: '🧹', label: '魔棒橡皮', key: 'D' },
  { id: 'replace',   icon: '🔁', label: '同色替换', key: 'R' },
  { id: 'mirror',    icon: '🪞', label: '镜像复制', key: 'M' },
  { id: 'pick',      icon: '💉', label: '取色', key: 'I' },
  { id: 'pan',       icon: '✋', label: '移动', key: 'H' },
]

// mirror-copy axis configuration
const mirrorAxis = ref<'v' | 'h'>('v')   // vertical or horizontal symmetry line
const mirrorDir = ref<1 | -1>(1)         // v: 1=左→右 -1=右→左 ; h: 1=上→下 -1=下→上

// active brush/eraser size shown in the toolbar
const activeBrushSize = computed(() =>
  tool.value === 'paint' ? brushSize.value : eraserSize.value,
)

const BASE_CELL = 18
const RULER = 26

// ---- derived ----
const estHeight = computed(() => {
  const img = sourceImg.value
  if (!img) return 0
  const ratio = (img.naturalHeight || 1) / (img.naturalWidth || 1)
  return Math.max(1, Math.round(gridWidth.value * ratio))
})
const workingPalette = computed<BeadColor[]>(() => {
  if (palMode.value === 'custom') {
    return myPaletteCodes.value.map(c => MARD_COLORS[c]).filter(Boolean)
  }
  return MARD_TIERS[tier.value].map(c => MARD_COLORS[c]).filter(Boolean)
})
// Palette grouped by A/B/C… series for the scrollable picker.
const paletteGroups = computed(() => {
  const byKey = new Map<string, BeadColor[]>()
  for (const c of workingPalette.value) {
    const k = c.code.match(/^[A-Z]+/)?.[0] || c.code
    if (!byKey.has(k)) byKey.set(k, [])
    byKey.get(k)!.push(c)
  }
  return MARD_GROUPS
    .map(g => ({ key: g.key, name: g.name, colors: byKey.get(g.key) || [] }))
    .filter(g => g.colors.length > 0)
})
const curColorHex = computed(() => MARD_COLORS[currentCode.value]?.hex || '#ffffff')

// Physical finished dimensions from bead diameter (mm → cm).
const finishedSize = computed(() => {
  const g = grid.value
  if (!g) return ''
  const w = (g.width * beadSize.value / 10)
  const h = (g.height * beadSize.value / 10)
  return `${w.toFixed(1)} × ${h.toFixed(1)} cm`
})

const colorCounts = computed(() => {
  gridVersion.value  // dependency
  return grid.value ? countColors(grid.value) : new Map<string, number>()
})
const usedCodes = computed(() => new Set(colorCounts.value.keys()))
const totalBeads = computed(() => {
  let n = 0
  for (const v of colorCounts.value.values()) n += v
  return n
})
const colorList = computed(() => {
  return [...colorCounts.value.entries()]
    .map(([code, count]) => ({
      code, count,
      name: MARD_COLORS[code]?.name || code,
      hex: MARD_COLORS[code]?.hex || '#ccc',
    }))
    .sort((a, b) => b.count - a.count)
})
const gapRows = computed(() => {
  const used = usedCodes.value
  return (['72', '96', '216', '264'] as Tier[]).map(t => {
    const tierPal = MARD_TIERS[t].map(c => MARD_COLORS[c]).filter(Boolean)
    // each missing color paired with its 平替 (substitute) in this kit
    const gaps = paletteGaps(used, MARD_TIERS[t]).map(color => ({
      color,
      sub: substituteFor(color, tierPal, matchMetric.value),
    }))
    return { tier: t, label: TIER_LABELS[t], gaps }
  })
})

// ---- hover tooltip ----
const hoverTip = computed(() => {
  if (!hover.value || !grid.value) return ''
  const { x, y } = hover.value
  const code = grid.value.cells[y * grid.value.width + x]
  if (!code) return `(${x + 1}, ${y + 1}) 空`
  const c = MARD_COLORS[code]
  return `(${x + 1}, ${y + 1}) ${code} ${c?.name || ''}`
})
const hoverTipStyle = ref<Record<string, string>>({})

// ---- file loading ----
function pickFile() { fileInput.value?.click() }
function onFileChange(e: Event) {
  const f = (e.target as HTMLInputElement).files?.[0]
  if (f) loadFile(f)
}
function onDrop(e: DragEvent) {
  isDragging.value = false
  const f = e.dataTransfer?.files?.[0]
  if (f) loadFile(f)
}
function loadFile(file: File) {
  if (!file.type.startsWith('image/')) {
    ElMessage.warning('请选择图片文件')
    return
  }
  const reader = new FileReader()
  reader.onload = () => {
    const img = new Image()
    img.onload = () => {
      sourceImg.value = img
      sourcePreview.value = String(reader.result)
      // 拖入 / 选择图片后立即转换成拼豆图纸（无论当前是空白画布还是已有图纸）
      convert(true)
    }
    img.onerror = () => ElMessage.error('图片解码失败')
    img.src = String(reader.result)
  }
  reader.readAsDataURL(file)
}

// ---- reference image ----
function onRefFileChange(e: Event) {
  const f = (e.target as HTMLInputElement).files?.[0]
  if (f) loadRefFile(f)
}
function onRefDrop(e: DragEvent) {
  const f = e.dataTransfer?.files?.[0]
  if (f) loadRefFile(f)
}
function loadRefFile(file: File) {
  if (!file.type.startsWith('image/')) return
  const reader = new FileReader()
  reader.onload = () => {
    const img = new Image()
    img.onload = () => {
      refImage.value = img
      refPreview.value = String(reader.result)
      render()
    }
    img.src = String(reader.result)
  }
  reader.readAsDataURL(file)
}
function removeRef() {
  if (refLocked.value) return
  refImage.value = null
  refPreview.value = ''
  render()
}

// ---- conversion ----
async function convert(refit = true) {
  if (!sourceImg.value) return
  if (workingPalette.value.length === 0) {
    if (refit) ElMessage.warning('当前色板为空，请先添加颜色或切换到套装色板')
    return
  }
  // A live re-convert (width / algorithm / palette tweak) snapshots the
  // current grid so Ctrl+Z returns to the previous setting.
  // A button conversion (refit) starts fresh, discarding edit history.
  if (!refit && grid.value) pushHistory()
  converting.value = true
  await nextTick()
  try {
    grid.value = imageToGrid(
      sourceImg.value, gridWidth.value, workingPalette.value,
      algo.value, matchMetric.value,
    )
    gridVersion.value++
    if (refit) {
      // a fresh conversion from the button invalidates the edit history
      undoStack.length = 0
      redoStack.length = 0
    }
    histVer.value++
    // default paint color = most-used color
    const first = [...countColors(grid.value).entries()].sort((a, b) => b[1] - a[1])[0]
    if (!currentCode.value || !workingPalette.value.some(c => c.code === currentCode.value)) {
      currentCode.value = first?.[0] || workingPalette.value[0]?.code || ''
    }
    await nextTick()
    syncCanvasSize()
    if (refit) fitView()
    else render()
  } catch (e: any) {
    ElMessage.error('转换失败：' + (e?.message || e))
  } finally {
    converting.value = false
  }
}

// ---- new blank canvas (draw from scratch, no image) ----
function newBlankGrid() {
  if (workingPalette.value.length === 0) {
    ElMessage.warning('当前色板为空，请先切换到套装色板或添加颜色')
    return
  }
  const w = Math.max(8, Math.min(220, Math.round(gridWidth.value)))
  const h = Math.max(8, Math.min(220, Math.round(blankHeight.value)))
  sourceImg.value = null
  sourcePreview.value = ''
  grid.value = { width: w, height: h, cells: new Array(w * h).fill(null) }
  gridVersion.value++
  undoStack.length = 0
  redoStack.length = 0
  histVer.value++
  if (!currentCode.value || !workingPalette.value.some(c => c.code === currentCode.value)) {
    currentCode.value = workingPalette.value[0]?.code || ''
  }
  tool.value = 'paint'
  nextTick(() => { syncCanvasSize(); fitView() })
}

/** Nearest-neighbour resample of the current grid to a new size. */
function resampleGrid(newW: number, newH: number) {
  const g = grid.value
  if (!g) return
  newW = Math.max(1, Math.round(newW))
  newH = Math.max(1, Math.round(newH))
  if (newW === g.width && newH === g.height) return
  const cells: (string | null)[] = new Array(newW * newH)
  for (let y = 0; y < newH; y++) {
    const sy = Math.min(g.height - 1, Math.floor(y * g.height / newH))
    for (let x = 0; x < newW; x++) {
      const sx = Math.min(g.width - 1, Math.floor(x * g.width / newW))
      cells[y * newW + x] = g.cells[sy * g.width + sx]
    }
  }
  grid.value = { width: newW, height: newH, cells }
  gridVersion.value++
}

// Tweaking width / algorithm / palette re-converts from the source image
// (debounced, undoable — convert() snapshots the previous grid first).
// For a blank / hand-drawn canvas (no source image) a width change instead
// resizes the current grid by resampling it.
// `suppressReconv` blocks the watch while undo/redo syncs the width slider.
let suppressReconv = false
let reconvTimer: number | undefined
watch([gridWidth, algo, tier, matchMetric, palMode, myPaletteCodes], (nv, ov) => {
  if (suppressReconv || !grid.value || transforming.value) return
  if (reconvTimer) clearTimeout(reconvTimer)
  if (sourceImg.value) {
    // image-based grid → re-quantize from the source
    reconvTimer = window.setTimeout(() => convert(false), 240)
  } else if (nv[0] !== ov[0]) {
    // blank / hand-drawn canvas → width change resizes (resamples) the grid
    reconvTimer = window.setTimeout(() => {
      const g = grid.value
      if (!g) return
      const nw = Math.max(1, Math.round(gridWidth.value))
      if (nw === g.width) return
      pushHistory()
      resampleGrid(nw, Math.max(1, Math.round(nw * g.height / g.width)))
      render()
    }, 240)
  }
})

// Persist custom palette to localStorage
watch(myPaletteCodes, (codes) => {
  localStorage.setItem('bead-my-palette', JSON.stringify(codes))
}, { deep: true })

function selectColor(code: string) {
  currentCode.value = code
  if (tool.value === 'erase' || tool.value === 'pan' || tool.value === 'mirror') {
    tool.value = 'paint'
  }
}

// ---- custom palette management ----
function addToMyPalette() {
  const code = myPaletteInput.value.trim().toUpperCase()
  if (!code) return
  if (!MARD_COLORS[code]) {
    ElMessage.warning(`色号 ${code} 不在 MARD 色卡中`)
    return
  }
  if (myPaletteCodes.value.includes(code)) {
    ElMessage.info(`${code} 已在色板中`)
    return
  }
  myPaletteCodes.value = [...myPaletteCodes.value, code]
  myPaletteInput.value = ''
}
function removeFromMyPalette(code: string) {
  myPaletteCodes.value = myPaletteCodes.value.filter(c => c !== code)
}
function clearMyPalette() {
  myPaletteCodes.value = []
}
function importFromUsed() {
  if (!grid.value) { ElMessage.info('请先生成图纸'); return }
  const existing = new Set(myPaletteCodes.value)
  const newCodes = [...usedCodes.value].filter(c => !existing.has(c))
  if (newCodes.length === 0) { ElMessage.info('当前图纸的颜色已全在色板中'); return }
  myPaletteCodes.value = [...myPaletteCodes.value, ...newCodes]
  ElMessage.success(`已从图纸导入 ${newCodes.length} 个色号`)
}
function onPaletteApply(codes: string[]) {
  myPaletteCodes.value = codes
  ElMessage.success(`我的色板已更新：${codes.length} 色`)
}

// ---- canvas sizing ----
function syncCanvasSize() {
  const cv = canvasRef.value, wrap = wrapRef.value
  if (!cv || !wrap) return
  const dpr = window.devicePixelRatio || 1
  const w = wrap.clientWidth, h = wrap.clientHeight
  cv.width = Math.round(w * dpr)
  cv.height = Math.round(h * dpr)
  cv.style.width = w + 'px'
  cv.style.height = h + 'px'
  const ctx = cv.getContext('2d')!
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
  render()
}

function fitView() {
  const g = grid.value, wrap = wrapRef.value
  if (!g || !wrap) return
  const availW = wrap.clientWidth - RULER - 24
  const availH = wrap.clientHeight - RULER - 24
  const z = Math.min(availW / (g.width * BASE_CELL), availH / (g.height * BASE_CELL))
  zoom.value = Math.max(0.15, Math.min(z, 4))
  const cell = BASE_CELL * zoom.value
  offset.value = {
    x: Math.max(8, (wrap.clientWidth - RULER - g.width * cell) / 2),
    y: Math.max(8, (wrap.clientHeight - RULER - g.height * cell) / 2),
  }
  render()
}

function zoomBy(dir: number) {
  const wrap = wrapRef.value
  if (!wrap) return
  zoomAt(wrap.clientWidth / 2, wrap.clientHeight / 2, dir > 0 ? 1.25 : 1 / 1.25)
}
function zoomAt(cx: number, cy: number, factor: number) {
  const oldZoom = zoom.value
  const newZoom = Math.max(0.15, Math.min(oldZoom * factor, 8))
  if (newZoom === oldZoom) return
  // keep the grid point under the cursor stable
  const gx = (cx - RULER - offset.value.x) / (BASE_CELL * oldZoom)
  const gy = (cy - RULER - offset.value.y) / (BASE_CELL * oldZoom)
  zoom.value = newZoom
  offset.value = {
    x: cx - RULER - gx * BASE_CELL * newZoom,
    y: cy - RULER - gy * BASE_CELL * newZoom,
  }
  render()
}
function onWheel(e: WheelEvent) {
  const d = e.deltaY !== 0 ? e.deltaY : e.deltaX
  // Shift + wheel adjusts brush / eraser size
  if (e.shiftKey && (tool.value === 'paint' || tool.value === 'erase')) {
    const step = d < 0 ? 1 : -1
    const size = tool.value === 'paint' ? brushSize : eraserSize
    size.value = Math.min(20, Math.max(1, size.value + step))
    render()
    return
  }
  const rect = wrapRef.value!.getBoundingClientRect()
  zoomAt(e.clientX - rect.left, e.clientY - rect.top, d < 0 ? 1.15 : 1 / 1.15)
}

// ---- pointer → cell ----
function cellAt(e: MouseEvent): { x: number; y: number } | null {
  const g = grid.value, wrap = wrapRef.value
  if (!g || !wrap) return null
  const rect = wrap.getBoundingClientRect()
  const cell = BASE_CELL * zoom.value
  const x = Math.floor((e.clientX - rect.left - RULER - offset.value.x) / cell)
  const y = Math.floor((e.clientY - rect.top - RULER - offset.value.y) / cell)
  if (x < 0 || y < 0 || x >= g.width || y >= g.height) return null
  return { x, y }
}

// ---- undo / redo ----
function snapGrid(): GridSnap {
  const g = grid.value!
  return { width: g.width, height: g.height, cells: g.cells.slice() }
}
function pushHistory() {
  if (!grid.value) return
  undoStack.push(snapGrid())
  if (undoStack.length > 60) undoStack.shift()
  redoStack.length = 0
  histVer.value++
}
// keep the width slider in sync with a restored snapshot, without the
// change re-triggering an image re-conversion
function syncWidthFromGrid() {
  const g = grid.value
  if (g && gridWidth.value !== g.width) {
    suppressReconv = true
    gridWidth.value = g.width
    nextTick(() => { suppressReconv = false })
  }
}
function undo() {
  if (!grid.value || !undoStack.length) return
  redoStack.push(snapGrid())
  grid.value = undoStack.pop()!
  syncWidthFromGrid()
  gridVersion.value++
  histVer.value++
  nextTick(() => { syncCanvasSize(); render() })
}
function redo() {
  if (!grid.value || !redoStack.length) return
  undoStack.push(snapGrid())
  grid.value = redoStack.pop()!
  syncWidthFromGrid()
  gridVersion.value++
  histVer.value++
  nextTick(() => { syncCanvasSize(); render() })
}

// ---- flip / rotate ----
function flipH() {
  const g = grid.value
  if (!g) return
  pushHistory()
  const w = g.width, h = g.height
  const n = g.cells.slice()
  for (let y = 0; y < h; y++)
    for (let x = 0; x < w; x++)
      n[y * w + (w - 1 - x)] = g.cells[y * w + x]
  grid.value = { ...g, cells: n }
  gridVersion.value++
  render()
}
function flipV() {
  const g = grid.value
  if (!g) return
  pushHistory()
  const w = g.width, h = g.height
  const n = g.cells.slice()
  for (let y = 0; y < h; y++)
    for (let x = 0; x < w; x++)
      n[(h - 1 - y) * w + x] = g.cells[y * w + x]
  grid.value = { ...g, cells: n }
  gridVersion.value++
  render()
}

// ---- one-click outline ----
// Wrap the drawn shape in a 1-cell border of the currently-selected color:
// every empty cell touching a filled cell (8-neighbourhood) becomes outline.
function outlineShape() {
  const g = grid.value
  if (!g) return
  if (!currentCode.value) {
    ElMessage.warning('请先在右侧调色板选择描边颜色')
    return
  }
  const w = g.width, h = g.height
  const mark: number[] = []
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      const idx = y * w + x
      if (g.cells[idx] !== null) continue        // only empty cells become outline
      let adj = false
      for (let dy = -1; dy <= 1 && !adj; dy++) {
        for (let dx = -1; dx <= 1; dx++) {
          if (!dx && !dy) continue
          const nx = x + dx, ny = y + dy
          if (nx < 0 || nx >= w || ny < 0 || ny >= h) continue
          if (g.cells[ny * w + nx] !== null) { adj = true; break }
        }
      }
      if (adj) mark.push(idx)
    }
  }
  if (!mark.length) {
    ElMessage.info('没有可描边的边缘（图纸为空或已填满）')
    return
  }
  pushHistory()
  for (const idx of mark) g.cells[idx] = currentCode.value
  gridVersion.value++
  render()
  ElMessage.success(`已描边 ${mark.length} 颗豆`)
}

// ---- one-click background removal ----
// Flood-fill inward from all four edges, clearing cells whose color is close
// to the dominant border color. Identifies the subject by what's left.
// Works best on photos / stickers with a relatively uniform background.
function removeBackground() {
  const g = grid.value
  if (!g) return
  const w = g.width, h = g.height
  // dominant border code = the background color
  const borderCount = new Map<string, number>()
  const tally = (code: string | null) => {
    if (code) borderCount.set(code, (borderCount.get(code) || 0) + 1)
  }
  for (let x = 0; x < w; x++) { tally(g.cells[x]); tally(g.cells[(h - 1) * w + x]) }
  for (let y = 0; y < h; y++) { tally(g.cells[y * w]); tally(g.cells[y * w + w - 1]) }
  let bgCode = '', bgN = 0
  for (const [code, n] of borderCount) if (n > bgN) { bgN = n; bgCode = code }
  const bg = bgCode ? MARD_COLORS[bgCode] : null
  if (!bg) { ElMessage.info('未检测到背景色（图纸四边为空）'); return }
  // a cell is "background" if its color is close enough to the border color
  const TOL = 11000   // ≈ 60 / channel, sum of squared RGB difference
  const isBg = (i: number): boolean => {
    const code = g.cells[i]
    if (!code) return false
    const c = MARD_COLORS[code]
    if (!c) return false
    const dr = c.rgb[0] - bg.rgb[0], dgr = c.rgb[1] - bg.rgb[1], db = c.rgb[2] - bg.rgb[2]
    return dr * dr + dgr * dgr + db * db <= TOL
  }
  // flood inward from every border cell — only edge-connected background goes
  const visited = new Uint8Array(w * h)
  const stack: number[] = []
  const seed = (i: number) => { if (!visited[i]) { visited[i] = 1; stack.push(i) } }
  for (let x = 0; x < w; x++) { seed(x); seed((h - 1) * w + x) }
  for (let y = 0; y < h; y++) { seed(y * w); seed(y * w + w - 1) }
  const removed: number[] = []
  while (stack.length) {
    const i = stack.pop()!
    if (!isBg(i)) continue
    removed.push(i)
    const x = i % w, y = (i / w) | 0
    if (x + 1 < w) seed(i + 1)
    if (x - 1 >= 0) seed(i - 1)
    if (y + 1 < h) seed(i + w)
    if (y - 1 >= 0) seed(i - w)
  }
  if (!removed.length) { ElMessage.info('未检测到可去除的背景'); return }
  pushHistory()
  for (const i of removed) g.cells[i] = null
  gridVersion.value++
  render()
  ElMessage.success(`已去除背景 ${removed.length} 颗豆`)
}

// ---- free transform (PS-style Ctrl+T) ----
interface XBox { cx: number; cy: number; halfW: number; halfH: number; angle: number }
const transforming = ref(false)
const xbox = ref<XBox>({ cx: 0, cy: 0, halfW: 0, halfH: 0, angle: 0 })
let xW0 = 0, xH0 = 0                              // original grid dimensions
let xCanvas: HTMLCanvasElement | null = null      // 1px-per-cell content snapshot
let xDrag: {
  mode: 'scale' | 'rotate' | 'move'
  handle: number
  anchor: { x: number; y: number }
  anchorLocal: { x: number; y: number }
  start: XBox
  startMouse: { x: number; y: number }
  startPointerAngle: number
} | null = null

const OPP_HANDLE = [2, 3, 0, 1, 6, 7, 4, 5]   // opposite scale handle

const xformScalePct = computed(() => {
  if (!xW0) return 100
  const sx = (xbox.value.halfW * 2) / xW0
  const sy = (xbox.value.halfH * 2) / xH0
  return Math.round((sx + sy) / 2 * 100)
})
const xformAngleDeg = computed(() => {
  const d = Math.round(xbox.value.angle * 180 / Math.PI)
  return ((d % 360) + 360) % 360
})

/** continuous cell-space coordinate of a pointer event */
function clientToCell(e: MouseEvent): { x: number; y: number } {
  const rect = wrapRef.value!.getBoundingClientRect()
  const cellPx = BASE_CELL * zoom.value
  return {
    x: (e.clientX - rect.left - RULER - offset.value.x) / cellPx,
    y: (e.clientY - rect.top - RULER - offset.value.y) / cellPx,
  }
}
/** local (pre-rotation) offset of scale-handle i from the box center */
function handleLocal(i: number, b: XBox): { x: number; y: number } {
  return {
    x: (i === 0 || i === 3 || i === 7) ? -b.halfW
     : (i === 1 || i === 2 || i === 5) ?  b.halfW : 0,
    y: (i === 0 || i === 1 || i === 4) ? -b.halfH
     : (i === 2 || i === 3 || i === 6) ?  b.halfH : 0,
  }
}
/** world (cell-space) position of scale-handle i (0-3 corners, 4-7 edges) */
function handleWorld(i: number, b: XBox): { x: number; y: number } {
  const l = handleLocal(i, b)
  const c = Math.cos(b.angle), s = Math.sin(b.angle)
  return { x: b.cx + l.x * c - l.y * s, y: b.cy + l.x * s + l.y * c }
}
/** world position of the rotation handle (floats above the top edge) */
function rotHandleWorld(b: XBox): { x: number; y: number } {
  const d = b.halfH + Math.max(1.4, 26 / (BASE_CELL * zoom.value))
  return { x: b.cx + d * Math.sin(b.angle), y: b.cy - d * Math.cos(b.angle) }
}
/** is a cell-space point inside the rotated box? */
function pointInXBox(p: { x: number; y: number }, b: XBox): boolean {
  const dx = p.x - b.cx, dy = p.y - b.cy
  const c = Math.cos(-b.angle), s = Math.sin(-b.angle)
  return Math.abs(dx * c - dy * s) <= b.halfW
      && Math.abs(dx * s + dy * c) <= b.halfH
}

function startTransform() {
  const g = grid.value
  if (!g || transforming.value) return
  xW0 = g.width; xH0 = g.height
  xbox.value = {
    cx: g.width / 2, cy: g.height / 2,
    halfW: g.width / 2, halfH: g.height / 2, angle: 0,
  }
  // 1px-per-cell offscreen snapshot of the current beads
  const cv = document.createElement('canvas')
  cv.width = g.width; cv.height = g.height
  const c = cv.getContext('2d')!
  for (let y = 0; y < g.height; y++) {
    for (let x = 0; x < g.width; x++) {
      const code = g.cells[y * g.width + x]
      if (!code) continue
      c.fillStyle = MARD_COLORS[code]?.hex || '#000'
      c.fillRect(x, y, 1, 1)
    }
  }
  xCanvas = cv
  xDrag = null
  hover.value = null
  transforming.value = true
  render()
}
function cancelTransform() {
  transforming.value = false
  xCanvas = null
  xDrag = null
  render()
}
function applyTransform() {
  const g = grid.value
  if (!g || !transforming.value) return
  const b = xbox.value
  // axis-aligned bounding box of the transformed quad (cell space)
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity
  for (let i = 0; i < 4; i++) {
    const p = handleWorld(i, b)
    minX = Math.min(minX, p.x); maxX = Math.max(maxX, p.x)
    minY = Math.min(minY, p.y); maxY = Math.max(maxY, p.y)
  }
  const newW = Math.max(1, Math.min(400, Math.round(maxX - minX)))
  const newH = Math.max(1, Math.min(400, Math.round(maxY - minY)))
  const sx = (b.halfW * 2) / xW0 || 1e-6
  const sy = (b.halfH * 2) / xH0 || 1e-6
  const c = Math.cos(-b.angle), s = Math.sin(-b.angle)
  const cells: (string | null)[] = new Array(newW * newH).fill(null)
  for (let ny = 0; ny < newH; ny++) {
    for (let nx = 0; nx < newW; nx++) {
      const wx = minX + nx + 0.5 - b.cx
      const wy = minY + ny + 0.5 - b.cy
      const bx = wx * c - wy * s        // inverse-rotate
      const by = wx * s + wy * c
      const gx = Math.floor(bx / sx + xW0 / 2)
      const gy = Math.floor(by / sy + xH0 / 2)
      if (gx >= 0 && gx < xW0 && gy >= 0 && gy < xH0) {
        cells[ny * newW + nx] = g.cells[gy * xW0 + gx]
      }
    }
  }
  pushHistory()
  grid.value = { width: newW, height: newH, cells }
  gridVersion.value++
  transforming.value = false
  xCanvas = null
  xDrag = null
  nextTick(() => { syncCanvasSize(); fitView() })
}

function transformOnDown(e: MouseEvent) {
  const m = clientToCell(e)
  const b = xbox.value
  const thr = 12 / (BASE_CELL * zoom.value)   // hit radius, cell units
  // rotation handle
  const rh = rotHandleWorld(b)
  if (Math.hypot(m.x - rh.x, m.y - rh.y) <= thr) {
    xDrag = { mode: 'rotate', handle: -1, start: { ...b }, startMouse: m,
              anchor: { x: b.cx, y: b.cy }, anchorLocal: { x: 0, y: 0 },
              startPointerAngle: Math.atan2(m.y - b.cy, m.x - b.cx) }
    return
  }
  // 8 scale handles
  for (let i = 0; i < 8; i++) {
    const hp = handleWorld(i, b)
    if (Math.hypot(m.x - hp.x, m.y - hp.y) <= thr) {
      const opp = OPP_HANDLE[i]
      xDrag = { mode: 'scale', handle: i, start: { ...b }, startMouse: m,
                anchor: handleWorld(opp, b), anchorLocal: handleLocal(opp, b),
                startPointerAngle: 0 }
      return
    }
  }
  // inside the box → move
  if (pointInXBox(m, b)) {
    xDrag = { mode: 'move', handle: -1, start: { ...b }, startMouse: m,
              anchor: { x: 0, y: 0 }, anchorLocal: { x: 0, y: 0 }, startPointerAngle: 0 }
  }
}
function transformOnMove(e: MouseEvent) {
  if (!xDrag) return
  const m = clientToCell(e)
  const b0 = xDrag.start
  if (xDrag.mode === 'move') {
    xbox.value = { ...b0,
      cx: b0.cx + (m.x - xDrag.startMouse.x),
      cy: b0.cy + (m.y - xDrag.startMouse.y) }
  } else if (xDrag.mode === 'rotate') {
    const ang = Math.atan2(m.y - b0.cy, m.x - b0.cx)
    xbox.value = { ...b0, angle: b0.angle + (ang - xDrag.startPointerAngle) }
  } else {
    // opposite-anchor scaling (rotation stays fixed)
    const a = b0.angle
    const ux = Math.cos(a), uy = Math.sin(a)
    const vx = -Math.sin(a), vy = Math.cos(a)
    const dx = m.x - xDrag.anchor.x, dy = m.y - xDrag.anchor.y
    const du = dx * ux + dy * uy
    const dv = dx * vx + dy * vy
    const i = xDrag.handle
    const xActive = i <= 3 || i === 5 || i === 7
    const yActive = i <= 3 || i === 4 || i === 6
    const halfW = xActive ? Math.max(0.5, Math.abs(du) / 2) : b0.halfW
    const halfH = yActive ? Math.max(0.5, Math.abs(dv) / 2) : b0.halfH
    const uComp = xActive ? du / 2 : -xDrag.anchorLocal.x
    const vComp = yActive ? dv / 2 : -xDrag.anchorLocal.y
    xbox.value = {
      cx: xDrag.anchor.x + uComp * ux + vComp * vx,
      cy: xDrag.anchor.y + uComp * uy + vComp * vy,
      halfW, halfH, angle: a,
    }
  }
  render()
}

function drawTransformPreview(ctx: CanvasRenderingContext2D,
                              cell: number, ox: number, oy: number) {
  if (!xCanvas) return
  const b = xbox.value
  ctx.save()
  ctx.translate(ox + b.cx * cell, oy + b.cy * cell)
  ctx.rotate(b.angle)
  const sw = b.halfW * 2 * cell, sh = b.halfH * 2 * cell
  ctx.imageSmoothingEnabled = false
  ctx.drawImage(xCanvas, -sw / 2, -sh / 2, sw, sh)
  ctx.restore()
}
function drawTransformBox(ctx: CanvasRenderingContext2D,
                          cell: number, ox: number, oy: number) {
  const b = xbox.value
  const toScreen = (p: { x: number; y: number }) =>
    ({ x: ox + p.x * cell, y: oy + p.y * cell })
  const corners = [0, 1, 2, 3].map(i => toScreen(handleWorld(i, b)))
  ctx.strokeStyle = '#7c5cff'
  ctx.lineWidth = 1.8
  ctx.beginPath()
  ctx.moveTo(corners[0].x, corners[0].y)
  for (let i = 1; i < 4; i++) ctx.lineTo(corners[i].x, corners[i].y)
  ctx.closePath()
  ctx.stroke()
  // rotation handle stem + knob
  const top = toScreen(handleWorld(4, b))
  const rh = toScreen(rotHandleWorld(b))
  ctx.beginPath()
  ctx.moveTo(top.x, top.y); ctx.lineTo(rh.x, rh.y)
  ctx.stroke()
  ctx.fillStyle = '#fff'
  ctx.beginPath(); ctx.arc(rh.x, rh.y, 6, 0, Math.PI * 2); ctx.fill(); ctx.stroke()
  // 8 scale handles
  for (let i = 0; i < 8; i++) {
    const hp = toScreen(handleWorld(i, b))
    ctx.fillStyle = '#fff'
    ctx.fillRect(hp.x - 5, hp.y - 5, 10, 10)
    ctx.strokeRect(hp.x - 5, hp.y - 5, 10, 10)
  }
}

// ---- editing / interaction ----
let painting = false
let panning = false
let panStart = { x: 0, y: 0, ox: 0, oy: 0 }

/** Stamp a circular brush of diameter `size` centered on (cx, cy). */
function stampBlock(g: PerlerGrid, cx: number, cy: number,
                    size: number, value: string | null) {
  const lo = -Math.floor((size - 1) / 2)
  const hi = Math.floor(size / 2)
  const cen = (lo + hi) / 2            // circle center offset within the span
  const r2 = (size / 2) * (size / 2)
  for (let dy = lo; dy <= hi; dy++) {
    for (let dx = lo; dx <= hi; dx++) {
      const ddx = dx - cen, ddy = dy - cen
      if (ddx * ddx + ddy * ddy > r2) continue   // outside the brush circle
      const ex = cx + dx, ey = cy + dy
      if (ex >= 0 && ex < g.width && ey >= 0 && ey < g.height) {
        g.cells[ey * g.width + ex] = value
      }
    }
  }
}

/** Mirror-copy one half of the grid onto the other across a line. */
function mirrorCopy(cell: { x: number; y: number }) {
  const g = grid.value
  if (!g) return
  pushHistory()
  const w = g.width, h = g.height
  const n = g.cells.slice()
  if (mirrorAxis.value === 'v') {
    // axis = column cell.x ; copy one side onto the other
    const ax = cell.x
    for (let k = 1; ax - k >= 0 || ax + k < w; k++) {
      const left = ax - k, right = ax + k
      if (left < 0 || right >= w) continue
      for (let y = 0; y < h; y++) {
        if (mirrorDir.value === 1) n[y * w + right] = g.cells[y * w + left]
        else                      n[y * w + left]  = g.cells[y * w + right]
      }
    }
  } else {
    // axis = row cell.y
    const ax = cell.y
    for (let k = 1; ax - k >= 0 || ax + k < h; k++) {
      const top = ax - k, bot = ax + k
      if (top < 0 || bot >= h) continue
      for (let x = 0; x < w; x++) {
        if (mirrorDir.value === 1) n[bot * w + x] = g.cells[top * w + x]
        else                      n[top * w + x] = g.cells[bot * w + x]
      }
    }
  }
  grid.value = { ...g, cells: n }
  gridVersion.value++
  render()
}

/** Flood-fill the contiguous same-value region starting at (sx, sy). */
function floodFill(g: PerlerGrid, sx: number, sy: number,
                   target: string | null, repl: string | null) {
  if (target === repl) return
  const w = g.width, h = g.height
  const stack = [sy * w + sx]
  while (stack.length) {
    const i = stack.pop()!
    if (g.cells[i] !== target) continue
    g.cells[i] = repl
    const x = i % w, y = (i / w) | 0
    if (x + 1 < w) stack.push(i + 1)
    if (x - 1 >= 0) stack.push(i - 1)
    if (y + 1 < h) stack.push(i + w)
    if (y - 1 >= 0) stack.push(i - w)
  }
}

function applyTool(cell: { x: number; y: number }) {
  const g = grid.value
  if (!g) return
  const idx = cell.y * g.width + cell.x
  if (tool.value === 'paint') {
    if (!currentCode.value) return
    stampBlock(g, cell.x, cell.y, brushSize.value, currentCode.value)
    gridVersion.value++
    render()
  } else if (tool.value === 'erase') {
    stampBlock(g, cell.x, cell.y, eraserSize.value, null)
    gridVersion.value++
    render()
  } else if (tool.value === 'wand') {
    // 魔棒画笔：把点击处相连的同色区域整片填成当前色
    if (!currentCode.value) return
    const target = g.cells[idx]
    if (target === currentCode.value) return
    floodFill(g, cell.x, cell.y, target, currentCode.value)
    gridVersion.value++
    render()
  } else if (tool.value === 'wanderase') {
    // 魔棒橡皮：把点击处相连的同色区域整片擦除
    const target = g.cells[idx]
    if (target === null) return
    floodFill(g, cell.x, cell.y, target, null)
    gridVersion.value++
    render()
  } else if (tool.value === 'replace') {
    // 同色替换：把整张图里该颜色全部换成当前色
    if (!currentCode.value) return
    const target = g.cells[idx]
    if (target === currentCode.value) return
    for (let i = 0; i < g.cells.length; i++) {
      if (g.cells[i] === target) g.cells[i] = currentCode.value
    }
    gridVersion.value++
    render()
  } else if (tool.value === 'mirror') {
    mirrorCopy(cell)
  } else if (tool.value === 'pick') {
    const code = g.cells[idx]
    if (code) { currentCode.value = code; tool.value = 'paint' }
  }
}

function onDown(e: MouseEvent) {
  if (transforming.value) { transformOnDown(e); return }
  if (tool.value === 'pan' || e.button === 1) {
    panning = true
    panStart = { x: e.clientX, y: e.clientY, ox: offset.value.x, oy: offset.value.y }
    return
  }
  const cell = cellAt(e)
  if (cell) {
    // snapshot once per action so Ctrl+Z reverts the whole stroke
    // (mirror does its own pushHistory inside mirrorCopy)
    if (['paint', 'erase', 'wand', 'wanderase', 'replace'].includes(tool.value)) pushHistory()
    painting = true
    applyTool(cell)
  }
}
function onMove(e: MouseEvent) {
  if (transforming.value) { if (xDrag) transformOnMove(e); return }
  if (panning) {
    offset.value = {
      x: panStart.ox + (e.clientX - panStart.x),
      y: panStart.oy + (e.clientY - panStart.y),
    }
    render()
    return
  }
  const cell = cellAt(e)
  hover.value = cell
  if (cell) {
    const rect = wrapRef.value!.getBoundingClientRect()
    hoverTipStyle.value = {
      left: (e.clientX - rect.left + 14) + 'px',
      top: (e.clientY - rect.top + 14) + 'px',
    }
  }
  if (painting && cell && (tool.value === 'paint' || tool.value === 'erase')) {
    applyTool(cell)
  } else {
    render()
  }
}
function onUp() {
  if (transforming.value) { xDrag = null; return }
  painting = false; panning = false
}
function onLeave() {
  if (transforming.value) { xDrag = null; return }
  painting = false; panning = false; hover.value = null; render()
}

// ---- rendering ----
function render() {
  const cv = canvasRef.value, g = grid.value
  if (!cv || !g) return
  const ctx = cv.getContext('2d')!
  const dpr = window.devicePixelRatio || 1
  const W = cv.width / dpr, H = cv.height / dpr
  const cell = BASE_CELL * zoom.value
  const ox = RULER + offset.value.x
  const oy = RULER + offset.value.y

  ctx.clearRect(0, 0, W, H)
  ctx.fillStyle = '#fdf6f0'
  ctx.fillRect(0, 0, W, H)

  // visible cell range (cull)
  const cx0 = Math.max(0, Math.floor((-offset.value.x) / cell))
  const cy0 = Math.max(0, Math.floor((-offset.value.y) / cell))
  const cx1 = Math.min(g.width, Math.ceil((W - ox) / cell) + 1)
  const cy1 = Math.min(g.height, Math.ceil((H - oy) / cell) + 1)

  // beads (hidden while a free-transform preview is active)
  if (!transforming.value) for (let y = cy0; y < cy1; y++) {
    for (let x = cx0; x < cx1; x++) {
      const code = g.cells[y * g.width + x]
      const px = ox + x * cell, py = oy + y * cell
      if (!code) {
        // empty / erased cell: neutral transparency checker (no bead here)
        ctx.fillStyle = ((x + y) & 1) ? '#ffffff' : '#d4d0d8'
        ctx.fillRect(px, py, cell, cell)
        continue
      }
      drawBead(ctx, px, py, cell, MARD_COLORS[code]?.hex || '#000', beadShape.value)
      // bead ring highlight (not for the edge-to-edge "fill" style)
      if (cell > 10 && beadShape.value !== 'fill') {
        ctx.strokeStyle = 'rgba(255,255,255,0.35)'
        ctx.lineWidth = 1
        ctx.beginPath()
        ctx.arc(px + cell * 0.36, py + cell * 0.36, cell * 0.14, 0, Math.PI * 2)
        ctx.stroke()
      }
      // color-code label
      if (showLabels.value && cell >= 13) {
        const bc = MARD_COLORS[code]
        if (bc) {
          ctx.fillStyle = textOn(bc.rgb)
          ctx.font = `bold ${Math.max(7, Math.round(cell * 0.32))}px "JetBrains Mono", monospace`
          ctx.textAlign = 'center'
          ctx.textBaseline = 'middle'
          ctx.fillText(code, px + cell / 2, py + cell / 2)
        }
      }
    }
  }

  // grid lines
  if (cell >= 5 && !transforming.value) {
    ctx.strokeStyle = 'rgba(120,90,90,0.18)'
    ctx.lineWidth = 1
    ctx.beginPath()
    for (let x = cx0; x <= cx1; x++) {
      const px = ox + x * cell
      ctx.moveTo(px, oy + cy0 * cell); ctx.lineTo(px, oy + cy1 * cell)
    }
    for (let y = cy0; y <= cy1; y++) {
      const py = oy + y * cell
      ctx.moveTo(ox + cx0 * cell, py); ctx.lineTo(ox + cx1 * cell, py)
    }
    ctx.stroke()
    // thick every-10 lines
    ctx.strokeStyle = 'rgba(232,70,42,0.55)'
    ctx.lineWidth = 1.6
    ctx.beginPath()
    for (let x = cx0; x <= cx1; x++) {
      if (x % 10) continue
      const px = ox + x * cell
      ctx.moveTo(px, oy); ctx.lineTo(px, oy + g.height * cell)
    }
    for (let y = cy0; y <= cy1; y++) {
      if (y % 10) continue
      const py = oy + y * cell
      ctx.moveTo(ox, py); ctx.lineTo(ox + g.width * cell, py)
    }
    ctx.stroke()
  }

  // ---- reference image overlay (on top of beads so it stays visible) ----
  const refImg = refImage.value
  if (refImg && !transforming.value) {
    ctx.save()
    ctx.globalAlpha = refOpacity.value
    ctx.drawImage(refImg, ox, oy, g.width * cell, g.height * cell)
    ctx.restore()
  }

  // free-transform preview
  if (transforming.value && xCanvas) drawTransformPreview(ctx, cell, ox, oy)

  // hover highlight
  if (hover.value && !transforming.value) {
    ctx.strokeStyle = '#ff6b9d'
    ctx.lineWidth = 2
    if (tool.value === 'paint' || tool.value === 'erase') {
      // circular brush / eraser footprint
      const s = tool.value === 'paint' ? brushSize.value : eraserSize.value
      const lo = -Math.floor((s - 1) / 2)
      const hi = Math.floor(s / 2)
      const cen = (lo + hi + 1) / 2
      ctx.beginPath()
      ctx.arc(
        ox + (hover.value.x + cen) * cell,
        oy + (hover.value.y + cen) * cell,
        (s / 2) * cell, 0, Math.PI * 2,
      )
      ctx.stroke()
    } else if (tool.value === 'mirror') {
      // show the symmetry line through the hovered cell
      ctx.strokeRect(ox + hover.value.x * cell, oy + hover.value.y * cell, cell, cell)
      ctx.strokeStyle = '#7c5cff'
      ctx.lineWidth = 2.5
      ctx.setLineDash([6, 4])
      ctx.beginPath()
      if (mirrorAxis.value === 'v') {
        const lx = ox + (hover.value.x + 0.5) * cell
        ctx.moveTo(lx, oy)
        ctx.lineTo(lx, oy + g.height * cell)
      } else {
        const ly = oy + (hover.value.y + 0.5) * cell
        ctx.moveTo(ox, ly)
        ctx.lineTo(ox + g.width * cell, ly)
      }
      ctx.stroke()
      ctx.setLineDash([])
    } else {
      ctx.strokeRect(ox + hover.value.x * cell, oy + hover.value.y * cell, cell, cell)
    }
  }

  // ruler
  ctx.fillStyle = '#fff'
  ctx.fillRect(0, 0, W, RULER)
  ctx.fillRect(0, 0, RULER, H)
  ctx.font = '10px "JetBrains Mono", monospace'
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  const step = cell < 16 ? 10 : cell < 30 ? 5 : 1
  for (let x = cx0; x < cx1; x++) {
    if (x % step) continue
    ctx.fillStyle = (x % 10 === 0) ? '#e8462a' : '#a896a3'
    ctx.fillText(String(x + 1), ox + x * cell + cell / 2, RULER / 2)
  }
  ctx.textAlign = 'right'
  for (let y = cy0; y < cy1; y++) {
    if (y % step) continue
    ctx.fillStyle = (y % 10 === 0) ? '#e8462a' : '#a896a3'
    ctx.fillText(String(y + 1), RULER - 4, oy + y * cell + cell / 2)
  }
  // corner mask
  ctx.fillStyle = '#fff'
  ctx.fillRect(0, 0, RULER, RULER)

  // free-transform box + handles (drawn on top of the ruler)
  if (transforming.value) drawTransformBox(ctx, cell, ox, oy)
}

function roundRect(
  ctx: CanvasRenderingContext2D,
  x: number, y: number, w: number, h: number, r: number,
) {
  if (r <= 0.5) { ctx.beginPath(); ctx.rect(x, y, w, h); return }
  ctx.beginPath()
  ctx.moveTo(x + r, y)
  ctx.arcTo(x + w, y, x + w, y + h, r)
  ctx.arcTo(x + w, y + h, x, y + h, r)
  ctx.arcTo(x, y + h, x, y, r)
  ctx.arcTo(x, y, x + w, y, r)
  ctx.closePath()
}

/** Draw one bead in a cell according to the chosen shape. */
function drawBead(
  ctx: CanvasRenderingContext2D,
  px: number, py: number, cell: number, hex: string, shape: BeadShape,
) {
  ctx.fillStyle = hex
  if (shape === 'fill') {
    // edge-to-edge, tiny overlap to avoid hairline seams
    ctx.fillRect(px, py, cell + 0.6, cell + 0.6)
  } else if (shape === 'circle') {
    const pad = cell > 7 ? cell * 0.06 : 0
    ctx.beginPath()
    ctx.arc(px + cell / 2, py + cell / 2, (cell - pad * 2) / 2, 0, Math.PI * 2)
    ctx.fill()
  } else {
    // rounded square
    const pad = cell > 7 ? Math.max(0.5, cell * 0.07) : 0
    const r = cell > 12 ? Math.min(cell * 0.22, 4) : 1
    roundRect(ctx, px + pad, py + pad, cell - pad * 2, cell - pad * 2, r)
    ctx.fill()
  }
}

// ---- export ----
/** Generic canvas export (PNG / JPEG) — mirrors the current canvas state. */
function exportImage(mime: 'png' | 'jpeg', quality?: number) {
  const g = grid.value
  if (!g) return
  const labels = showLabels.value
  const cell = labels ? 42 : 26
  const cv = document.createElement('canvas')
  cv.width = RULER + g.width * cell
  cv.height = RULER + g.height * cell
  const ctx = cv.getContext('2d')!
  ctx.fillStyle = '#ffffff'
  ctx.fillRect(0, 0, cv.width, cv.height)

  for (let y = 0; y < g.height; y++) {
    for (let x = 0; x < g.width; x++) {
      const code = g.cells[y * g.width + x]
      const px = RULER + x * cell, py = RULER + y * cell
      if (!code) {
        // empty cell: neutral transparency checker (no bead here)
        ctx.fillStyle = ((x + y) & 1) ? '#ffffff' : '#d4d4d4'
        ctx.fillRect(px, py, cell, cell)
        continue
      }
      const bc = MARD_COLORS[code]
      drawBead(ctx, px, py, cell, bc?.hex || '#000', beadShape.value)
      if (labels && bc) {
        ctx.fillStyle = textOn(bc.rgb)
        ctx.font = `bold ${Math.round(cell * 0.30)}px "JetBrains Mono", monospace`
        ctx.textAlign = 'center'
        ctx.textBaseline = 'middle'
        ctx.fillText(code, px + cell / 2, py + cell / 2)
      }
    }
  }
  // grid lines
  ctx.strokeStyle = 'rgba(120,90,90,0.25)'
  ctx.lineWidth = 1
  ctx.beginPath()
  for (let x = 0; x <= g.width; x++) {
    ctx.moveTo(RULER + x * cell, RULER); ctx.lineTo(RULER + x * cell, cv.height)
  }
  for (let y = 0; y <= g.height; y++) {
    ctx.moveTo(RULER, RULER + y * cell); ctx.lineTo(cv.width, RULER + y * cell)
  }
  ctx.stroke()
  ctx.strokeStyle = 'rgba(232,70,42,0.6)'
  ctx.lineWidth = 2
  ctx.beginPath()
  for (let x = 0; x <= g.width; x += 10) {
    ctx.moveTo(RULER + x * cell, RULER); ctx.lineTo(RULER + x * cell, cv.height)
  }
  for (let y = 0; y <= g.height; y += 10) {
    ctx.moveTo(RULER, RULER + y * cell); ctx.lineTo(cv.width, RULER + y * cell)
  }
  ctx.stroke()
  // ruler numbers
  ctx.fillStyle = '#fff'
  ctx.fillRect(0, 0, cv.width, RULER)
  ctx.fillRect(0, 0, RULER, cv.height)
  ctx.font = '11px monospace'
  ctx.textBaseline = 'middle'
  for (let x = 0; x < g.width; x++) {
    ctx.fillStyle = (x % 10 === 0) ? '#e8462a' : '#aaa'
    ctx.textAlign = 'center'
    ctx.fillText(String(x + 1), RULER + x * cell + cell / 2, RULER / 2)
  }
  for (let y = 0; y < g.height; y++) {
    ctx.fillStyle = (y % 10 === 0) ? '#e8462a' : '#aaa'
    ctx.textAlign = 'right'
    ctx.fillText(String(y + 1), RULER - 4, RULER + y * cell + cell / 2)
  }
  ctx.fillStyle = '#fff'
  ctx.fillRect(0, 0, RULER, RULER)

  const ext = mime === 'jpeg' ? 'jpg' : 'png'
  const mimeType = mime === 'jpeg' ? 'image/jpeg' : 'image/png'
  const a = document.createElement('a')
  a.download = `拼豆图纸_${g.width}x${g.height}.${ext}`
  a.href = cv.toDataURL(mimeType, quality)
  a.click()
  ElMessage.success('图纸已导出')
}

/** Export as SVG vector — mirrors the current canvas state. */
function downloadSVG(shape: 'circle' | 'rect') {
  const g = grid.value
  if (!g) return
  const labels = showLabels.value
  const cell = labels ? 42 : 26
  const W = RULER + g.width * cell
  const H = RULER + g.height * cell

  let beads = ''

  for (let y = 0; y < g.height; y++) {
    for (let x = 0; x < g.width; x++) {
      const code = g.cells[y * g.width + x]
      const px = RULER + x * cell, py = RULER + y * cell
      if (!code) continue
      const bc = MARD_COLORS[code]
      if (!bc) continue
      const d = cell - 1
      if (shape === 'circle') {
        const r = d / 2
        beads += `<circle cx="${px + d / 2}" cy="${py + d / 2}" r="${r}" fill="${bc.hex}" />\n`
      } else {
        beads += `<rect x="${px}" y="${py}" width="${d}" height="${d}" rx="${Math.min(3, d * 0.15)}" fill="${bc.hex}" />\n`
      }
      if (labels) {
        beads += `<text x="${px + d / 2}" y="${py + d / 2 + 1}" text-anchor="middle" dominant-baseline="middle" font-size="${Math.round(cell * 0.28)}" font-family="monospace" fill="${textOn(bc.rgb)}">${code}</text>\n`
      }
    }
  }

  let gridLines = ''
  for (let x = 0; x <= g.width; x++) {
    const lx = RULER + x * cell
    gridLines += `<line x1="${lx}" y1="${RULER}" x2="${lx}" y2="${H}" ${x % 10 === 0 ? 'class="tick"' : ''} />\n`
  }
  for (let y = 0; y <= g.height; y++) {
    const ly = RULER + y * cell
    gridLines += `<line x1="${RULER}" y1="${ly}" x2="${W}" y2="${ly}" ${y % 10 === 0 ? 'class="tick"' : ''} />\n`
  }

  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">
<style>.tick{stroke:#e8462a;stroke-width:2}line{stroke:rgba(120,90,90,0.25);stroke-width:1}</style>
<rect width="100%" height="100%" fill="#fff" />
${gridLines}${beads}</svg>`

  const blob = new Blob([svg], { type: 'image/svg+xml;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.download = `拼豆图纸_${g.width}x${g.height}.svg`
  a.href = url
  a.click()
  URL.revokeObjectURL(url)
  ElMessage.success('SVG 已导出')
}

/** Export material list as CSV */
function downloadCSV() {
  const g = grid.value
  if (!g) return
  const sorted = [...colorCounts.value.entries()].sort((a, b) => b[1] - a[1])
  const rows = ['﻿色号,颜色名,Hex,数量']
  for (const [code, count] of sorted) {
    const c = MARD_COLORS[code]
    rows.push(`${code},${c?.name ?? ''},${c?.hex ?? ''},${count}`)
  }
  const blob = new Blob([rows.join('\n')], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.download = `拼豆材料单_${g.width}x${g.height}.csv`
  a.href = url
  a.click()
  URL.revokeObjectURL(url)
  ElMessage.success('材料单已导出')
}

// ---- export dialog handlers ----
function handleExportPng() {
  showExportDialog.value = false
  exportImage('png')
}
function handleExportJpg(opts: { quality: number }) {
  showExportDialog.value = false
  exportImage('jpeg', opts.quality / 100)
}
function handleExportSvg(opts: { shape: 'circle' | 'rect' }) {
  showExportDialog.value = false
  downloadSVG(opts.shape)
}
function handleExportCsv() {
  showExportDialog.value = false
  downloadCSV()
}

// Bead shape & code labels only affect display — just repaint, no re-convert.
watch([beadShape, showLabels], () => render())

// ---- keyboard shortcuts ----
let panBeforeSpace: Tool | null = null
function onKeyDown(e: KeyboardEvent) {
  // ignore while typing in a form field
  const tag = (e.target as HTMLElement)?.tagName
  if (tag === 'INPUT' || tag === 'SELECT' || tag === 'TEXTAREA') return
  if (!grid.value) return

  // free-transform: Enter applies, Esc cancels
  if (transforming.value) {
    if (e.key === 'Enter') { e.preventDefault(); applyTransform() }
    else if (e.key === 'Escape') { e.preventDefault(); cancelTransform() }
    return
  }

  // undo / redo
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'z') {
    e.preventDefault()
    if (e.shiftKey) redo(); else undo()
    return
  }
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'y') {
    e.preventDefault(); redo(); return
  }
  if (e.ctrlKey || e.metaKey || e.altKey) return

  switch (e.key.toLowerCase()) {
    case 'b': tool.value = 'paint'; break
    case 'e': tool.value = 'erase'; break
    case 'g': tool.value = 'wand'; break
    case 'd': tool.value = 'wanderase'; break
    case 'r': tool.value = 'replace'; break
    case 'm': tool.value = 'mirror'; break
    case 'i': tool.value = 'pick'; break
    case 'h': tool.value = 'pan'; break
    case ' ':
      e.preventDefault()
      if (tool.value !== 'pan') { panBeforeSpace = tool.value; tool.value = 'pan' }
      break
    case '+': case '=': zoomBy(1); break
    case '-': case '_': zoomBy(-1); break
    case '0': fitView(); break
    default: return
  }
}
function onKeyUp(e: KeyboardEvent) {
  if (e.key === ' ' && panBeforeSpace) {
    tool.value = panBeforeSpace
    panBeforeSpace = null
  }
}

// ---- lifecycle ----
// This view is wrapped in <keep-alive>, so the canvas & all edits survive
// navigating to the MARD palette tab and back. Global listeners are bound on
// activate / unbound on deactivate so shortcuts don't fire on other pages.
function onResize() { syncCanvasSize() }
function bindGlobalEvents() {
  window.addEventListener('resize', onResize)
  window.addEventListener('keydown', onKeyDown)
  window.addEventListener('keyup', onKeyUp)
}
function unbindGlobalEvents() {
  window.removeEventListener('resize', onResize)
  window.removeEventListener('keydown', onKeyDown)
  window.removeEventListener('keyup', onKeyUp)
}
onActivated(() => {
  bindGlobalEvents()
  // container size may have changed while the view was inactive
  if (grid.value) nextTick(() => syncCanvasSize())
})
onDeactivated(unbindGlobalEvents)
onBeforeUnmount(unbindGlobalEvents)
watch(tier, () => {
  // keep currentCode valid for the new tier's picker
  if (currentCode.value && !MARD_TIERS[tier.value].includes(currentCode.value)) {
    currentCode.value = workingPalette.value[0]?.code || ''
  }
})
</script>

<style scoped>
.bead-studio { display: flex; flex-direction: column; gap: 1rem; }

/* ===== setup ===== */
.setup-card { padding: 1.1rem 1.25rem; }
.setup-grid {
  display: grid;
  grid-template-columns: 220px 1fr;
  gap: 1.25rem;
}
@media (max-width: 720px) { .setup-grid { grid-template-columns: 1fr; } }

.upload-zone {
  border: 2.5px dashed var(--sakura-light);
  border-radius: var(--radius-md);
  background: var(--cream-2);
  height: 170px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  overflow: hidden;
  transition: all var(--transition-fast);
}
.upload-zone:hover, .upload-zone.dragging {
  border-color: var(--sakura);
  background: var(--sakura-glow);
}
.upload-zone.filled { border-style: solid; padding: 4px; }
.upload-preview { max-width: 100%; max-height: 100%; border-radius: var(--radius-sm); object-fit: contain; }
.upload-hint { text-align: center; color: var(--plum-2); }
.upload-emoji { font-size: 2rem; }
.upload-text { font-family: var(--font-display); font-size: 1rem; margin-top: 0.3rem; }
.upload-sub { font-size: 0.7rem; color: var(--plum-3); margin-top: 0.15rem; }

.params { display: flex; flex-direction: column; gap: 0.85rem; }
.slider { flex: 1; accent-color: var(--sakura); cursor: pointer; }
.convert-btn { align-self: flex-start; }

/* ===== workspace ===== */
.workspace {
  display: grid;
  grid-template-columns: 1fr 300px;
  gap: 1rem;
  align-items: start;
}
@media (max-width: 1000px) { .workspace { grid-template-columns: 1fr; } }

.canvas-col { padding: 0; overflow: hidden; }

.toolbar {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.55rem 0.8rem;
  border-bottom: 2px dashed var(--line-strong);
  flex-wrap: wrap;
}
.tool-group { display: flex; align-items: center; gap: 0.25rem; }
.tool-btn {
  width: 32px; height: 32px;
  border: 2px solid var(--cream-4);
  background: #fff;
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 0.95rem;
  display: flex; align-items: center; justify-content: center;
  transition: all var(--transition-fast);
}
.tool-btn:hover { border-color: var(--sakura); transform: translateY(-1px); }
.tool-btn.on {
  background: var(--sakura);
  border-color: var(--sakura);
  box-shadow: 0 3px 10px var(--sakura-glow);
}
.tool-btn:disabled {
  opacity: 0.35;
  cursor: not-allowed;
  transform: none;
}
.tool-btn:disabled:hover { border-color: var(--cream-4); }

/* brush / eraser size indicator */
.size-tag {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  font-size: 0.74rem;
  color: var(--plum-2);
  background: var(--cream-2);
  border-radius: var(--radius-pill);
  padding: 0.18rem 0.6rem;
  white-space: nowrap;
}
.size-tag b { color: var(--plum-1); }
.size-hint {
  font-size: 0.62rem;
  color: var(--plum-3);
  border: 1px dashed var(--line-strong);
  border-radius: var(--radius-pill);
  padding: 0 0.35rem;
}

/* mirror-copy config */
.mirror-cfg {
  display: flex;
  align-items: center;
  gap: 2px;
  padding: 0 0.25rem;
}
.mini-btn {
  width: auto !important;
  font-size: 0.68rem !important;
  font-weight: 700;
  font-family: var(--font-round);
  padding: 0 0.45rem;
  min-width: 30px;
}
.mini-btn.on {
  background: var(--plum-1) !important;
  border-color: var(--plum-1) !important;
  color: #fff !important;
}

.kbd-hint {
  font-size: 0.72rem;
  color: var(--plum-3);
  border: 1.5px dashed var(--line-strong);
  border-radius: var(--radius-pill);
  padding: 0.12rem 0.6rem;
  cursor: help;
  white-space: nowrap;
}
.tool-divider { width: 1px; height: 22px; background: var(--line-strong); }
.export-opt {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  font-size: 0.76rem;
  font-weight: 700;
  color: var(--plum-2);
  cursor: pointer;
  user-select: none;
}

/* live param row */
.param-bar {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5rem 0.8rem;
  background: var(--cream-2);
  border-bottom: 2px dashed var(--line-strong);
  flex-wrap: wrap;
}
.pb-cell {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}
.pb-cell.pb-wide { flex: 1; min-width: 160px; }
.pb-label {
  font-size: 0.66rem;
  font-weight: 700;
  color: var(--plum-3);
}
.pb-cell .input { padding: 0.25rem 0.4rem; font-size: 0.78rem; width: 72px; }
.pb-cell .select { padding: 0.25rem 0.5rem; font-size: 0.78rem; }
.pb-cell .slider { accent-color: var(--sakura); cursor: pointer; }
.pb-hint {
  font-size: 0.7rem;
  color: var(--plum-3);
  margin-left: auto;
}
.pb-hint.busy { color: var(--sakura-deep); font-weight: 700; }
.cur-color { display: flex; align-items: center; gap: 0.35rem; }
.cur-swatch {
  width: 24px; height: 24px; border-radius: 6px;
  border: 2px solid var(--cream-4);
}
.cur-label { font-size: 0.78rem; color: var(--plum-2); }
.zoom-label { font-size: 0.76rem; color: var(--plum-2); min-width: 42px; text-align: center; }
.grid-size { font-size: 0.76rem; color: var(--plum-3); }

.canvas-wrap {
  position: relative;
  height: 64vh;
  min-height: 360px;
  background: #fdf6f0;
  overflow: hidden;
  cursor: crosshair;
}
.canvas-wrap canvas { display: block; }
.hover-tip {
  position: absolute;
  background: var(--plum-1);
  color: #fff;
  font-size: 0.72rem;
  font-family: var(--font-mono);
  padding: 0.2rem 0.5rem;
  border-radius: var(--radius-sm);
  pointer-events: none;
  white-space: nowrap;
  z-index: 5;
}

/* free-transform action bar */
.canvas-wrap.xforming { cursor: default; }
.xform-bar {
  position: absolute;
  top: 10px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 0.6rem;
  background: rgba(255, 255, 255, 0.96);
  border: 2px solid var(--plum-1);
  border-radius: var(--radius-pill);
  padding: 0.35rem 0.45rem 0.35rem 0.85rem;
  box-shadow: var(--shadow-soft);
  z-index: 8;
}
.xform-title {
  font-family: var(--font-display);
  font-size: 0.86rem;
  color: var(--plum-1);
}
.xform-info {
  font-size: 0.74rem;
  color: var(--plum-2);
}

/* ===== side ===== */
.side-col { display: flex; flex-direction: column; gap: 1rem; }
.side-card { padding: 0.8rem 0.9rem; }
.side-head {
  font-family: var(--font-display);
  font-size: 0.95rem;
  color: var(--plum-1);
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 0.6rem;
}
.side-count { font-size: 0.7rem; font-family: var(--font-mono); color: var(--plum-3); }
.side-sub { font-size: 0.72rem; color: var(--plum-3); margin: -0.35rem 0 0.55rem; }
.side-empty { font-size: 0.78rem; color: var(--plum-3); padding: 0.5rem 0; }

.palette-scroll {
  max-height: 320px;
  overflow-y: auto;
  padding-right: 2px;
}
.pal-group { margin-bottom: 0.55rem; }
.pal-group:last-child { margin-bottom: 0; }
.pal-group-label {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.7rem;
  color: var(--plum-2);
  margin-bottom: 0.25rem;
  position: sticky;
  top: 0;
  background: #fff;
  padding: 0.1rem 0;
  z-index: 1;
}
.pal-group-key {
  font-family: var(--font-mono);
  font-weight: 800;
  color: var(--sakura-deep);
  background: var(--sakura-glow);
  border-radius: 4px;
  padding: 0 0.3rem;
}
.pal-group-n { margin-left: auto; color: var(--plum-3); font-family: var(--font-mono); }
.palette-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(20px, 1fr));
  gap: 3px;
}
.pal-swatch {
  aspect-ratio: 1;
  border: 1.5px solid rgba(0,0,0,0.08);
  border-radius: 4px;
  cursor: pointer;
  padding: 0;
  transition: transform var(--transition-fast);
  position: relative;
}
.pal-swatch:hover { transform: scale(1.25); z-index: 2; }
.pal-swatch.used::after {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: 3px;
  box-shadow: inset 0 0 0 1.5px rgba(255,255,255,0.85);
}
.pal-swatch.on {
  box-shadow: 0 0 0 2.5px var(--sakura);
  transform: scale(1.2);
  z-index: 3;
}

.color-list { max-height: 240px; overflow-y: auto; display: flex; flex-direction: column; gap: 1px; }
.color-row {
  display: grid;
  grid-template-columns: 18px 42px 1fr auto;
  align-items: center;
  gap: 0.4rem;
  padding: 0.25rem 0.3rem;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: background var(--transition-fast);
}
.color-row:hover { background: var(--sakura-glow); }
.cl-swatch { width: 16px; height: 16px; border-radius: 4px; border: 1px solid rgba(0,0,0,0.1); }
.cl-code { font-size: 0.72rem; color: var(--plum-2); }
.cl-name { font-size: 0.76rem; color: var(--plum-1); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.cl-count { font-size: 0.74rem; color: var(--sakura-deep); font-weight: 700; }

.gap-block { margin-bottom: 0.6rem; }
.gap-block:last-child { margin-bottom: 0; }
.gap-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.3rem; }
.gap-tier { font-size: 0.8rem; font-weight: 700; color: var(--plum-1); font-family: var(--font-round); }
.gap-stat { font-size: 0.72rem; font-weight: 700; color: var(--bad); }
.gap-stat.ok { color: var(--ok); }
.gap-pairs {
  display: flex;
  flex-direction: column;
  gap: 2px;
  max-height: 150px;
  overflow-y: auto;
}
.gap-pair {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  padding: 1px 0;
}
.gap-swatch {
  width: 15px; height: 15px;
  border-radius: 4px;
  border: 1px solid rgba(0,0,0,0.12);
  flex-shrink: 0;
}
.gap-swatch.miss {
  border-style: dashed;
  border-color: var(--bad);
}
.gap-arrow { font-size: 0.7rem; color: var(--plum-3); }
.gap-sub-code { font-size: 0.66rem; color: var(--plum-2); }

/* ===== bead-size toggle ===== */
.bead-size-toggle {
  display: inline-flex;
  gap: 2px;
  background: var(--cream-2);
  border-radius: var(--radius-pill);
  padding: 2px;
}
.pill-btn {
  padding: 0.25rem 0.65rem;
  border: 2px solid transparent;
  background: transparent;
  border-radius: var(--radius-pill);
  font-family: var(--font-round);
  font-weight: 700;
  font-size: 0.78rem;
  color: var(--plum-3);
  cursor: pointer;
  transition: all var(--transition-fast);
  line-height: 1.3;
}
.pill-btn.on {
  background: #fff;
  border-color: var(--sakura);
  color: var(--sakura-deep);
  box-shadow: 0 2px 6px var(--sakura-glow);
}
.pill-btn:hover:not(.on) { color: var(--plum-1); }
.pill-sub {
  font-size: 0.62rem;
  padding: 0.25rem 0.4rem;
  opacity: 0.5;
  min-width: 20px;
}
.pill-sub:hover { opacity: 1; }

/* ===== reference image overlay ===== */
.ref-section {
  padding: 0.35rem 0.75rem;
  border-top: 2px dashed var(--line-strong);
  background: var(--cream-2);
}
.ref-toggle {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  cursor: pointer;
  font-size: 0.82rem;
  font-weight: 700;
  color: var(--plum-2);
  user-select: none;
}
.ref-toggle-icon { font-size: 0.65rem; }
.ref-badge {
  font-size: 0.65rem;
  background: var(--sakura-glow);
  color: var(--sakura-deep);
  padding: 0.05rem 0.5rem;
  border-radius: var(--radius-pill);
}
.ref-body {
  margin-top: 0.5rem;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}
.ref-upload {
  border: 2px dashed var(--cream-4);
  border-radius: var(--radius-md);
  padding: 0.4rem 0.85rem;
  cursor: pointer;
  font-size: 0.78rem;
  color: var(--plum-3);
  text-align: center;
  transition: border var(--transition-fast);
}
.ref-upload:hover { border-color: var(--sakura-light); }
.ref-thumb {
  width: 42px; height: 42px;
  object-fit: cover;
  border-radius: var(--radius-sm);
  border: 1.5px solid var(--cream-4);
}
.ref-controls {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}
.ref-slider-label {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.72rem;
  color: var(--plum-3);
}
.ref-slider { width: 80px; }
.ref-lock-btn {
  background: none;
  border: 1.5px solid var(--cream-4);
  border-radius: var(--radius-sm);
  padding: 0.1rem 0.35rem;
  cursor: pointer;
  font-size: 0.9rem;
  line-height: 1;
  transition: all var(--transition-fast);
}
.ref-lock-btn.locked { border-color: var(--sakura); background: var(--sakura-glow); }

/* ===== palette mode toggle ===== */
.mode-toggle {
  display: inline-flex;
  gap: 2px;
  background: var(--cream-2);
  border-radius: var(--radius-pill);
  padding: 2px;
}
.mode-btn {
  padding: 0.28rem 0.75rem;
  border: 2px solid transparent;
  background: transparent;
  border-radius: var(--radius-pill);
  font-family: var(--font-round);
  font-weight: 700;
  font-size: 0.8rem;
  color: var(--plum-3);
  cursor: pointer;
  transition: all var(--transition-fast);
  line-height: 1.3;
}
.mode-btn.on {
  background: #fff;
  border-color: var(--sakura);
  color: var(--sakura-deep);
  box-shadow: 0 2px 6px var(--sakura-glow);
}
.mode-btn:hover:not(.on) { color: var(--plum-1); }

/* ===== my palette side card ===== */
.my-pal-card .my-pal-mode {
  margin-bottom: 0.6rem;
}
.my-pal-pick-btn {
  width: 100%;
  margin-bottom: 0.5rem;
}
.my-pal-add {
  display: flex;
  gap: 0.4rem;
  margin-bottom: 0.4rem;
}
.my-pal-input { flex: 1; min-width: 0; font-family: var(--font-mono); text-transform: uppercase; }
.my-pal-actions {
  display: flex;
  gap: 0.4rem;
  margin-bottom: 0.5rem;
}
.my-pal-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(42px, 1fr));
  gap: 4px;
  max-height: 240px;
  overflow-y: auto;
  padding-right: 2px;
}
.my-pal-chip {
  aspect-ratio: 1;
  border: 1.5px solid rgba(0,0,0,0.12);
  border-radius: var(--radius-sm);
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1px;
  font-family: var(--font-mono);
  font-weight: 800;
  padding: 0;
  transition: transform var(--transition-fast);
}
.my-pal-chip:hover { transform: scale(1.1); z-index: 2; }
.chip-code { font-size: 0.62rem; line-height: 1; }
.chip-x {
  font-size: 0.5rem;
  line-height: 1;
  opacity: 0;
  transition: opacity var(--transition-fast);
}
.my-pal-chip:hover .chip-x { opacity: 0.85; }
</style>
