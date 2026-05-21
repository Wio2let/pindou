<template>
  <div class="card" style="overflow:hidden;">
    <div class="flex items-center justify-between" style="padding:0.85rem 1.25rem; border-bottom:1px solid var(--border-subtle);">
      <span style="font-size:0.857rem; font-weight:600;">所有任务</span>
      <router-link to="/tasks/create" class="btn btn-primary btn-sm">+ 新建</router-link>
    </div>

    <div v-if="loading" style="padding:1.25rem;">
      <div v-for="i in 4" :key="i" class="skeleton" style="height:2.5rem; margin-bottom:0.5rem;"></div>
    </div>
    <div v-else-if="tasks.length === 0" class="empty-state">
      <div class="empty-icon">◈</div>
      <div class="empty-text">还没有任务</div>
    </div>
    <div v-else class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>名称</th>
            <th>关键词</th>
            <th>状态</th>
            <th>间隔</th>
            <th>上次运行</th>
            <th style="text-align:right;">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="t in tasks" :key="t.id">
            <td style="font-weight:500;">{{ t.name }}</td>
            <td><span v-for="kw in t.keywords.split(',')" :key="kw" class="tag" style="margin-right:4px;">{{ kw.trim() }}</span></td>
            <td><span class="badge" :class="statusBadge(t.status)">{{ statusLabel(t.status) }}</span></td>
            <td class="text-sm text-muted">{{ t.interval_minutes }}分</td>
            <td class="text-sm text-muted">{{ t.last_run_at ? fmt(t.last_run_at) : '从未' }}</td>
            <td style="text-align:right;">
              <router-link :to="`/tasks/${t.id}`" class="btn btn-ghost btn-xs">详情</router-link>
              <router-link :to="`/tasks/${t.id}/edit`" class="btn btn-ghost btn-xs">编辑</router-link>
              <button class="btn btn-ghost btn-xs" @click="handleRun(t)">运行</button>
              <button class="btn btn-danger btn-xs" @click="handleDelete(t)">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useTasks, type Task } from '../composables/useTasks'
import { ElMessage } from 'element-plus'

const { list, remove, run } = useTasks()
const loading = ref(false)
const tasks = ref<Task[]>([])

function statusBadge(s: string) { const m: Record<string,string>={idle:'badge-neutral',running:'badge-warning',error:'badge-danger'}; return m[s]||'badge-neutral' }
function statusLabel(s: string) { const m: Record<string,string>={idle:'空闲',running:'运行中',error:'错误'}; return m[s]||s }
function fmt(t: string) { return new Date(t).toLocaleString('zh-CN') }

async function load() { loading.value=true; try { tasks.value=await list() } catch { ElMessage.error('加载失败') } finally { loading.value=false } }
async function handleRun(t: Task) { try { await run(t.id); ElMessage.success('已启动') } catch { ElMessage.error('启动失败') } }
async function handleDelete(t: Task) { try { await remove(t.id); tasks.value=tasks.value.filter(x=>x.id!==t.id); ElMessage.success('已删除') } catch { ElMessage.error('删除失败') } }
onMounted(load)
</script>
