<template>
  <div>
    <!-- Search Bar -->
    <div class="card" style="padding:1rem 1.25rem;">
      <div class="flex gap-2 items-end" style="flex-wrap:wrap;">
        <div class="form-row" style="flex:1; min-width:220px;">
          <label>搜索 B 站视频</label>
          <input class="input" v-model="keyword" placeholder="输入关键词…"
                 @keyup.enter="onSearchFromForm" />
        </div>
        <div class="form-row" style="width:130px;">
          <label>排序</label>
          <select class="select" v-model="order" @change="onSearchFromForm">
            <option value="totalrank">综合</option>
            <option value="click">最多播放</option>
            <option value="pubdate">最新发布</option>
            <option value="dm">最多弹幕</option>
            <option value="stow">最多收藏</option>
            <option value="scores">最多评论</option>
          </select>
        </div>
        <div class="form-row" style="width:130px;">
          <label>时长</label>
          <select class="select" v-model.number="duration" @change="onSearchFromForm">
            <option :value="0">全部</option>
            <option :value="1">10 分钟内</option>
            <option :value="2">10–30 分钟</option>
            <option :value="3">30–60 分钟</option>
            <option :value="4">60 分钟以上</option>
          </select>
        </div>
        <button class="btn btn-primary" @click="onSearchFromForm" :disabled="loading">
          {{ loading ? '搜索中…' : '搜索' }}
        </button>
      </div>
    </div>

    <!-- Results -->
    <div v-if="loading" style="margin-top:1.25rem;">
      <div class="bili-grid">
        <div v-for="i in 8" :key="i" class="skeleton" style="height:240px;"></div>
      </div>
    </div>

    <div v-else-if="errorMsg" class="empty-state" style="margin-top:2rem;">
      <div class="empty-icon">!</div>
      <div class="empty-text">{{ errorMsg }}</div>
    </div>

    <div v-else-if="videos.length === 0 && searched" class="empty-state" style="margin-top:2rem;">
      <div class="empty-icon">▶</div>
      <div class="empty-text">未找到相关视频</div>
    </div>

    <div v-else-if="videos.length > 0" style="margin-top:1.25rem;">
      <div class="flex items-center justify-between" style="margin-bottom:0.75rem; flex-wrap:wrap; gap:0.5rem;">
        <span class="text-sm text-muted">共 {{ total.toLocaleString() }} 个结果 · 第 {{ page }} 页</span>
        <div class="text-xs text-muted">点击卡片可直接打开 B 站</div>
      </div>
      <div class="bili-grid">
        <a v-for="v in videos" :key="v.bvid"
           :href="v.url" target="_blank" rel="noopener"
           class="bili-card">
          <div class="bili-cover-wrap">
            <img :src="v.pic" :alt="v.title" class="bili-cover" loading="lazy"
                 referrerpolicy="no-referrer" />
            <span class="bili-duration">{{ v.duration || '--' }}</span>
          </div>
          <div class="bili-info">
            <div class="bili-title" :title="v.title">{{ v.title }}</div>
            <div class="bili-author">
              <span class="bili-up">UP · {{ v.author }}</span>
              <span class="bili-date">{{ fmtDate(v.pubdate) }}</span>
            </div>
            <div class="bili-stats">
              <span title="播放">▶ {{ fmtNum(v.play) }}</span>
              <span title="弹幕">💬 {{ fmtNum(v.danmaku) }}</span>
              <span title="点赞">♥ {{ fmtNum(v.like) }}</span>
              <span title="收藏">★ {{ fmtNum(v.favorites) }}</span>
            </div>
            <div v-if="v.description" class="bili-desc">{{ v.description }}</div>
          </div>
        </a>
      </div>

      <!-- Pagination -->
      <div class="flex items-center justify-between" style="margin-top:1.25rem; padding:0.75rem 0;">
        <span class="text-xs text-muted">第 {{ page }} / {{ totalPages }} 页</span>
        <div class="flex gap-2">
          <button class="btn btn-ghost btn-sm" :disabled="page <= 1 || loading" @click="goPage(page - 1)">上一页</button>
          <button class="btn btn-ghost btn-sm" :disabled="page >= totalPages || loading" @click="goPage(page + 1)">下一页</button>
        </div>
      </div>
    </div>

    <div v-else class="empty-state" style="margin-top:2rem;">
      <div class="empty-icon">▶</div>
      <div class="empty-text">输入关键词开始搜索 B 站视频</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'

