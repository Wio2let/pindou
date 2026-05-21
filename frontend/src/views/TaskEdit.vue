<template>
  <div style="max-width:640px;">
    <div class="card" style="padding:1.5rem;">
      <div style="font-size:0.857rem; font-weight:600; margin-bottom:1.5rem;">编辑任务</div>

      <div v-if="loading" style="padding:1rem 0;">
        <div class="skeleton" style="height:2.5rem; margin-bottom:0.75rem;"></div>
        <div class="skeleton" style="height:2.5rem; margin-bottom:0.75rem;"></div>
        <div class="skeleton" style="height:2.5rem;"></div>
      </div>

      <div v-else style="display:flex; flex-direction:column; gap:1.25rem;">
        <div class="form-row">
          <label>任务名称</label>
          <input class="input" v-model="form.name" placeholder="例如：美妆测评" />
        </div>
        <div class="form-row">
          <label>搜索关键词</label>
          <input class="input" v-model="form.keywords" placeholder="多个用逗号分隔" />
          <span class="form-hint">例如：精华液,面霜,防晒</span>
        </div>
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:1rem;">
          <div class="form-row">
            <label>排序</label>
            <select class="select" v-model="form.search_sort">
              <option value="general">综合</option>
              <option value="popularity_descending">最热</option>
              <option value="time_descending">最新</option>
            </select>
          </div>
          <div class="form-row">
            <label>类型</label>
            <select class="select" v-model.number="form.note_type">
              <option :value="0">全部</option>
              <option :value="1">视频</option>
              <option :value="2">图文</option>
            </select>
          </div>
        </div>

        <div style="border-top:1px solid var(--border-subtle); padding-top:1rem;">
          <div class="form-row">
            <label style="font-weight:600; color:var(--text-primary);">采集设置</label>
          </div>
          <div style="display:grid; grid-template-columns:1fr 1fr; gap:1rem; margin-top:0.75rem;">
            <div class="form-row">
              <label>轮询间隔（分）</label>
              <input class="input" type="number" v-model.number="form.interval_minutes" min="5" max="1440" />
            </div>
            <div class="form-row">
              <label>每次最多帖子</label>
              <input class="input" type="number" v-model.number="form.max_posts_per_run" min="1" max="100" />
            </div>
          </div>
          <div class="form-row" style="margin-top:0.75rem;">
            <label>每个帖子最多评论数</label>
            <input class="input" type="number" v-model.number="form.max_comments_per_post" min="0" max="500" />
          </div>
          <div class="form-row" style="margin-top:0.75rem;">
            <label>最小帖子点赞数 (低于此值的帖子跳过不打开)</label>
            <input class="input" type="number" v-model.number="form.min_post_likes" min="0" />
          </div>
          <div class="form-row" style="margin-top:0.75rem;">
            <label>发布时间</label>
            <select class="select" v-model.number="form.publish_time_type">
              <option :value="0">不限</option>
              <option :value="1">24 小时内</option>
              <option :value="2">7 天内</option>
              <option :value="3">30 天内</option>
              <option :value="4">半年内</option>
            </select>
            <span class="form-hint">只爬取在此时间窗内发布的图文/视频</span>
          </div>
        </div>

        <div style="border-top:1px solid var(--border-subtle); padding-top:1rem;">
          <div class="form-row">
            <label style="font-weight:600; color:var(--text-primary);">评论过滤</label>
          </div>
          <div style="display:grid; grid-template-columns:1fr 1fr; gap:1rem; margin-top:0.75rem;">
            <div class="form-row">
              <label>评论关键词</label>
              <input class="input" v-model="form.comment_keywords" placeholder="多个用逗号分隔" />
            </div>
            <div class="form-row">
              <label>最小点赞</label>
              <input class="input" type="number" v-model.number="form.min_comment_likes" min="0" />
            </div>
          </div>
        </div>

        <div style="border-top:1px solid var(--border-subtle); padding-top:1rem;">
          <label class="flex items-center gap-2" style="cursor:pointer;">
            <input type="checkbox" v-model="form.enabled" />
            <span>启用此任务（自动按间隔运行）</span>
          </label>
        </div>

        <div class="flex gap-2" style="padding-top:0.5rem;">
          <button class="btn btn-primary" @click="handleSave" :disabled="saving">
            {{ saving ? '保存中...' : '保存修改' }}
          </button>
          <button class="btn btn-ghost" @click="$router.back()">取消</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useTasks } from '../composables/useTasks'

const props = defineProps<{ id?: string }>()
const route = useRoute()
const router = useRouter()
const taskId = computed(() => Number(props.id || route.params.id))
const { get, update } = useTasks()

const loading = ref(true)
const saving = ref(false)
const form = reactive({
  name: '',
  keywords: '',
  search_sort: 'general',
  note_type: 0,
  interval_minutes: 30,
  max_posts_per_run: 20,
  max_comments_per_post: 50,
  min_post_likes: 0,
  publish_time_type: 0,
  comment_keywords: '',
  min_comment_likes: 1,
  enabled: true,
})

async function load() {
  loading.value = true
  try {
    const t = await get(taskId.value)
    form.name = t.name
    form.keywords = t.keywords
    form.search_sort = t.search_sort
    form.note_type = t.note_type
    form.interval_minutes = t.interval_minutes
    form.max_posts_per_run = t.max_posts_per_run
    form.max_comments_per_post = t.max_comments_per_post
    form.min_post_likes = (t as any).min_post_likes ?? 0
    form.publish_time_type = (t as any).publish_time_type ?? 0
    form.comment_keywords = t.comment_keywords || ''
    form.min_comment_likes = t.min_comment_likes
    form.enabled = t.enabled
  } catch (e: any) {
    ElMessage.error('任务不存在')
    router.push('/tasks')
  } finally {
    loading.value = false
  }
}

async function handleSave() {
  if (!form.name?.trim() || !form.keywords?.trim()) {
    ElMessage.warning('名称和关键词必填')
    return
  }
  saving.value = true
  try {
    await update(taskId.value, { ...form })
    ElMessage.success('已保存')
    router.push(`/tasks/${taskId.value}`)
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>
