<template>
  <div class="detail-page">
    <!-- Task Header -->
    <div class="card task-header" style="padding:1rem 1.25rem;">
      <div class="flex items-center justify-between">
        <div>
          <div class="flex items-center gap-2">
            <div style="font-size:1.1rem; font-weight:600;">{{ task?.name || '加载中...' }}</div>
            <div class="status-lamp" :class="`lamp-${lampState}`" :title="statusLabel(task?.status||'unknown')">
              <span class="lamp-dot"></span>
              <span class="lamp-text">{{ statusLabel(task?.status||'unknown') }}</span>
            </div>
          </div>
        </div>
        <div class="flex gap-2">
          <button class="btn btn-primary btn-sm" @click="handleRun" :disabled="running">{{ running ? '运行中...' : '运行' }}</button>
          <button class="btn btn-danger btn-sm" @click="handleStop" :disabled="!isRunning">停止</button>
          <router-link :to="`/tasks/${taskId}/edit`" class="btn btn-ghost btn-sm">编辑</router-link>
          <router-link :to="`/tasks/${taskId}/search`" class="btn btn-ghost btn-sm">搜索评论</router-link>
        </div>
      </div>
      <div class="flex gap-3 mt-2">
        <span class="text-xs text-muted">间隔: {{ task?.interval_minutes }}分</span>
        <span class="text-xs text-muted">上限: {{ task?.max_posts_per_run }}帖</span>
        <span class="text-xs text-muted">上次: {{ task?.last_run_at ? fmt(task.last_run_at) : '从未' }}</span>
      </div>
    </div>

    <!-- Posts + Images + Comments — drag splitters to resize -->
    <div class="detail-grid">
      <!-- Post Cards -->
      <div class="col-resizable" :style="{ width: widthPosts + 'px' }">
        <div class="flex items-center justify-between" style="margin-bottom:0.75rem; gap:0.5rem; flex-wrap:wrap;">
          <span class="text-sm text-muted">
            帖子（{{ posts.length }}）
            <template v-if="selectedNoteIds.length">
              · 已选 {{ selectedNoteIds.length }}
            </template>
            <span class="text-xs" style="margin-left:0.5rem; color:var(--text-muted);" title="先点一个复选框作为起点，再按住 Shift 点另一个复选框，可一次选中/取消中间所有项">提示: Shift+点 可范围选择</span>
          </span>
          <div class="flex items-center gap-2">
            <button class="btn btn-primary btn-xs"
                    :disabled="batchRefreshing || posts.length === 0"
                    @click="handleBatchRefresh"
                    title="批量为缺配图或缺评论的帖子抓取所有数据">
              {{ batchRefreshing ? `抓取中…(~${batchDone}/${batchTotal})` : '批量抓取' }}
            </button>
            <button v-if="selectedNoteIds.length" class="btn btn-danger btn-xs" @click="handleBulkDelete">
              删除选中
            </button>
            <button class="btn btn-ghost btn-xs" @click="toggleSelectAll">
              {{ allSelected ? '取消全选' : '全选' }}
            </button>
            <select class="select" v-model="sortBy" style="width:auto; padding:0.25rem 0.5rem; font-size:0.786rem;" @change="loadPosts">
              <option value="crawled">最新</option>
              <option value="likes">最多赞</option>
              <option value="comments">最多评论</option>
              <option value="collected">最多收藏</option>
            </select>
          </div>
        </div>

        <!-- Filter bar -->
        <div class="filter-bar">
          <label class="filter-cell">
            <span class="filter-label">最少 ♥</span>
            <input class="input" type="number" min="0" v-model.number="filterMinLikes"
                   @keyup.enter="loadPosts" placeholder="0" />
          </label>
          <label class="filter-cell">
            <span class="filter-label">最少 💬</span>
            <input class="input" type="number" min="0" v-model.number="filterMinComments"
                   @keyup.enter="loadPosts" placeholder="0" />
          </label>
          <label class="filter-cell">
            <span class="filter-label">最少 ★收藏</span>
            <input class="input" type="number" min="0" v-model.number="filterMinCollected"
                   @keyup.enter="loadPosts" placeholder="0" />
          </label>
          <div class="flex gap-1">
            <button class="btn btn-primary btn-xs" @click="loadPosts">应用</button>
            <button class="btn btn-ghost btn-xs" @click="resetFilters">清空</button>
          </div>
        </div>

        <div class="posts-scroll">
        <div v-if="loadingPosts">
          <div v-for="i in 4" :key="i" class="skeleton" style="height:90px; margin-bottom:0.75rem;"></div>
        </div>
        <div v-else-if="posts.length === 0" class="empty-state">
          <div class="empty-icon">◇</div>
          <div class="empty-text">暂无帖子</div>
        </div>
        <div v-else class="post-list">
          <div v-for="(post, index) in posts" :key="post.note_id"
            class="post-card"
            :class="{ active: selectedNoteId === post.note_id }"
            @click="selectPost(post.note_id)">
            <div class="flex items-start gap-2">
              <input type="checkbox" :checked="selectedNoteIds.includes(post.note_id)"
                     @click.stop="onCheckboxClick($event, index)"
                     style="margin-top:0.25rem; cursor:pointer;" />
              <img v-if="firstImage(post)"
                   :src="firstImage(post)"
                   :alt="post.title"
                   class="post-thumb"
                   loading="lazy"
                   referrerpolicy="no-referrer"
                   @error="onImgError" />
              <div v-else class="post-thumb post-thumb-empty">无图</div>
              <div style="flex:1; min-width:0;">
                <div class="post-title">{{ post.title || '无标题' }}</div>
                <div class="post-desc">{{ post.desc?.slice(0, 80) || '' }}</div>
                <div class="flex items-center justify-between" style="margin-top:0.4rem; gap:0.5rem;">
                  <div class="post-meta">
                    <span>{{ post.author_name }}</span>
                    <span>♥ {{ post.liked_count }}</span>
                    <span>💬 {{ post.comment_count }}</span>
                  </div>
                  <div class="flex gap-1">
                    <a :href="postUrl(post)"
                       target="_blank"
                       rel="noopener"
                       class="btn btn-primary btn-xs"
                       @click.stop>
                      打开原文 ↗
                    </a>
                    <button class="btn btn-danger btn-xs"
                            @click.stop="handleDeletePost(post)">
                      删除
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
        </div><!-- /.posts-scroll -->
      </div>

      <!-- Splitter 1: posts | images -->
      <div class="splitter" @mousedown="startResize('left', $event)"
           title="拖动调整宽度，双击复位"
           @dblclick="resetWidths"></div>

      <!-- Images Panel — carousel -->
      <div class="card col-resizable" :style="{ padding: 0, width: widthImages + 'px' }">
        <div class="flex items-center justify-between" style="padding:0.7rem 1rem; border-bottom:1px solid var(--border-subtle);">
          <div>
            <span class="text-sm" style="font-weight:600;">配图</span>
            <span v-if="selectedImages.length" class="text-xs text-muted" style="margin-left:0.4rem;">
              {{ carouselIndex + 1 }} / {{ selectedImages.length }}
            </span>
            <span v-if="selectedPost" class="text-xs text-muted" style="margin-left:0.5rem;">
              · {{ selectedPost.author_name }}
            </span>
          </div>
          <button v-if="selectedNoteId" class="btn btn-primary btn-xs"
                  :disabled="refreshingAny"
                  @click="refreshAllNow"
                  title="同时去小红书实时抓配图和评论">
            {{ refreshingAny ? '抓取中…' : '抓取配图+评论' }}
          </button>
        </div>

        <div v-if="!selectedNoteId" class="empty-state" style="padding:2rem 1rem;">
          <div class="empty-icon">▣</div>
          <div class="empty-text">请选择左侧帖子</div>
        </div>

        <div v-else-if="refreshingImages" class="empty-state" style="padding:2rem 1rem;">
          <div class="empty-icon">⏳</div>
          <div class="empty-text">正在抓取配图…</div>
        </div>

        <div v-else-if="selectedImages.length === 0" class="empty-state" style="padding:2rem 1rem;">
          <div class="empty-icon">▣</div>
          <div class="empty-text">该帖暂无配图</div>
          <div class="text-xs text-muted" style="margin-top:0.3rem;">
            可点列表顶部「批量抓取」或本面板「抓取配图+评论」
          </div>
        </div>

        <!-- Video posts: real player. Image posts: image carousel. -->
        <div v-else-if="isVideoPost" class="carousel">
          <div class="carousel-stage video-stage">
            <video
              :src="selectedPost?.video_url"
              :poster="selectedImages[0] || ''"
              controls
              preload="metadata"
              referrerpolicy="no-referrer"
              playsinline
              class="video-player"
              @error="onVideoError">
              <source :src="selectedPost?.video_url" />
              你的浏览器不支持视频播放
            </video>
          </div>
          <div v-if="videoFailed" class="video-fallback-note">
            视频加载失败（XHS 防盗链）。
            <a :href="postUrl(selectedPost!)" target="_blank" rel="noopener">去原帖播放 ↗</a>
          </div>
        </div>

        <div v-else class="carousel">
          <div class="carousel-stage">
            <button class="carousel-arrow left" @click="prevImage" :disabled="selectedImages.length < 2">‹</button>
            <a :href="selectedImages[carouselIndex]" target="_blank" rel="noopener" class="carousel-img-wrap">
              <img :src="selectedImages[carouselIndex]"
                   referrerpolicy="no-referrer"
                   @error="onImgError" />
            </a>
            <button class="carousel-arrow right" @click="nextImage" :disabled="selectedImages.length < 2">›</button>
          </div>
          <div v-if="selectedImages.length > 1 && selectedImages.length <= 12" class="carousel-dots">
            <button v-for="(_, i) in selectedImages" :key="i"
                    class="carousel-dot"
                    :class="{ active: i === carouselIndex }"
                    @click="carouselIndex = i"></button>
          </div>
        </div>
      </div>

      <!-- Splitter 2: images | comments -->
      <div class="splitter" @mousedown="startResize('right', $event)"
           title="拖动调整宽度，双击复位"
           @dblclick="resetWidths"></div>

      <!-- Comments Panel -->
      <div class="card col-flex" style="padding:0;">
        <div style="padding:0.7rem 1rem; border-bottom:1px solid var(--border-subtle);">
          <span class="text-sm" style="font-weight:600;">评论（{{ comments.length }}）</span>
          <span v-if="refreshingComments" class="text-xs text-muted" style="margin-left:0.5rem;">
            抓取中…
          </span>
        </div>
        <div v-if="loadingComments" style="padding:1rem;">
          <div v-for="i in 4" :key="i" class="skeleton" style="height:3.5rem; margin-bottom:0.5rem;"></div>
        </div>
        <div v-else-if="!selectedNoteId" class="empty-state" style="padding:2rem 1rem;">
          <div class="empty-icon">◈</div>
          <div class="empty-text">请选择左侧帖子</div>
        </div>
        <div v-else-if="comments.length === 0" class="empty-state" style="padding:2rem 1rem;">
          <div class="empty-icon">◈</div>
          <div class="empty-text">该帖暂无评论</div>
        </div>
        <div v-else class="comment-scroll">
          <div v-for="c in comments" :key="c.id" class="comment-item">
            <div class="flex items-center justify-between">
              <span class="comment-user">{{ c.user_name }}</span>
              <div class="flex items-center gap-2">
                <span class="badge" :class="usefulnessBadge(c.usefulness_label)">{{ c.usefulness_label }}</span>
                <button class="fav-btn" :class="{ on: c.favorite }"
                        @click="toggleFavorite(c)"
                        :title="c.favorite ? '取消收藏' : '收藏'">
                  {{ c.favorite ? '♥' : '♡' }}
                </button>
              </div>
            </div>
            <div class="comment-content">{{ c.content }}</div>
            <div v-if="commentImages(c).length" class="comment-pics">
              <a v-for="(u, i) in commentImages(c)" :key="i"
                 :href="u" target="_blank" rel="noopener"
                 class="comment-pic-cell"
                 :title="`点击查看大图 (${i + 1}/${commentImages(c).length})`">
                <img :src="u"
                     loading="lazy"
                     referrerpolicy="no-referrer"
                     @error="onImgError" />
              </a>
            </div>
            <div v-if="c.favorite" class="comment-category">
              <input class="cat-input"
                     :value="c.category"
                     :placeholder="'分类标签 (回车保存)'"
                     :list="`cat-options-${c.id}`"
                     @keyup.enter="(e: any) => saveCategory(c, e.target.value)"
                     @blur="(e: any) => saveCategory(c, e.target.value)" />
              <datalist :id="`cat-options-${c.id}`">
                <option v-for="cat in knownCategories" :key="cat" :value="cat" />
              </datalist>
              <span v-if="c.category" class="cat-tag">#{{ c.category }}</span>
            </div>
            <div class="comment-footer">
              <span>♥ {{ c.liked_count }}</span>
              <span v-if="c.ip_location">{{ c.ip_location }}</span>
              <span v-if="c.is_actionable" class="badge badge-warning" style="font-size:0.643rem;">实用</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, reactive } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useTasks } from '../composables/useTasks'