const keyword = ref('')
const order = ref('totalrank')
const duration = ref(0)
const videos = ref<any[]>([])
const loading = ref(false)
const searched = ref(false)
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const errorMsg = ref('')

const totalPages = computed(() => {
  if (!total.value || !pageSize.value) return 1
  return Math.max(1, Math.ceil(total.value / pageSize.value))
})

function fmtNum(n: number | string | undefined): string {
  const v = typeof n === 'number' ? n : Number(n || 0)
  if (!Number.isFinite(v) || v === 0) return '0'
  if (v >= 100_000_000) return (v / 100_000_000).toFixed(1) + '亿'
  if (v >= 10_000) return (v / 10_000).toFixed(1) + '万'
  return v.toLocaleString()
}

function fmtDate(ts: number | undefined): string {
  if (!ts) return ''
  const d = new Date(ts * 1000)
  if (Number.isNaN(d.getTime())) return ''
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

async function runSearch() {
  if (!keyword.value.trim()) return
  loading.value = true
  searched.value = true
  errorMsg.value = ''
  try {
    const res = await axios.get('/api/bilibili/search', {
      params: {
        keyword: keyword.value.trim(),
        page: page.value,
        order: order.value,
        duration: duration.value,
      },
    })
    videos.value = res.data.items || []
    total.value = res.data.total || 0
    pageSize.value = res.data.page_size || videos.value.length || 20
  } catch (e: any) {
    const detail = e?.response?.data?.detail || e?.message || '搜索失败'
    errorMsg.value = detail
    videos.value = []
    ElMessage.error(detail)
  } finally {
    loading.value = false
  }
}

function onSearchFromForm() {
  page.value = 1
  runSearch()
}

function goPage(p: number) {
  if (p < 1 || p > totalPages.value) return
  page.value = p
  runSearch()
  window.scrollTo({ top: 0, behavior: 'smooth' })
}
</script>

<style scoped>
.bili-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 1rem;
}
.bili-card {
  display: flex;
  flex-direction: column;
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  overflow: hidden;
  text-decoration: none;
  color: inherit;
  transition: all var(--transition-fast);
}
.bili-card:hover {
  border-color: var(--accent);
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}
.bili-cover-wrap {
  position: relative;
  aspect-ratio: 16 / 10;
  background: var(--bg-surface);
  overflow: hidden;
}
.bili-cover {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform var(--transition-fast);
}
.bili-card:hover .bili-cover { transform: scale(1.03); }
.bili-duration {
  position: absolute;
  bottom: 6px;
  right: 6px;
  background: rgba(0,0,0,0.78);
  color: #fff;
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 0.714rem;
  font-family: var(--font-mono);
}
.bili-info {
  padding: 0.7rem 0.8rem 0.8rem;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  flex: 1;
}
.bili-title {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  font-size: 0.9rem;
  font-weight: 600;
  line-height: 1.4;
  color: var(--text-primary);
}
.bili-card:hover .bili-title { color: var(--accent); }
.bili-author {
  display: flex;
  justify-content: space-between;
  font-size: 0.75rem;
  color: var(--text-secondary);
}
.bili-up {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-right: 0.5rem;
}
.bili-date { color: var(--text-muted); font-family: var(--font-mono); }
.bili-stats {
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem;
  font-size: 0.714rem;
  color: var(--text-muted);
}
.bili-desc {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  font-size: 0.75rem;
  color: var(--text-secondary);
  line-height: 1.45;
  margin-top: 0.15rem;
}
</style>
