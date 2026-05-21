import { ref } from 'vue'
import { useApi } from './useApi'

export interface Post {
  note_id: string
  task_id: number
  title: string
  desc: string
  type: string
  author_name: string
  author_id: string
  liked_count: number
  collected_count: number
  comment_count: number
  share_count: number
  image_urls: string
  video_url: string | null
  xsec_token: string
  xsec_source: string
  url: string
  crawled_at: string
  created_at: string
}

export interface PostDetail extends Post {
  useful_comment_count: number
  avg_usefulness: number
}

export function usePosts() {
  const api = useApi()

  async function list(taskId: number, params?: any): Promise<Post[]> {
    const res = await api.get(`/tasks/${taskId}/posts`, { params })
    return res.data
  }

  async function getDetail(noteId: string): Promise<PostDetail> {
    const res = await api.get(`/posts/${noteId}`)
    return res.data
  }

  async function remove(noteId: string): Promise<void> {
    await api.delete(`/posts/${noteId}`)
  }

  async function bulkRemove(taskId: number, noteIds: string[]): Promise<number> {
    const res = await api.post(`/tasks/${taskId}/posts/bulk-delete`, {
      note_ids: noteIds,
    })
    return res.data?.deleted ?? 0
  }

  async function refreshImages(noteId: string): Promise<string[]> {
    const res = await api.post(`/posts/${noteId}/refresh-images`)
    return res.data?.images || []
  }

  async function refreshAll(noteId: string, maxComments = 50): Promise<{
    images: string[]
    image_count: number
    comments_fetched: number
    comments_saved: number
  }> {
    const res = await api.post(`/posts/${noteId}/refresh-all`, null, {
      params: { max_comments: maxComments },
    })
    return res.data
  }

  async function refreshAllPosts(taskId: number, limit = 200): Promise<{
    total: number
    needed_refresh: number
    processed: number
    images_added: number
    comments_added: number
    failed: number
    skipped_no_token: number
  }> {
    const res = await api.post(`/tasks/${taskId}/refresh-all-posts`, null, {
      params: { limit },
      timeout: 20 * 60 * 1000,  // 20 min for large tasks
    })
    return res.data
  }

  return { list, getDetail, remove, bulkRemove, refreshImages, refreshAll, refreshAllPosts }
}
