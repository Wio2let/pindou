<template>
  <div class="page">
    <BeadTabs />

    <div class="header card">
      <div class="head-left">
        <span class="title">🖼️ 像素画廊</span>
        <span class="sub">
          {{ REMOTE_ENABLED
            ? '所有人的作品都能在这里看到，在工坊点「🎨 发布」即可上传'
            : '在工坊点「🎨 发布」就能把作品保存到这里（仅存于本机）' }}
        </span>
      </div>
      <div class="head-right">
        <span class="stat-chip" v-if="loading">读取中…</span>
        <span class="stat-chip"><b>{{ state.length }}</b> / {{ MAX_WORKS }} 件</span>
        <button v-if="REMOTE_ENABLED" class="btn btn-ghost btn-xs"
                @click="refresh" title="重新拉取所有作品"
                :disabled="loading">🔄 刷新</button>
        <button v-if="!REMOTE_ENABLED && state.length > 0"
                class="btn btn-ghost btn-xs danger-text"
                @click="onClearAll"
                title="清空整个画廊（不能撤销）">🗑 清空</button>
      </div>
    </div>

    <div v-if="error" class="error-bar card">
      ⚠️ 连接画廊服务器失败：{{ error }} —— 可点右上「🔄 刷新」重试
    </div>

    <!-- Empty state -->
    <div v-if="state.length === 0" class="empty card">
      <div class="empty-emoji">🌸</div>
      <div class="empty-text">画廊还是空的</div>
      <div class="empty-hint">去工坊画一张图，点工具栏上的「🎨 发布」就能放进来</div>
      <router-link to="/bead-studio" class="btn btn-primary btn-sm">去工坊</router-link>
    </div>

    <!-- Works grid -->
    <div v-else class="grid">
      <div v-for="w in state" :key="w.id" class="work-card card"
           @click="preview = w">
        <div class="thumb-wrap">
          <img :src="w.thumbnail" :alt="w.title" class="thumb" loading="lazy" />
        </div>
        <div class="meta">
          <div class="meta-title">{{ w.title }}</div>
          <div class="meta-stats">
            <span class="ms-chip">{{ w.width }}×{{ w.height }}</span>
            <span class="ms-chip">{{ w.totalBeads.toLocaleString() }} 颗</span>
            <span class="ms-chip">{{ w.uniqueColors }} 色</span>
          </div>
          <div class="meta-date">{{ fmtDate(w.createdAt) }}</div>
        </div>
        <button v-if="!REMOTE_ENABLED" class="card-x" @click.stop="onRemove(w)"
                title="从画廊删除">✕</button>
        <button v-else-if="isMine(w.id)" class="card-x mine" @click.stop="onUnpublish(w)"
                title="取消发布（只对你自己发布的作品有效）">✕</button>
        <span v-if="isMine(w.id)" class="mine-badge">我的</span>
      </div>
    </div>

    <!-- Lightbox preview -->
    <div v-if="preview" class="lightbox" @click.self="preview = null">
      <div class="lb-card card">
        <div class="lb-head">
          <span class="lb-title">{{ preview.title }}</span>
          <button class="modal-close" @click="preview = null">✕</button>
        </div>
        <div class="lb-body">
          <img :src="preview.thumbnail" :alt="preview.title" class="lb-img" />
        </div>
        <div class="lb-foot">
          <span class="ms-chip">{{ preview.width }}×{{ preview.height }}</span>
          <span class="ms-chip">{{ preview.totalBeads.toLocaleString() }} 颗</span>
          <span class="ms-chip">{{ preview.uniqueColors }} 色</span>
          <span class="ms-chip">{{ fmtDate(preview.createdAt) }}</span>
          <span class="lb-spacer"></span>
          <a class="btn btn-ghost btn-xs" :href="preview.thumbnail"
             :download="preview.title + '.png'"
             target="_blank" rel="noopener">⬇ 下载</a>
          <button v-if="REMOTE_ENABLED && isMine(preview.id)"
                  class="btn btn-ghost btn-xs danger-text"
                  @click="onUnpublish(preview); preview = null">
            🗑 取消发布
          </button>
          <button v-else-if="!REMOTE_ENABLED"
                  class="btn btn-ghost btn-xs danger-text"
                  @click="onRemove(preview); preview = null">
            🗑 删除
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import BeadTabs from '../components/BeadTabs.vue'
import { useGallery, type GalleryWork } from '../composables/useGallery'
import { useHeartTrail } from '../composables/useHeartTrail'

