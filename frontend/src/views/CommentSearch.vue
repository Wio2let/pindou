<template>
  <div class="card" style="padding:0;">
    <div class="flex items-center justify-between" style="padding:0.85rem 1.25rem; border-bottom:1px solid var(--border-subtle);">
      <span style="font-size:0.857rem; font-weight:600;">评论搜索 <span class="text-muted" style="font-weight:400;">#{{ taskId }}</span></span>
      <router-link :to="`/tasks/${taskId}`" class="btn btn-ghost btn-sm">返回</router-link>
    </div>

    <!-- Search -->
    <div style="padding:0.85rem 1.25rem; border-bottom:1px solid var(--border-subtle);">
      <div class="flex gap-2 items-center" style="flex-wrap:wrap;">
        <div class="form-row" style="flex:2; min-width:160px;">
          <label>关键词</label>
          <input class="input" v-model="filters.q" placeholder="搜索评论" @keyup.enter="handleSearch" />
        </div>
        <div class="form-row" style="width:90px;">
          <label>最低分</label>
          <input class="input" type="number" v-model.number="filters.min_score" step="0.1" min="0" max="1" />
        </div>
        <div class="form-row" style="width:80px;">
          <label>点赞</label>
          <input class="input" type="number" v-model.number="filters.min_likes" min="0" />
        </div>
        <label class="flex items-center gap-1" style="padding-bottom:0.2rem; cursor:pointer;">
          <input type="checkbox" v-model="filters.actionable_only" style="accent-color:var(--accent);" />
          <span class="text-sm text-muted">仅实用</span>
        </label>
        <button class="btn btn-primary btn-sm" @click="handleSearch" :disabled="searching">搜索</button>
        <button class="btn btn-ghost btn-sm" @click="reset">重置</button>
      </div>
    </div>

    <!-- Info -->
    <div class="flex items-center justify-between" style="padding:0.45rem 1.25rem; border-bottom:1px solid var(--border-subtle);">
      <span class="text-xs text-muted">{{ result.total }} 条结果</span>
      <select class="select" v-model="filters.sort" style="width:auto; padding:0.2rem 0.45rem; font-size:0.786rem;" @change="handleSearch">
        <option value="score">按评分</option><option value="likes">按点赞</option><option value="date">按时间</option>
      </select>
    </div>

    <!-- Results -->
    <div v-if="searching" style="padding:1.25rem;">
      <div v-for="i in 4" :key="i" class="skeleton" style="height:70px; margin-bottom:0.5rem;"></div>
    </div>
    <div v-else-if="result.items.length===0" class="empty-state">
      <div class="empty-icon">◈</div>
      <div class="empty-text">未找到匹配的评论</div>
    </div>
    <div v-else style="padding:0.75rem 1.25rem;">
      <div v-for="c in result.items" :key="c.id" class="result-item">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <span class="comment-user">{{ c.user_name }}</span>
            <span v-if="c.ip_location" class="text-xs text-muted">{{ c.ip_location }}</span>
          </div>
          <div class="flex items-center gap-2">
            <span class="badge" :class="usefulnessBadge(c.usefulness_label)">{{ c.usefulness_score.toFixed(2) }}</span>
            <span v-if="c.is_actionable" class="badge badge-warning" style="font-size:0.6rem;">实用</span>
          </div>
        </div>
        <div class="comment-content">
          <span v-if="filters.q" v-html="highlight(c.content, filters.q)"></span>
          <span v-else>{{ c.content }}</span>
        </div>
        <div class="flex items-center justify-between comment-footer">
          <div class="flex gap-3">
            <span>♥ {{ c.liked_count }}</span>
            <span>💬 {{ c.sub_comment_count }}</span>
          </div>
          <a :href="`https://www.xiaohongshu.com/explore/${c.note_id}`"
             target="_blank"
             rel="noopener"
             class="btn btn-primary btn-xs">
            查看原文 ↗
          </a>
        </div>
      </div>

      <div v-if="result.total_pages>1" class="flex items-center justify-between" style="margin-top:1rem; padding-top:0.75rem; border-top:1px solid var(--border-subtle);">
        <span class="text-xs text-muted">第 {{ result.page }}/{{ result.total_pages }} 页</span>
        <div class="flex gap-2">
          <button class="btn btn-ghost btn-xs" :disabled="result.page<=1" @click="go(-1)">上一页</button>
          <button class="btn btn-ghost btn-xs" :disabled="result.page>=result.total_pages" @click="go(1)">下一页</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useComments, type CommentSearchResult } from '../composables/useComments'

const props = defineProps<{ id: string }>()
const route = useRoute()
const taskId = props.id || route.params.id as string
const { search: searchComments } = useComments()
const searching = ref(false)
const filters = reactive({ q:'', min_score:0, min_likes:0, sort:'score', actionable_only:false, page:1, per_page:50 })
const result = reactive<CommentSearchResult>({ items:[], total:0, page:1, per_page:50, total_pages:0 })

function usefulnessBadge(l:string){const m:Record<string,string>={high:'badge-success',medium:'badge-warning',low:'badge-neutral'};return m[l]||'badge-neutral'}
function highlight(t:string,q:string){if(!q)return t;return t.replace(new RegExp(q.replace(/[.*+?^${}()|[\]\\]/g,'\\$&'),'gi'),m=>`<span style="color:var(--accent);font-weight:600;">${m}</span>`)}
function go(d:number){filters.page+=d;handleSearch()}
async function handleSearch(){searching.value=true;try{Object.assign(result,await searchComments(Number(taskId),{...filters}))}catch(e:any){ElMessage.error(e?.response?.data?.detail||'搜索失败')}finally{searching.value=false}}
function reset(){filters.q='';filters.min_score=0;filters.min_likes=0;filters.page=1;handleSearch()}
handleSearch()
</script>

<style scoped>
.result-item {
  padding:0.7rem;
  border:1px solid var(--border-subtle);
  border-radius:var(--radius-sm);
  margin-bottom:0.5rem;
  transition:all var(--transition-fast);
}
.result-item:hover{border-color:var(--border-default);background:var(--bg-card-hover);}
.comment-user{font-size:0.786rem;font-weight:500;color:var(--accent);}
.comment-content{font-size:0.857rem;margin:0.4rem 0;line-height:1.5;}
.comment-footer{font-size:0.714rem;color:var(--text-secondary);}
</style>