import { usePosts, type Post } from '../composables/usePosts'
import { useComments, type Comment } from '../composables/useComments'

const props = defineProps<{ id: string }>()
const route = useRoute(); const router = useRouter()
const taskId = computed(() => Number(props.id || route.params.id))
const { get: getTask, run: runTask, stopTask, getStatus } = useTasks()
const { list: listPosts, remove: removePost, bulkRemove: bulkRemovePosts, refreshAll, refreshAllPosts } = usePosts()
const { listByPost, update: updateComment, listCategories } = useComments()

const task = ref<any>(null)
const loadingPosts = ref(false)
const loadingComments = ref(false)
const running = ref(false)
const isRunning = ref(false)
const posts = ref<Post[]>([])
const comments = ref<Comment[]>([])
const selectedNoteId = ref('')
const selectedNoteIds = ref<string[]>([])
const lastCheckedIndex = ref<number>(-1)
const sortBy = ref('crawled')
const filterMinLikes = ref<number>(0)
const filterMinComments = ref<number>(0)
const filterMinCollected = ref<number>(0)
const carouselIndex = ref(0)
const refreshingImages = ref(false)
const refreshingComments = ref(false)
const batchRefreshing = ref(false)
const batchDone = ref(0)
const batchTotal = ref(0)

const allSelected = computed(() => posts.value.length > 0 && selectedNoteIds.value.length === posts.value.length)
const refreshingAny = computed(() => refreshingImages.value || refreshingComments.value)