// Same cursor-heart particle effect as the studio page
useHeartTrail()

const {
  state, loading, error,
  remove, unpublish, isMine, clearAll, refresh, ensureHydrated,
  MAX_WORKS, REMOTE_ENABLED,
} = useGallery()

const preview = ref<GalleryWork | null>(null)

onMounted(() => { ensureHydrated() })

function fmtDate(ms: number): string {
  const d = new Date(ms)
  const yyyy = d.getFullYear()
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  const hh = String(d.getHours()).padStart(2, '0')
  const mi = String(d.getMinutes()).padStart(2, '0')
  return `${yyyy}-${mm}-${dd} ${hh}:${mi}`
}

async function onRemove(w: GalleryWork) {
  try {
    await ElMessageBox.confirm(`从画廊删除「${w.title}」？`, '删除作品', {
      confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning',
    })
    remove(w.id)
  } catch { /* cancelled */ }
}

async function onUnpublish(w: GalleryWork) {
  try {
    await ElMessageBox.confirm(
      `取消发布「${w.title}」？这会把它从画廊上彻底删掉（所有人都看不到了），不能撤销。`,
      '取消发布',
      { confirmButtonText: '取消发布', cancelButtonText: '再想想', type: 'warning' },
    )
  } catch { return /* cancelled */ }
  try {
    await unpublish(w.id)
    ElMessage.success(`「${w.title}」已从画廊取消发布`)
  } catch (e: any) {
    ElMessage.error(`取消发布失败：${e?.message || e}`)
  }
}
async function onClearAll() {
  try {
    await ElMessageBox.confirm(`清空全部 ${state.value.length} 件作品？这个操作不能撤销。`, '清空画廊', {
      confirmButtonText: '清空', cancelButtonText: '取消', type: 'warning',
    })
    clearAll()
  } catch { /* cancelled */ }
}
</script>

<style scoped>
.page { padding: 1rem 1.2rem; max-width: 1300px; margin: 0 auto; }

.header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0.9rem 1.2rem; margin-bottom: 0.9rem; gap: 0.8rem; flex-wrap: wrap;
}
.head-left { display: flex; flex-direction: column; gap: 0.15rem; }
.title { font-family: var(--font-display); font-size: 1.3rem; color: var(--plum-1); }
.sub { font-size: 0.78rem; color: var(--plum-3); }
.head-right { display: flex; align-items: center; gap: 0.5rem; }
.stat-chip {
  background: var(--cream-2); border: 1.5px solid var(--line-strong);
  border-radius: var(--radius-pill); padding: 0.22rem 0.7rem;
  font-size: 0.74rem; color: var(--plum-2);
}
.stat-chip b { color: var(--sakura-deep); font-family: var(--font-mono); }
.danger-text { color: var(--bad); }
.danger-text:hover { background: var(--bad-glow); }

.error-bar {
  padding: 0.6rem 0.9rem; margin-bottom: 0.7rem;
  background: var(--bad-glow); border: 1.5px solid var(--bad);
  color: #b22e3c; font-size: 0.85rem;
}

.empty {
  display: flex; flex-direction: column; align-items: center; gap: 0.55rem;
  padding: 3rem 1rem 2.4rem; text-align: center;
}
.empty-emoji { font-size: 3rem; line-height: 1; }
.empty-text { font-family: var(--font-display); font-size: 1.15rem; color: var(--plum-1); }
.empty-hint { font-size: 0.85rem; color: var(--plum-3); margin-bottom: 0.6rem; }

