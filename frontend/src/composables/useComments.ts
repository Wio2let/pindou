import { useApi } from './useApi'

export interface Comment {
  id: number
  comment_id: string
  note_id: string
  task_id: number
  content: string
  user_name: string
  liked_count: number
  sub_comment_count: number
  ip_location: string | null
  pictures: string
  favorite: boolean
  category: string
  usefulness_score: number
  usefulness_label: string
  matched_keywords: string
  is_actionable: boolean
  created_at: string
}

export interface CommentSearchResult {
  items: Comment[]
  total: number
  page: number
  per_page: number
  total_pages: number
}

export function useComments() {
  const api = useApi()

  async function listByPost(noteId: string, params?: any): Promise<Comment[]> {
    const res = await api.get(`/posts/${noteId}/comments`, { params })
    return res.data
  }

  async function search(taskId: number, params: {
    q?: string
    min_score?: number
    min_likes?: number
    sort?: string
    actionable_only?: boolean
    page?: number
    per_page?: number
  }): Promise<CommentSearchResult> {
    const res = await api.get(`/tasks/${taskId}/comments/search`, { params })
    return res.data
  }

  async function refresh(noteId: string, maxCount = 50): Promise<{ fetched: number, saved: number }> {
    const res = await api.post(`/posts/${noteId}/refresh-comments`, null, {
      params: { max_count: maxCount },
    })
    return res.data
  }

  async function update(id: number, data: { favorite?: boolean; category?: string }): Promise<Comment> {
    const res = await api.patch(`/comments/${id}`, data)
    return res.data
  }

  async function listFavorites(params?: {
    category?: string
    task_id?: number
    sort?: 'recent' | 'score' | 'likes'
    page?: number
    per_page?: number
  }): Promise<Comment[]> {
    const res = await api.get('/comments/favorites', { params })
    return res.data
  }

  async function listCategories(taskId?: number): Promise<{
    total: number
    uncategorized: number
    categories: { category: string; count: number }[]
  }> {
    const res = await api.get('/comments/categories', {
      params: taskId != null ? { task_id: taskId } : undefined,
    })
    return res.data
  }

  return { listByPost, search, refresh, update, listFavorites, listCategories }
}
