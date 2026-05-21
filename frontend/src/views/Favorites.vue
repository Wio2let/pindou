<template>
  <div>
    <div class="fav-layout">
      <!-- Sidebar: category list -->
      <aside class="fav-sidebar card">
        <div class="sidebar-head">
          <span class="display-md">分类</span>
          <button class="btn btn-ghost btn-xs" @click="reload" :disabled="loadingCats">
            刷新
          </button>
        </div>

        <div v-if="loadingCats" style="padding:0.5rem;">
          <div v-for="i in 4" :key="i" class="skeleton" style="height:2.2rem; margin-bottom:0.5rem;"></div>
        </div>

        <div v-else class="cat-list">
          <button class="cat-row" :class="{ active: selectedCat === '' }" @click="setCat('')">
            <span class="cat-name">🌸 全部</span>
            <span class="cat-count mono tabular">{{ totalCount }}</span>
          </button>
          <button class="cat-row" :class="{ active: selectedCat === 'uncategorized' }"
                  @click="setCat('uncategorized')">
            <span class="cat-name">📦 未分类</span>
            <span class="cat-count mono tabular">{{ uncategorizedCount }}</span>
          </button>
          <div v-if="categories.length" class="cat-divider"></div>
          <button v-for="cat in categories" :key="cat.category"
                  class="cat-row"
                  :class="{ active: selectedCat === cat.category }"
                  @click="setCat(cat.category)">
            <span class="cat-name">#{{ cat.category }}</span>
            <span class="cat-count mono tabular">{{ cat.count }}</span>
          </button>
          <div v-if="categories.length === 0 && uncategorizedCount === 0" class="empty-state" style="padding:1.5rem 0.5rem;">
            <div class="empty-icon">♡</div>
            <div class="empty-text">还没有收藏的评论<br><span class="text-xs">在任务详情页给评论点 ♡ 即可</span></div>
          </div>
        </div>
      </aside>

      <!-- Main: comments list -->
      <section class="fav-main">
        <div class="fav-head card">
          <div class="flex items-center justify-between" style="padding:0.6rem 1rem; flex-wrap:wrap; gap:0.5rem;">
            <span class="text-sm" style="font-weight:600;">
              {{ titleLabel }} ({{ comments.length }})
            </span>
            <div class="flex items-center gap-2">
              <span class="text-xs text-muted">排序</span>
              <select class="select" v-model="sortBy" @change="loadList" style="width:auto; padding:0.25rem 0.55rem; font-size:0.78rem;">
                <option value="recent">最新</option>
                <option value="score">实用度</option>
                <option value="likes">点赞数</option>
              </select>
            </div>
          </div>
        </div>

        <div v-if="loadingList" style="margin-top:1rem;">
          <div v-for="i in 5" :key="i" class="skeleton" style="height:5rem; margin-bottom:0.5rem;"></div>
        </div>

        <div v-else-if="comments.length === 0" class="empty-state" style="margin-top:2rem;">
          <div class="empty-icon">♡</div>
          <div class="empty-text">此分类还没有收藏</div>
        </div>

        <div v-else class="fav-list">
          <div v-for="c in comments" :key="c.id" class="fav-card card">
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <span class="comment-user">{{ c.user_name }}</span>
                <span v-if="c.category" class="cat-tag-static">#{{ c.category }}</span>
                <span class="badge" :class="usefulnessBadge(c.usefulness_label)">{{ c.usefulness_label }}</span>
              </div>
              <button class="fav-btn on" @click="unfavorite(c)" title="取消收藏">♥</button>
            </div>
            <div class="comment-content">{{ c.content }}</div>
            <div v-if="commentImages(c).length" class="comment-pics">
              <a v-for="(u, i) in commentImages(c)" :key="i"
                 :href="u" target="_blank" rel="noopener" class="comment-pic-cell">
                <img :src="u" loading="lazy" referrerpolicy="no-referrer" @error="onImgError" />
              </a>
            </div>
            <div class="comment-meta">
              <span>♥ {{ c.liked_count }}</span>
              <span v-if="c.ip_location">{{ c.ip_location }}</span>
              <router-link :to="`/tasks/${c.task_id}`" class="text-xs text-muted">→ 任务 #{{ c.task_id }}</router-link>
              <span class="text-xs text-muted">·</span>
              <input class="cat-input"
                     :value="c.category"
                     placeholder="改分类 (回车保存)"
                     :list="`fav-cats-${c.id}`"
                     @keyup.enter="(e: any) => saveCategory(c, e.target.value)"
                     @blur="(e: any) => saveCategory(c, e.target.value)" />
              <datalist :id="`fav-cats-${c.id}`">
                <option v-for="cat in categoryNames" :key="cat" :value="cat" />
              </datalist>
            </div>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useComments, type Comment } from '../composables/useComments'

const { listFavorites, listCategories, update: updateComment } = useComments()

const loadingCats = ref(false)
const loadingList = ref(false)
const totalCount = ref(0)
const uncategorizedCount = ref(0)
const categories = ref<{ category: string; count: number }[]>([])
const categoryNames = computed(() => categories.value.map(c => c.category))

const comments = ref<Comment[]>([])
const selectedCat = ref<string>('')  // '' = all, 'uncategorized' = blank, other = named
const sortBy = ref<'recent' | 'score' | 'likes'>('recent')

const titleLabel = computed(() => {
  if (selectedCat.value === '') return '全部收藏'
  if (selectedCat.value === 'uncategorized') return '未分类'
  return `# ${selectedCat.value}`
})

function usefulnessBadge(l: string) {
  const m: Record<string, string> = { high: 'badge-success', medium: 'badge-warning', low: 'badge-neutral' }
  return m[l] || 'badge-neutral'
}