// ---- Column widths (drag-resizable, persisted to localStorage) ----
const DEFAULT_W_POSTS = 560
const DEFAULT_W_IMAGES = 480
const MIN_COL_W = 240
const widthPosts = ref(DEFAULT_W_POSTS)
const widthImages = ref(DEFAULT_W_IMAGES)
const draggingSide = ref<'left'|'right'|null>(null)
let dragStartX = 0
let dragStartPosts = 0
let dragStartImages = 0

function startResize(side: 'left'|'right', e: MouseEvent) {
  draggingSide.value = side
  dragStartX = e.clientX
  dragStartPosts = widthPosts.value
  dragStartImages = widthImages.value
  document.addEventListener('mousemove', onResize)
  document.addEventListener('mouseup', endResize)
  document.body.style.cursor = 'col-resize'
  document.body.style.userSelect = 'none'
  e.preventDefault()
}
function onResize(e: MouseEvent) {
  const dx = e.clientX - dragStartX
  if (draggingSide.value === 'left') {
    widthPosts.value = Math.max(MIN_COL_W, dragStartPosts + dx)
  } else if (draggingSide.value === 'right') {
    widthImages.value = Math.max(MIN_COL_W, dragStartImages + dx)
  }
}
function endResize() {
  draggingSide.value = null
  document.removeEventListener('mousemove', onResize)
  document.removeEventListener('mouseup', endResize)
  document.body.style.cursor = ''
  document.body.style.userSelect = ''
  saveWidths()
}
function resetWidths() {
  widthPosts.value = DEFAULT_W_POSTS
  widthImages.value = DEFAULT_W_IMAGES
  saveWidths()
}
function saveWidths() {
  try {
    localStorage.setItem('taskDetailColWidths',
      JSON.stringify({ posts: widthPosts.value, images: widthImages.value }))
  } catch {}
}
function loadWidths() {
  try {
    const raw = localStorage.getItem('taskDetailColWidths')
    if (!raw) return
    const w = JSON.parse(raw)
    if (typeof w?.posts === 'number')  widthPosts.value  = Math.max(MIN_COL_W, w.posts)
    if (typeof w?.images === 'number') widthImages.value = Math.max(MIN_COL_W, w.images)
  } catch {}
}

