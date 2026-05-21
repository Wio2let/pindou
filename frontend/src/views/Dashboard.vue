<template>
  <div>
    <div class="grid-4">
      <div v-for="(s, i) in stats" :key="s.label" class="card stat-card">
        <div class="stat-num-wrap">
          <span class="stat-index mono">{{ String(i + 1).padStart(2, '0') }}</span>
          <span class="stat-num tabular">{{ s.value }}</span>
        </div>
        <div class="stat-rule"></div>
        <div class="stat-label">{{ s.label }}</div>
        <div v-if="s.sub" class="stat-sub mono">{{ s.sub }}</div>
      </div>
    </div>

    <div class="card" style="margin-top:1.25rem; overflow:hidden;">
      <div class="flex items-center justify-between" style="padding:0.85rem 1.25rem; border-bottom:1px solid var(--border-subtle);">
        <span style="font-size:0.857rem; font-weight:600;">监控任务</span>
        <router-link to="/tasks/create" class="btn btn-primary btn-sm">+ 新建</router-link>
      </div>

      <div v-if="loading" style="padding:1.25rem;">
        <div v-for="i in 3" :key="i" class="skeleton" style="height:2.5rem; margin-bottom:0.5rem;"></div>
      </div>
      <div v-else-if="taskStats.length === 0" class="empty-state">
        <div class="empty-icon">◈</div>
        <div class="empty-text">还没有监控任务</div>
        <router-link to="/tasks/create" class="btn btn-primary btn-sm" style="margin-top:0.75rem;">创建第一个任务</router-link>
      </div>
      <div v-else class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>任务</th>
              <th>状态</th>
              <th style="text-align:right;">帖子</th>
              <th style="text-align:right;">评论</th>
              <th style="text-align:right;">实用</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="t in taskStats" :key="t.task_id">
              <td style="font-weight:500;">{{ t.task_name }}</td>
              <td><span class="badge" :class="statusBadge(t.last_run_status)">{{ statusLabel(t.last_run_status) }}</span></td>
              <td style="text-align:right; font-family:var(--font-mono);">{{ t.total_posts }}</td>
              <td style="text-align:right; font-family:var(--font-mono);">{{ t.total_comments }}</td>
              <td style="text-align:right;"><span class="badge badge-warning" v-if="t.useful_comments > 0">{{ t.useful_comments }}</span><span v-else class="text-muted text-sm">0</span></td>
              <td style="text-align:right;">
                <router-link :to="`/tasks/${t.task_id}`" class="btn btn-ghost btn-xs">详情</router-link>
                <router-link :to="`/tasks/${t.task_id}/search`" class="btn btn-ghost btn-xs">搜索</router-link>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div class="card" style="margin-top:1rem; padding:1rem 1.25rem;">
      <div class="flex items-center justify-between">
        <span class="text-sm text-muted">小红书</span>
        <span class="badge" :class="loginStatus ? 'badge-success' : 'badge-neutral'">{{ loginStatus ? '已登录' : '未登录' }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useApi } from '../composables/useApi'
import { useTasks, type TaskStats } from '../composables/useTasks'

const api = useApi()
const { getStats } = useTasks()
const loading = ref(false)
const taskStats = ref<TaskStats[]>([])
const loginStatus = ref(false)
const stats = ref([
  { label: '活跃任务', value: 0, sub: '' },
  { label: '帖子数', value: 0, sub: '' },
  { label: '评论数', value: 0, sub: '' },
  { label: '实用评论', value: 0, sub: '评分 ≥ 0.4' },
])

function statusBadge(s: string) { const m: Record<string,string> = { idle:'badge-neutral', running:'badge-warning', error:'badge-danger' }; return m[s]||'badge-neutral' }
function statusLabel(s: string) { const m: Record<string,string> = { idle:'空闲', running:'运行中', error:'错误' }; return m[s]||s }

onMounted(async () => {
  loading.value = true
  try {
    const [o, tasks, lr] = await Promise.all([api.get('/stats/overview'), getStats(), api.get('/system/login-status')])
    stats.value = [
      { label:'活跃任务 · ACTIVE TASKS', value: o.data.active_tasks, sub:'' },
      { label:'帖子数 · POSTS', value: o.data.total_posts, sub:`今日 +${o.data.posts_today}` },
      { label:'评论数 · COMMENTS', value: o.data.total_comments, sub:`今日 +${o.data.comments_today}` },
      { label:'实用评论 · USEFUL', value: o.data.total_useful_comments, sub:'评分 ≥ 0.4' },
    ]
    taskStats.value = tasks
    loginStatus.value = lr.data.logged_in
  } catch(e) { console.error(e) }
  finally { loading.value = false }
})
</script>

<style scoped>
.stat-card {
  padding: 1.4rem 1.25rem 1.1rem;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  position: relative;
  overflow: hidden;
}
.stat-card::before {
  /* candy stripe on the top */
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 4px;
  background: linear-gradient(90deg, var(--sakura), var(--peach), var(--honey), var(--mint), var(--lavender));
  border-radius: var(--radius-lg) var(--radius-lg) 0 0;
}
.stat-card::after {
  content: '✦';
  position: absolute;
  top: 12px;
  right: 12px;
  color: var(--sakura-light);
  font-size: 14px;
  transition: transform var(--transition-base);
}
.stat-card:hover::after { transform: rotate(180deg) scale(1.4); color: var(--sakura); }

.stat-num-wrap {
  display: flex;
  align-items: baseline;
  gap: 0.5rem;
}
.stat-index {
  font-size: 0.7rem;
  font-weight: 700;
  color: var(--sakura);
  background: var(--sakura-glow);
  padding: 0.1rem 0.5rem;
  border-radius: var(--radius-pill);
  letter-spacing: 0.05em;
}
.stat-num {
  font-family: var(--font-display);
  font-size: 2.6rem;
  line-height: 1;
  color: var(--plum-1);
  letter-spacing: 0.02em;
  text-shadow: 0 2px 0 var(--sakura-light);
}
.stat-rule {
  display: none;
}
.stat-label {
  font-family: var(--font-round);
  font-weight: 700;
  font-size: 0.78rem;
  color: var(--plum-2);
  margin-top: 0.35rem;
  letter-spacing: 0.02em;
}
.stat-sub {
  font-size: 0.74rem;
  font-weight: 600;
  color: var(--ok);
  background: var(--ok-glow);
  padding: 0.1rem 0.55rem;
  border-radius: var(--radius-pill);
  align-self: flex-start;
  margin-top: 0.2rem;
}
</style>