function commentImages(c: Comment): string[] {
  if (!c?.pictures) return []
  try {
    const arr = JSON.parse(c.pictures)
    return Array.isArray(arr) ? arr.filter((u: any) => typeof u === 'string' && u.startsWith('http')) : []
  } catch { return [] }
}
function onImgError(e: Event) {
  const el = e.target as HTMLImageElement
  el.style.visibility = 'hidden'
}

async function reload() {
  await Promise.all([loadCats(), loadList()])
}

async function loadCats() {
  loadingCats.value = true
  try {
    const r = await listCategories()
    totalCount.value = r.total
    uncategorizedCount.value = r.uncategorized
    categories.value = r.categories
  } catch { /* ignore */ }
  finally { loadingCats.value = false }
}

async function loadList() {
  loadingList.value = true
  try {
    const params: any = { sort: sortBy.value, per_page: 200 }
    if (selectedCat.value) params.category = selectedCat.value
    comments.value = await listFavorites(params)
  } catch { comments.value = [] }
  finally { loadingList.value = false }
}

function setCat(cat: string) {
  selectedCat.value = cat
  loadList()
}

async function unfavorite(c: Comment) {
  try {
    await updateComment(c.id, { favorite: false })
    comments.value = comments.value.filter(x => x.id !== c.id)
    ElMessage.info('已取消收藏')
    loadCats()
  } catch { ElMessage.error('取消失败') }
}

async function saveCategory(c: Comment, raw: string) {
  const next = (raw || '').trim()
  if (next === c.category) return
  try {
    const updated = await updateComment(c.id, { category: next })
    Object.assign(c, updated)
    loadCats()
    // If we were filtering by a specific named category and the new one doesn't match, drop from list
    if (selectedCat.value && selectedCat.value !== 'uncategorized' &&
        selectedCat.value !== updated.category) {
      comments.value = comments.value.filter(x => x.id !== c.id)
    }
    if (selectedCat.value === 'uncategorized' && updated.category) {
      comments.value = comments.value.filter(x => x.id !== c.id)
    }
  } catch { ElMessage.error('保存失败') }
}

onMounted(() => { reload() })
</script>

<style scoped>
.fav-layout {
  display: grid;
  grid-template-columns: 260px 1fr;
  gap: 1.25rem;
  align-items: start;
}
@media (max-width: 900px) { .fav-layout { grid-template-columns: 1fr; } }

.fav-sidebar { padding: 0; overflow: hidden; position: sticky; top: 1rem; }
.sidebar-head {
  padding: 0.85rem 1rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px dashed var(--line-strong);
}
.cat-list { padding: 0.4rem; display: flex; flex-direction: column; gap: 0.2rem; }
.cat-divider { height: 1px; background: var(--line); margin: 0.4rem 0.4rem; }
.cat-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.55rem 0.7rem;
  background: transparent;
  border: 2px solid transparent;
  border-radius: var(--radius-md);
  cursor: pointer;
  font-family: var(--font-round);
  font-weight: 600;
  font-size: 0.84rem;
  color: var(--plum-2);
  transition: all var(--transition-fast);
  text-align: left;
}
.cat-row:hover { background: var(--cream-2); color: var(--plum-1); }
.cat-row.active {
  background: linear-gradient(135deg, #ffe6ef, #fff0f5);
  border-color: var(--sakura);
  color: var(--sakura-deep);
}
.cat-count {
  font-size: 0.72rem;
  color: var(--plum-3);
  background: var(--cream-2);
  padding: 0.05rem 0.5rem;
  border-radius: var(--radius-pill);
}
.cat-row.active .cat-count {
  background: var(--sakura);
  color: #fff;
}

.fav-main { min-width: 0; }
.fav-head { margin-bottom: 0.6rem; padding: 0; }
.fav-list { display: flex; flex-direction: column; gap: 0.6rem; }
.fav-card { padding: 0.8rem 1rem; }

.comment-user { font-size: 0.86rem; font-weight: 600; color: var(--sakura-deep); }
.comment-content { font-size: 0.9rem; margin: 0.4rem 0; line-height: 1.55; color: var(--plum-1); }
.comment-pics { display: flex; flex-wrap: wrap; gap: 0.35rem; margin: 0.35rem 0; }
.comment-pic-cell {
  display: block;
  width: 80px;
  height: 80px;
  border-radius: var(--radius-sm);
  overflow: hidden;
  border: 1px solid var(--line-strong);
}
.comment-pic-cell img { width: 100%; height: 100%; object-fit: cover; }
.comment-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.55rem;
  margin-top: 0.4rem;
  font-size: 0.74rem;
  color: var(--plum-2);
}
.fav-btn {
  background: transparent;
  border: none;
  cursor: pointer;
  font-size: 1.1rem;
  color: var(--sakura);
  text-shadow: 0 0 8px var(--sakura-glow);
  padding: 0 0.15rem;
}
.fav-btn:hover { transform: scale(1.15); }

.cat-tag-static {
  font-family: var(--font-mono);
  font-size: 0.7rem;
  color: var(--sakura-deep);
  background: var(--sakura-glow);
  border: 1px solid var(--sakura-light);
  padding: 0.1rem 0.5rem;
  border-radius: var(--radius-pill);
}
.cat-input {
  flex: 0 0 auto;
  min-width: 130px;
  border: 1.5px solid var(--cream-4);
  background: #fff;
  border-radius: var(--radius-pill);
  font-size: 0.72rem;
  padding: 0.18rem 0.65rem;
  font-family: var(--font-body);
  color: var(--plum-1);
  outline: none;
  margin-left: auto;
}
.cat-input:focus { border-color: var(--sakura); box-shadow: 0 0 0 3px var(--sakura-ring); }
</style>