const selectedPost = computed(() =>
  posts.value.find(p => p.note_id === selectedNoteId.value) || null
)
const isVideoPost = computed(() => {
  const p = selectedPost.value
  if (!p) return false
  if ((p.type || '').toLowerCase() !== 'video') return false
  const v: any = (p as any).video_url
  return typeof v === 'string' && v.length > 0
})
const videoFailed = ref(false)
function onVideoError() { videoFailed.value = true }

const selectedImages = computed<string[]>(() => {
  const p = selectedPost.value
  if (!p?.image_urls) return []
  try {
    const arr = JSON.parse(p.image_urls)
    return Array.isArray(arr) ? arr.filter((u: any) => !!u).map(String) : []
  } catch { return [] }
})

function statusLabel(s:string){const m:Record<string,string>={idle:'空闲',running:'运行中',error:'错误',paused:'已暂停'};return m[s]||'未知'}

const lampState = computed(() => {
  const s = task.value?.status
  if (s === 'running') return 'running'
  if (s === 'error') return 'error'
  if (s === 'paused') return 'paused'
  if (s === 'idle') return 'idle'
  return 'unknown'
})
function usefulnessBadge(l:string){const m:Record<string,string>={high:'badge-success',medium:'badge-warning',low:'badge-neutral'};return m[l]||'badge-neutral'}
function fmt(t:string){return new Date(t).toLocaleString('zh-CN')}

async function loadTask() {
  try { task.value = await getTask(taskId.value) }
  catch { ElMessage.error('任务不存在'); router.push('/tasks') }
}

async function loadPosts() {
  loadingPosts.value = true
  try {
    posts.value = await listPosts(taskId.value, {
      sort: sortBy.value,
      per_page: 50,
      min_likes: filterMinLikes.value || 0,
      min_comments: filterMinComments.value || 0,
      min_collected: filterMinCollected.value || 0,
    })
    lastCheckedIndex.value = -1
    // Auto-select first post AND load its comments so the panels aren't empty.
    if (posts.value.length) {
      const initial = posts.value.find(p => p.note_id === selectedNoteId.value)
        ? selectedNoteId.value
        : posts.value[0].note_id
      await selectPost(initial)
    } else {
      selectedNoteId.value = ''
      comments.value = []
    }
  } catch {
    ElMessage.error('加载失败')
  } finally {
    loadingPosts.value = false
  }
}

// Track which notes we've already attempted to refresh this session
// so we don't hammer the backend on every re-click. reactive() so the
// template's `.has()` check tracks mutations.
const refreshedNotes = reactive(new Set<string>())

function imagesAreUsable(post: Post | null | undefined): boolean {
  if (!post?.image_urls) return false
  try {
    const arr = JSON.parse(post.image_urls)
    if (!Array.isArray(arr)) return false
    return arr.some(u => typeof u === 'string' && u.startsWith('http'))
  } catch { return false }
}

