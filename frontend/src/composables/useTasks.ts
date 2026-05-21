import { ref } from 'vue'
import { useApi } from './useApi'

export interface Task {
  id: number
  name: string
  keywords: string
  search_sort: string
  note_type: number
  interval_minutes: number
  max_posts_per_run: number
  max_comments_per_post: number
  min_post_likes: number
  publish_time_type: number
  comment_keywords: string
  min_comment_likes: number
  enabled: boolean
  status: string
  last_run_at: string | null
  next_run_at: string | null
  created_at: string
  updated_at: string
}

export interface TaskStats {
  task_id: number
  task_name: string
  total_posts: number
  total_comments: number
  useful_comments: number
  last_run_status: string
  last_run_time: string | null
  is_enabled: boolean
}

export function useTasks() {
  const api = useApi()
  const loading = ref(false)

  async function list(): Promise<Task[]> {
    loading.value = true
    try {
      const res = await api.get('/tasks')
      return res.data
    } finally {
      loading.value = false
    }
  }

  async function get(id: number): Promise<Task> {
    const res = await api.get(`/tasks/${id}`)
    return res.data
  }

  async function create(data: Partial<Task>): Promise<Task> {
    const res = await api.post('/tasks', data)
    return res.data
  }

  async function update(id: number, data: Partial<Task>): Promise<Task> {
    const res = await api.patch(`/tasks/${id}`, data)
    return res.data
  }

  async function remove(id: number): Promise<void> {
    await api.delete(`/tasks/${id}`)
  }

  async function run(id: number): Promise<void> {
    await api.post(`/tasks/${id}/run`)
  }

  async function stopTask(id: number): Promise<void> {
    await api.post(`/tasks/${id}/stop`)
  }

  async function getStats(): Promise<TaskStats[]> {
    const res = await api.get('/tasks/stats/summary')
    return res.data
  }

  async function getStatus(id: number) {
    const res = await api.get(`/tasks/${id}/status`)
    return res.data
  }

  return { loading, list, get, create, update, remove, run, stopTask, getStats, getStatus }
}