.grid {
  display: grid; gap: 0.85rem;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
}
.work-card {
  position: relative; display: flex; flex-direction: column;
  padding: 0.55rem; cursor: pointer;
  transition: all var(--transition-fast);
  overflow: hidden;
}
.work-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 6px 20px var(--sakura-glow);
}
.thumb-wrap {
  background: repeating-conic-gradient(#f7eee5 0% 25%, #ffffff 0% 50%) 0 0 / 14px 14px;
  border-radius: var(--radius-sm);
  border: 1.5px solid var(--line-strong);
  aspect-ratio: 1;
  display: flex; align-items: center; justify-content: center;
  overflow: hidden;
}
.thumb {
  max-width: 100%; max-height: 100%; object-fit: contain;
  image-rendering: pixelated;
}
.meta { display: flex; flex-direction: column; gap: 0.25rem; padding: 0.5rem 0.2rem 0.1rem; }
.meta-title {
  font-family: var(--font-display); font-size: 0.92rem; color: var(--plum-1);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.meta-stats { display: flex; gap: 0.25rem; flex-wrap: wrap; }
.ms-chip {
  background: var(--cream-2); border: 1px solid var(--line-strong);
  border-radius: var(--radius-pill); padding: 0.05rem 0.45rem;
  font-size: 0.65rem; color: var(--plum-2); font-family: var(--font-mono);
}
.meta-date { font-size: 0.66rem; color: var(--plum-3); }
.card-x {
  position: absolute; top: 0.4rem; right: 0.4rem;
  width: 1.6rem; height: 1.6rem; border-radius: 50%;
  border: none; background: rgba(255, 255, 255, 0.88);
  color: var(--plum-3); cursor: pointer; font-size: 0.8rem;
  opacity: 0; transition: all var(--transition-fast);
  display: flex; align-items: center; justify-content: center;
}
.work-card:hover .card-x { opacity: 1; }
.card-x:hover { background: var(--bad); color: #fff; }
.card-x.mine { opacity: 1; background: var(--sakura-glow); color: var(--sakura-deep); border: 1.5px solid var(--sakura); }
.card-x.mine:hover { background: var(--bad); color: #fff; border-color: var(--bad); }
.mine-badge {
  position: absolute; top: 0.4rem; left: 0.4rem;
  background: var(--sakura); color: #fff;
  font-family: var(--font-mono); font-weight: 800;
  font-size: 0.6rem; padding: 0.1rem 0.45rem;
  border-radius: var(--radius-pill);
  box-shadow: 0 1px 0 var(--sakura-deep);
  pointer-events: none;
}

/* lightbox */
.lightbox {
  position: fixed; inset: 0; background: rgba(74,54,69,0.6);
  display: flex; align-items: center; justify-content: center;
  z-index: 200; backdrop-filter: blur(6px);
}
.lb-card {
  width: min(820px, 94vw); max-height: 92vh;
  display: flex; flex-direction: column;
  padding: 1rem 1.25rem 0.85rem;
  animation: pop-in 0.3s cubic-bezier(0.34, 1.56, 0.64, 1) both;
}
.lb-head {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 0.55rem;
}
.lb-title { font-family: var(--font-display); font-size: 1.05rem; color: var(--plum-1); }
.modal-close { background: none; border: none; font-size: 1.2rem; cursor: pointer; color: var(--plum-3); }
.modal-close:hover { color: var(--plum-1); }
.lb-body {
  flex: 1; min-height: 0; display: flex; align-items: center; justify-content: center;
  background: repeating-conic-gradient(#f7eee5 0% 25%, #ffffff 0% 50%) 0 0 / 14px 14px;
  border-radius: var(--radius-md); border: 1.5px solid var(--line-strong);
  padding: 0.5rem; overflow: auto;
}
.lb-img { max-width: 100%; max-height: 70vh; object-fit: contain; image-rendering: pixelated; }
.lb-foot {
  display: flex; align-items: center; gap: 0.4rem; flex-wrap: wrap;
  padding-top: 0.6rem; border-top: 1.5px dashed var(--line-strong); margin-top: 0.45rem;
}
.lb-spacer { flex: 1; }
</style>