async function selectPost(nid: string) {
  selectedNoteId.value = nid
  carouselIndex.value = 0
  videoFailed.value = false
  if (!nid) { comments.value = []; return }

  // Just read from DB — no automatic Chrome navigation.
  // To fetch fresh data, the user clicks the top-of-list "批量抓取" button
  // or the per-post "抓取配图+评论" button in the image panel.
  loadingComments.value = true
  try {
    comments.value = await listByPost(nid, { sort: 'score', min_score: 0 })
  } catch {
    comments.value = []
  } finally {
    loadingComments.value = false
  }
}

async function refreshAllNow() {
  const p = selectedPost.value
  if (!p || refreshingAny.value) return
  refreshingImages.value = true
  refreshingComments.value = true
  refreshedNotes.add(p.note_id)
  try {
    const r = await refreshAll(p.note_id, 50)
    // Apply images
    if (r.images?.length) {
      p.image_urls = JSON.stringify(r.images)
      if (selectedNoteId.value === p.note_id) carouselIndex.value = 0
    }
    // Reload comments from DB so the freshly saved ones show with scoring
    if (selectedNoteId.value === p.note_id) {
      comments.value = await listByPost(p.note_id, { sort: 'score', min_score: 0 })
    }
    // Summary toast
    const parts: string[] = []
    parts.push(`配图 ${r.image_count} 张`)
    if (r.comments_saved > 0) parts.push(`新增评论 ${r.comments_saved} 条`)
    else if (r.comments_fetched > 0) parts.push(`评论 ${r.comments_fetched} 条 (已存在)`)
    else parts.push('评论 0 条')
    ElMessage.success('抓取完成：' + parts.join('、'))
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '抓取失败')
  } finally {
    refreshingImages.value = false
    refreshingComments.value = false
  }
}

function prevImage() {
  if (!selectedImages.value.length) return
  carouselIndex.value = (carouselIndex.value - 1 + selectedImages.value.length) % selectedImages.value.length
}
function nextImage() {
  if (!selectedImages.value.length) return
  carouselIndex.value = (carouselIndex.value + 1) % selectedImages.value.length
}

function resetFilters() {
  filterMinLikes.value = 0
  filterMinComments.value = 0
  filterMinCollected.value = 0
  loadPosts()
}

async function handleRun() {
  running.value = true; isRunning.value = true
  try { await runTask(taskId.value); ElMessage.success('已启动，完成后刷新页面') }
  catch { isRunning.value = false }
  finally { running.value = false }
}
async function handleStop() {
  try { await stopTask(taskId.value); isRunning.value = false; ElMessage.success('已停止') }
  catch { ElMessage.error('停止失败') }
}

function setSelected(noteId: string, shouldSelect: boolean) {
  const i = selectedNoteIds.value.indexOf(noteId)
  if (shouldSelect && i < 0) selectedNoteIds.value.push(noteId)
  else if (!shouldSelect && i >= 0) selectedNoteIds.value.splice(i, 1)
}

function onCheckboxClick(e: MouseEvent, index: number) {
  const target = e.target as HTMLInputElement
  const shouldSelect = target.checked
  const post = posts.value[index]
  if (!post) return

  if (e.shiftKey && lastCheckedIndex.value >= 0 && lastCheckedIndex.value !== index) {
    const [start, end] = lastCheckedIndex.value < index
      ? [lastCheckedIndex.value, index]
      : [index, lastCheckedIndex.value]
    for (let i = start; i <= end; i++) {
      const p = posts.value[i]
      if (p) setSelected(p.note_id, shouldSelect)
    }
  } else {
    setSelected(post.note_id, shouldSelect)
  }
  lastCheckedIndex.value = index
}

function toggleSelectAll() {
  selectedNoteIds.value = allSelected.value ? [] : posts.value.map(p => p.note_id)
  lastCheckedIndex.value = -1
}

// ---- Favorites + category ----
const knownCategories = ref<string[]>([])

async function refreshKnownCategories() {
  try {
    const r = await listCategories(taskId.value)
    knownCategories.value = r.categories.map((x: any) => x.category).filter(Boolean)
  } catch { /* keep last */ }
}

async function toggleFavorite(c: Comment) {
  const wantOn = !c.favorite
  try {
    const updated = await updateComment(c.id, { favorite: wantOn })
    Object.assign(c, updated)
    if (wantOn) ElMessage.success('已加入收藏')
    else ElMessage.info('已取消收藏')
    refreshKnownCategories()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '操作失败')
  }
}

async function saveCategory(c: Comment, raw: string) {
  const next = (raw || '').trim()
  if (next === c.category) return
  try {
    const updated = await updateComment(c.id, { category: next })
    Object.assign(c, updated)
    refreshKnownCategories()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '分类保存失败')
  }
}

