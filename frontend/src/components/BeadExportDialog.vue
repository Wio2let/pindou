<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal-card card">
      <div class="modal-head">
        <span class="modal-title">📦 导出图纸</span>
        <button class="modal-close" @click="$emit('close')">✕</button>
      </div>

      <div class="modal-body">
        <!-- Live preview of the exported result -->
        <div class="export-preview">
          <div class="export-preview-stage">
            <img v-if="curPreview" :src="curPreview" alt="导出预览" class="export-preview-img" />
            <span v-else class="export-preview-empty">预览生成中…</span>
          </div>
          <span class="export-preview-cap">
            📄 导出预览 · {{ grid.width }} × {{ grid.height }}（{{ gridLines ? '带网格线' : '无网格线' }}）
          </span>
        </div>

        <!-- Format cards — multi-select -->
        <div class="export-pick-hint">勾选要导出的格式 · 可多选，一次导出多个文件</div>
        <div class="export-formats">
          <button v-for="fmt in FORMATS" :key="fmt.id"
                  type="button" class="fmt-btn" :class="{ on: picked[fmt.id] }"
                  @click="picked[fmt.id] = !picked[fmt.id]">
            <span v-if="picked[fmt.id]" class="fmt-check">✓</span>
            <span class="fmt-icon">{{ fmt.icon }}</span>
            <span class="fmt-label">{{ fmt.label }}</span>
            <span class="fmt-desc">{{ fmt.desc }}</span>
          </button>
        </div>

        <!-- grid-lines toggle (applies to the PNG / JPG / SVG images) -->
        <label class="export-grid-opt">
          <input type="checkbox" v-model="gridLines" />
          <span class="export-grid-name">网格线与坐标尺</span>
          <span class="export-grid-hint">
            {{ gridLines ? '带网格线和坐标，方便照着摆豆' : '纯净图案，无网格线和坐标' }}
          </span>
        </label>

        <!-- format-specific options -->
        <div v-if="picked.jpg" class="export-opt-row">
          <label>JPEG 质量</label>
          <input type="range" min="60" max="100" step="1" v-model.number="jpgQuality" class="slider" />
          <span class="mono">{{ jpgQuality }}%</span>
        </div>
        <div v-if="picked.svg" class="export-opt-row">
          <label>SVG 豆型</label>
          <select class="select" v-model="svgShape">
            <option value="circle">圆形 circle</option>
            <option value="rect">方形 rect</option>
          </select>
        </div>

        <div class="export-info">
          <span>网格：{{ grid.width }} × {{ grid.height }}</span>
          <span>｜豆数：{{ totalBeads }} 颗</span>
          <span>｜已选 {{ selectedFormats.length }} 种格式</span>
        </div>
      </div>

      <div class="modal-foot">
        <button class="btn btn-ghost" @click="$emit('close')">取消</button>
        <button class="btn btn-primary"
                :disabled="selectedFormats.length === 0" @click="doExport">
          导出{{ selectedFormats.length > 1 ? ` ${selectedFormats.length} 个文件` : '' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from 'vue'

export interface ExportGrid {
  width: number
  height: number
}

type ExportFormat = 'png' | 'jpg' | 'svg' | 'csv'

const props = defineProps<{
  grid: ExportGrid
  beadShape: string
  totalBeads: number
  mardColors: Record<string, { name: string; hex: string; rgb: [number, number, number] }>
  preview: string        // preview with grid lines
  previewPlain: string   // preview without grid lines
}>()

const emit = defineEmits<{
  close: []
  export: [{
    formats: ExportFormat[]
    gridLines: boolean
    jpgQuality: number
    svgShape: 'circle' | 'rect'
  }]
}>()

const FORMATS: { id: ExportFormat; icon: string; label: string; desc: string }[] = [
  { id: 'png', icon: '🖼', label: 'PNG', desc: '无损图片，适合印刷' },
  { id: 'jpg', icon: '🌈', label: 'JPEG', desc: '可调质量，适合分享' },
  { id: 'svg', icon: '✏️', label: 'SVG', desc: '矢量图，可编辑' },
  { id: 'csv', icon: '📊', label: 'CSV 材料单', desc: '色号·数量，可打印采购清单' },
]

const picked = reactive<Record<ExportFormat, boolean>>({
  png: true, jpg: false, svg: false, csv: false,
})
const gridLines = ref(true)
const jpgQuality = ref(90)
const svgShape = ref<'circle' | 'rect'>('circle')

const selectedFormats = computed(() => FORMATS.map(f => f.id).filter(id => picked[id]))
const curPreview = computed(() => (gridLines.value ? props.preview : props.previewPlain))

function doExport() {
  if (selectedFormats.value.length === 0) return
  emit('export', {
    formats: selectedFormats.value,
    gridLines: gridLines.value,
    jpgQuality: jpgQuality.value,
    svgShape: svgShape.value,
  })
}
</script>

<style scoped>
.modal-overlay {
  position: fixed; inset: 0; background: rgba(74,54,69,0.35);
  display: flex; align-items: center; justify-content: center;
  z-index: 100; backdrop-filter: blur(4px);
}
.modal-card {
  width: min(520px, 92vw); padding: 1.25rem 1.5rem;
  animation: pop-in 0.3s cubic-bezier(0.34, 1.56, 0.64, 1) both;
}
.modal-head {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 1rem;
}
.modal-title { font-family: var(--font-display); font-size: 1.1rem; color: var(--plum-1); }
.modal-close { background: none; border: none; font-size: 1.2rem; cursor: pointer; color: var(--plum-3); }
.modal-close:hover { color: var(--plum-1); }
.modal-body { display: flex; flex-direction: column; gap: 0.7rem; }
.modal-foot {
  display: flex; justify-content: flex-end; gap: 0.65rem;
  margin-top: 1.1rem; padding-top: 0.85rem;
  border-top: 2px dashed var(--line-strong);
}
.export-pick-hint { font-size: 0.72rem; color: var(--plum-3); text-align: center; }
.export-formats {
  display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem;
}
.fmt-btn {
  position: relative;
  display: flex; flex-direction: column; align-items: center; gap: 0.15rem;
  padding: 0.65rem 0.5rem; border: 2px solid var(--cream-4); border-radius: var(--radius-md);
  background: #fff; cursor: pointer; transition: all var(--transition-fast);
}
.fmt-btn:hover { border-color: var(--sakura-light); }
.fmt-btn.on {
  border-color: var(--sakura); background: var(--sakura-glow);
  box-shadow: 0 0 0 2px var(--sakura-ring);
}
.fmt-check {
  position: absolute; top: 3px; right: 7px;
  font-size: 0.78rem; font-weight: 800; color: var(--sakura-deep);
}
.fmt-icon { font-size: 1.5rem; }
.fmt-label { font-family: var(--font-round); font-weight: 700; font-size: 0.82rem; color: var(--plum-1); }
.fmt-desc { font-size: 0.68rem; color: var(--plum-3); text-align: center; }
.export-grid-opt {
  display: flex; align-items: center; gap: 0.45rem;
  font-size: 0.8rem; color: var(--plum-2); cursor: pointer; user-select: none;
  background: var(--cream-2); border-radius: var(--radius-sm); padding: 0.45rem 0.65rem;
}
.export-grid-opt input { cursor: pointer; }
.export-grid-name { font-weight: 700; }
.export-grid-hint { font-size: 0.68rem; color: var(--plum-3); }
.export-opt-row {
  display: flex; align-items: center; gap: 0.65rem;
  font-size: 0.8rem; color: var(--plum-2);
}
.export-info {
  text-align: center; font-size: 0.74rem; color: var(--plum-3);
  background: var(--cream-2); border-radius: var(--radius-sm); padding: 0.35rem;
}

/* export preview */
.export-preview { display: flex; flex-direction: column; gap: 0.3rem; }
.export-preview-stage {
  display: flex; align-items: center; justify-content: center;
  background: var(--cream-2);
  border: 2px dashed var(--line-strong);
  border-radius: var(--radius-md);
  padding: 0.5rem;
  max-height: 300px;
  overflow: hidden;
}
.export-preview-img {
  max-width: 100%;
  max-height: 280px;
  object-fit: contain;
  border-radius: var(--radius-sm);
  box-shadow: var(--shadow-soft);
}
.export-preview-empty {
  font-size: 0.78rem; color: var(--plum-3); padding: 2.5rem 1rem;
}
.export-preview-cap {
  text-align: center; font-size: 0.68rem; color: var(--plum-3);
}
</style>
