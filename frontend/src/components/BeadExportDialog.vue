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
            <img v-if="preview" :src="preview" alt="导出预览" class="export-preview-img" />
            <span v-else class="export-preview-empty">预览生成中…</span>
          </div>
          <span class="export-preview-cap">📄 导出预览 · {{ grid.width }} × {{ grid.height }}（即下载图纸的样子）</span>
        </div>

        <!-- Format cards -->
        <div class="export-formats">
          <button v-for="fmt in FORMATS" :key="fmt.id"
                  class="fmt-btn" :class="{ on: format === fmt.id }"
                  @click="format = fmt.id">
            <span class="fmt-icon">{{ fmt.icon }}</span>
            <span class="fmt-label">{{ fmt.label }}</span>
            <span class="fmt-desc">{{ fmt.desc }}</span>
          </button>
        </div>

        <!-- Format-specific options -->
        <div v-if="format === 'jpg'" class="export-opt-row">
          <label>JPEG 质量</label>
          <input type="range" min="60" max="100" step="1" v-model.number="jpgQuality" class="slider" />
          <span class="mono">{{ jpgQuality }}%</span>
        </div>
        <div v-if="format === 'svg'" class="export-opt-row">
          <label>SVG 豆型</label>
          <select class="select" v-model="svgShape">
            <option value="circle">圆形 circle</option>
            <option value="rect">方形 rect</option>
          </select>
        </div>

        <!-- Info -->
        <div class="export-info">
          <span>网格：{{ grid.width }} × {{ grid.height }}</span>
          <span>｜豆数：{{ totalBeads }} 颗</span>
          <span>｜格式：{{ format.toUpperCase() }}</span>
        </div>
        <div class="export-note">
          导出将保持当前画布的样式（豆型 / 是否标色号）
        </div>
      </div>

      <div class="modal-foot">
        <button class="btn btn-ghost" @click="$emit('close')">取消</button>
        <button class="btn btn-primary" @click="doExport">导出</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

export interface ExportGrid {
  width: number
  height: number
}

const props = defineProps<{
  grid: ExportGrid
  beadShape: string
  totalBeads: number
  mardColors: Record<string, { name: string; hex: string; rgb: [number, number, number] }>
  preview: string
}>()

const emit = defineEmits<{
  close: []
  'export-png': []
  'export-jpg': [{ quality: number }]
  'export-svg': [{ shape: 'circle' | 'rect' }]
  'export-csv': []
}>()

type ExportFormat = 'png' | 'jpg' | 'svg' | 'csv'

const FORMATS: { id: ExportFormat; icon: string; label: string; desc: string }[] = [
  { id: 'png', icon: '🖼', label: 'PNG', desc: '无损图片，适合印刷' },
  { id: 'jpg', icon: '🌈', label: 'JPEG', desc: '可调质量，适合分享' },
  { id: 'svg', icon: '✏️', label: 'SVG', desc: '矢量图，可编辑' },
  { id: 'csv', icon: '📊', label: 'CSV 材料单', desc: '色号·数量，可打印采购清单' },
]

const format = ref<ExportFormat>('png')
const jpgQuality = ref(90)
const svgShape = ref<'circle' | 'rect'>('circle')

function doExport() {
  switch (format.value) {
    case 'png': emit('export-png'); break
    case 'jpg': emit('export-jpg', { quality: jpgQuality.value }); break
    case 'svg': emit('export-svg', { shape: svgShape.value }); break
    case 'csv': emit('export-csv'); break
  }
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
.modal-body { display: flex; flex-direction: column; gap: 0.85rem; }
.modal-foot {
  display: flex; justify-content: flex-end; gap: 0.65rem;
  margin-top: 1.1rem; padding-top: 0.85rem;
  border-top: 2px dashed var(--line-strong);
}
.export-formats {
  display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem;
}
.fmt-btn {
  display: flex; flex-direction: column; align-items: center; gap: 0.15rem;
  padding: 0.65rem 0.5rem; border: 2px solid var(--cream-4); border-radius: var(--radius-md);
  background: #fff; cursor: pointer; transition: all var(--transition-fast);
}
.fmt-btn:hover { border-color: var(--sakura-light); }
.fmt-btn.on {
  border-color: var(--sakura); background: var(--sakura-glow);
  box-shadow: 0 0 0 2px var(--sakura-ring);
}
.fmt-icon { font-size: 1.5rem; }
.fmt-label { font-family: var(--font-round); font-weight: 700; font-size: 0.82rem; color: var(--plum-1); }
.fmt-desc { font-size: 0.68rem; color: var(--plum-3); text-align: center; }
.export-opt-row {
  display: flex; align-items: center; gap: 0.65rem;
  font-size: 0.8rem; color: var(--plum-2);
}
.export-info {
  text-align: center; font-size: 0.74rem; color: var(--plum-3);
  background: var(--cream-2); border-radius: var(--radius-sm); padding: 0.35rem;
}
.export-note {
  text-align: center; font-size: 0.7rem; color: var(--plum-3); line-height: 1.5;
}

/* export preview */
.export-preview { display: flex; flex-direction: column; gap: 0.3rem; }
.export-preview-stage {
  display: flex; align-items: center; justify-content: center;
  background: var(--cream-2);
  border: 2px dashed var(--line-strong);
  border-radius: var(--radius-md);
  padding: 0.5rem;
  max-height: 320px;
  overflow: hidden;
}
.export-preview-img {
  max-width: 100%;
  max-height: 300px;
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