function commentImages(c: Comment): string[] {
  if (!c?.pictures) return []
  try {
    const arr = JSON.parse(c.pictures)
    return Array.isArray(arr) ? arr.filter((u: any) => typeof u === 'string' && u.startsWith('http')) : []
  } catch { return [] }
}

function firstImage(post: Post): string {
  if (!post?.image_urls) return ''
  try {
    const arr = JSON.parse(post.image_urls)
    return Array.isArray(arr) && arr.length ? String(arr[0] || '') : ''
  } catch { return '' }
}

function postUrl(post: Post): string {
  // Prefer the stored URL (which now includes xsec_token for new crawls).
  if (post.url && post.url.includes('xsec_token=')) return post.url
  if (post.xsec_token) {
    const t = encodeURIComponent(post.xsec_token)
    const s = encodeURIComponent(post.xsec_source || 'pc_search')
    return `https://www.xiaohongshu.com/explore/${post.note_id}?xsec_token=${t}&xsec_source=${s}`
  }
  // Fallback — will likely show the QR-code block, but we'd rather hand the
  // user *something* than nothing.
  return `https://www.xiaohongshu.com/explore/${post.note_id}`
}
function onImgError(e: Event) {
  const el = e.target as HTMLImageElement
  el.style.visibility = 'hidden'
}

async function handleDeletePost(post: Post) {
  try {
    await ElMessageBox.confirm(
      `确认删除「${post.title || post.note_id}」及其评论吗？`,
      '删除帖子',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
  } catch { return }
  try {
    await removePost(post.note_id)
    posts.value = posts.value.filter(p => p.note_id !== post.note_id)
    selectedNoteIds.value = selectedNoteIds.value.filter(id => id !== post.note_id)
    lastCheckedIndex.value = -1
    if (selectedNoteId.value === post.note_id) {
      const next = posts.value[0]?.note_id || ''
      await selectPost(next)
    }
    ElMessage.success('已删除')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '删除失败')
  }
}

async function handleBatchRefresh() {
  if (batchRefreshing.value || posts.value.length === 0) return
  try {
    await ElMessageBox.confirm(
      `将为所有缺配图或缺评论的帖子批量抓取数据（封面 + 全部配图 + 评论）。\n这会逐个打开小红书页面，可能需要几分钟。`,
      '批量抓取',
      { type: 'info', confirmButtonText: '开始', cancelButtonText: '取消' },
    )
  } catch { return }

  batchRefreshing.value = true
  batchDone.value = 0
  // Rough upper bound — we can't know server-side count without a probe.
  // Use total posts so the progress fraction makes sense.
  batchTotal.value = posts.value.length

  const tickStart = Date.now()
  const tick = window.setInterval(() => {
    // ~5s per post (detail + comments)
    const elapsed = (Date.now() - tickStart) / 1000
    const est = Math.min(Math.floor(elapsed / 5), batchTotal.value - 1)
    if (est > batchDone.value) batchDone.value = est
  }, 1000)

  try {
    const r = await refreshAllPosts(taskId.value, 200)
    batchDone.value = r.processed
    if (r.needed_refresh === 0) {
      ElMessage.info('所有帖子的配图和评论都已是最新')
    } else {
      let msg = `批量抓取完成：处理 ${r.processed} 个帖子`
      msg += `（新增配图 ${r.images_added}，新增评论 ${r.comments_added}）`
      if (r.failed) msg += `，失败 ${r.failed}`
      if (r.skipped_no_token) msg += `，缺 token 跳过 ${r.skipped_no_token}`
      if (r.images_added + r.comments_added > 0) ElMessage.success(msg)
      else ElMessage.warning(msg)
    }
    // Reload posts list so new image_urls show up; also reload current comments
    await loadPosts()
    if (selectedNoteId.value) {
      try {
        comments.value = await listByPost(selectedNoteId.value, { sort: 'score', min_score: 0 })
      } catch {}
    }
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '批量抓取失败')
  } finally {
    clearInterval(tick)
    batchRefreshing.value = false
    batchDone.value = 0
    batchTotal.value = 0
  }
}

async function handleBulkDelete() {
  if (!selectedNoteIds.value.length) return
  try {
    await ElMessageBox.confirm(
      `确认删除选中的 ${selectedNoteIds.value.length} 个帖子及其评论吗？`,
      '批量删除',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
  } catch { return }
  try {
    const n = await bulkRemovePosts(taskId.value, [...selectedNoteIds.value])
    const removed = new Set(selectedNoteIds.value)
    posts.value = posts.value.filter(p => !removed.has(p.note_id))
    if (removed.has(selectedNoteId.value)) {
      const next = posts.value[0]?.note_id || ''
      await selectPost(next)
    }
    selectedNoteIds.value = []
    lastCheckedIndex.value = -1
    ElMessage.success(`已删除 ${n} 个帖子`)
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '删除失败')
  }
}

let statusTimer: number | undefined
async function pollStatus() {
  try {
    const s = await getStatus(taskId.value)
    if (task.value) {
      const wasRunning = task.value.status === 'running'
      task.value.status = s.status
      task.value.last_run_at = s.last_run_at
      task.value.next_run_at = s.next_run_at
      isRunning.value = s.status === 'running'
      // Auto-refresh posts when a run just finished.
      if (wasRunning && s.status !== 'running') {
        await loadPosts()
      }
    }
  } catch { /* swallow — keep polling */ }
}
function startPolling() {
  if (statusTimer) return
  statusTimer = window.setInterval(pollStatus, 3000)
}
function stopPolling() {
  if (statusTimer) { clearInterval(statusTimer); statusTimer = undefined }
}

onMounted(() => {
  loadWidths(); loadTask(); loadPosts(); startPolling(); refreshKnownCategories()
})
onBeforeUnmount(() => { stopPolling(); endResize() })
</script>

<style scoped>
.status-lamp {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.78rem;
  font-weight: 700;
  font-family: var(--font-round);
  padding: 0.25rem 0.8rem;
  border-radius: 999px;
  background: #fff;
  border: 1.5px solid var(--cream-4);
  color: var(--plum-2);
  user-select: none;
  box-shadow: var(--shadow-soft);
}
.lamp-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: var(--plum-3);
  flex-shrink: 0;
  position: relative;
}
.lamp-running .lamp-dot {
  background: var(--warn);
  box-shadow: 0 0 8px var(--warn);
  animation: lamp-pulse 1.4s ease-out infinite;
}
.lamp-running { color: #c87b1f; border-color: var(--warn); background: var(--warn-glow); }
.lamp-idle .lamp-dot   { background: var(--ok); box-shadow: 0 0 8px var(--ok); }
.lamp-idle             { color: var(--ok); border-color: var(--ok); background: var(--ok-glow); }
.lamp-error .lamp-dot  { background: var(--bad); box-shadow: 0 0 8px var(--bad); }
.lamp-error            { color: var(--bad); border-color: var(--bad); background: var(--bad-glow); }
.lamp-paused .lamp-dot { background: var(--plum-3); }
.lamp-paused           { color: var(--plum-2); border-color: var(--cream-4); background: var(--cream-2); }
.lamp-unknown .lamp-dot{ background: var(--plum-4); animation: lamp-blink 1.6s ease-in-out infinite; }
.lamp-unknown          { color: var(--plum-3); border-color: var(--line); background: #fff; }

@keyframes lamp-pulse {
  0%   { box-shadow: 0 0 0 0   rgba(255, 184, 74, 0.55); }
  70%  { box-shadow: 0 0 0 10px rgba(255, 184, 74, 0);   }
  100% { box-shadow: 0 0 0 0   rgba(255, 184, 74, 0);    }
}
@keyframes lamp-blink {
  0%, 100% { opacity: 0.4; }
  50%      { opacity: 1; }
}

/* Root — fill the viewport-locked .main, header fixed, grid scrolls inside */
.detail-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  gap: 1rem;
}
.task-header { flex: 0 0 auto; }

/* Big panels shouldn't lift/jump on hover like small cards do */
.detail-page > .card:hover,
.detail-grid > .card:hover { transform: none; }

.detail-grid {
  display: flex;
  align-items: stretch;
  gap: 0;
  flex: 1 1 auto;
  min-height: 0;          /* critical: lets children scroll instead of grow */
}

/* Posts column */
.col-resizable {
  flex-shrink: 0;
  min-width: 240px;
  display: flex;
  flex-direction: column;
  min-height: 0;
}
.col-flex {
  flex: 1 1 0;
  min-width: 240px;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

/* Internal scroll area of the posts column */
.posts-scroll {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  padding-right: 2px;
}

.splitter {
  flex: 0 0 10px;
  cursor: col-resize;
  position: relative;
  user-select: none;
  background: transparent;
  margin: 0 0.35rem;
}
.splitter::before {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 3px;
  height: 40px;
  background: var(--border-default, #d4d4d4);
  border-radius: 2px;
  transition: background 0.15s, height 0.15s;
}
.splitter:hover::before {
  background: var(--accent, #b45309);
  height: 60px;
}
.splitter:active::before {
  background: var(--accent, #b45309);
  height: 80%;
}

@media (max-width: 900px) {
  .detail-grid { flex-direction: column; }
  .splitter { display: none; }
  .col-resizable, .col-flex {
    width: auto !important;
    flex: 1 1 auto !important;
  }
}

.post-card {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  padding: 0.85rem;
  margin-bottom: 0.625rem;
  cursor: pointer;
  transition: all var(--transition-fast);
}
.post-card:hover { border-color: var(--border-default); box-shadow: var(--shadow-sm); }
.post-card.active { border-color: var(--accent); background: var(--accent-bg); }
.post-thumb {
  width: 64px;
  height: 64px;
  object-fit: cover;
  border-radius: var(--radius-sm);
  background: var(--bg-surface);
  flex-shrink: 0;
}
.post-thumb-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.7rem;
  color: var(--text-muted);
  border: 1px dashed var(--border-subtle);
}
.post-title { font-size: 0.9rem; font-weight: 600; }
.post-desc { font-size: 0.786rem; color: var(--text-secondary); margin-top: 0.2rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.post-meta { font-size: 0.714rem; color: var(--text-muted); display: flex; gap: 0.75rem; }

.filter-bar {
  display: flex;
  align-items: end;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  margin-bottom: 0.75rem;
  background: var(--bg-surface, #f8f6f2);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  flex-wrap: wrap;
}
.filter-cell {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  min-width: 90px;
}
.filter-cell .input {
  padding: 0.25rem 0.4rem;
  font-size: 0.786rem;
  width: 100%;
}
.filter-label {
  font-size: 0.7rem;
  color: var(--text-muted);
}

.carousel {
  padding: 0.6rem;
  flex: 1 1 auto;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  overflow-y: auto;
}
.carousel-stage {
  position: relative;
  background: var(--bg-surface);
  border-radius: var(--radius-sm);
  overflow: hidden;
  flex: 1 1 auto;
  min-height: 240px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.carousel-img-wrap {
  display: block;
  width: 100%;
  height: 100%;
}
.carousel-img-wrap img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  display: block;
}
.video-stage {
  background: #000;
}
.video-player {
  width: 100%;
  height: 100%;
  object-fit: contain;
  display: block;
}
.video-fallback-note {
  padding: 0.55rem 0.85rem;
  font-size: 0.78rem;
  color: var(--bad);
  background: var(--bad-glow);
  border: 1px solid var(--bad);
  border-radius: var(--radius-sm);
  margin: 0.6rem;
  text-align: center;
}
.video-fallback-note a { font-weight: 700; }
.carousel-arrow {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: none;
  background: rgba(0,0,0,0.55);
  color: #fff;
  font-size: 22px;
  line-height: 1;
  cursor: pointer;
  z-index: 2;
  display: flex;
  align-items: center;
  justify-content: center;
}
.carousel-arrow.left  { left: 0.5rem; }
.carousel-arrow.right { right: 0.5rem; }
.carousel-arrow:hover:not(:disabled) { background: rgba(0,0,0,0.75); }
.carousel-arrow:disabled { opacity: 0.3; cursor: default; }

.carousel-dots {
  display: flex;
  justify-content: center;
  gap: 0.3rem;
  margin-top: 0.5rem;
}
.carousel-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  border: none;
  background: var(--border-default, #d4d4d4);
  cursor: pointer;
  padding: 0;
}
.carousel-dot.active { background: var(--accent, #b45309); }

.comment-scroll { flex: 1 1 auto; min-height: 0; overflow-y: auto; }
.comment-item { padding: 0.6rem 1rem; border-bottom: 1px solid var(--border-subtle); }
.comment-user { font-size: 0.786rem; font-weight: 500; color: var(--accent); }
.comment-content { font-size: 0.857rem; margin: 0.3rem 0; line-height: 1.5; }
.comment-footer { font-size: 0.714rem; color: var(--text-secondary); display: flex; gap: 0.75rem; }

.comment-pics {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  margin: 0.35rem 0;
}
.comment-pic-cell {
  display: block;
  width: 80px;
  height: 80px;
  border-radius: var(--radius-sm);
  overflow: hidden;
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  transition: transform var(--transition-fast);
}
.comment-pic-cell:hover { transform: scale(1.03); border-color: var(--accent); }
.comment-pic-cell img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.fav-btn {
  background: transparent;
  border: none;
  cursor: pointer;
  font-size: 1.05rem;
  line-height: 1;
  color: var(--plum-3);
  padding: 0 0.15rem;
  transition: transform var(--transition-fast), color var(--transition-fast);
}
.fav-btn:hover { color: var(--sakura); transform: scale(1.15); }
.fav-btn.on {
  color: var(--sakura);
  text-shadow: 0 0 8px var(--sakura-glow);
  animation: fav-pop 0.4s ease-out;
}
@keyframes fav-pop {
  0%   { transform: scale(0.8); }
  60%  { transform: scale(1.35); }
  100% { transform: scale(1); }
}

.comment-category {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  margin: 0.35rem 0 0;
}
.cat-input {
  flex: 1;
  border: 1.5px solid var(--sakura-light);
  background: #fff;
  border-radius: var(--radius-pill);
  font-size: 0.74rem;
  padding: 0.2rem 0.65rem;
  font-family: var(--font-body);
  color: var(--plum-1);
  outline: none;
  transition: border-color var(--transition-fast), box-shadow var(--transition-fast);
}
.cat-input:focus {
  border-color: var(--sakura);
  box-shadow: 0 0 0 3px var(--sakura-ring);
}
.cat-tag {
  font-family: var(--font-mono);
  font-size: 0.7rem;
  color: var(--sakura-deep);
  background: var(--sakura-glow);
  border: 1px solid var(--sakura-light);
  padding: 0.1rem 0.5rem;
  border-radius: var(--radius-pill);
  white-space: nowrap;
}
</style>
