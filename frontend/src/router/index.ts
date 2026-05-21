import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'dashboard',
      component: () => import('../views/Dashboard.vue'),
    },
    {
      path: '/tasks/create',
      name: 'task-create',
      component: () => import('../views/TaskCreate.vue'),
    },
    {
      path: '/tasks',
      name: 'task-list',
      component: () => import('../views/TaskList.vue'),
    },
    {
      path: '/tasks/:id',
      name: 'task-detail',
      component: () => import('../views/TaskDetail.vue'),
      props: true,
    },
    {
      path: '/tasks/:id/edit',
      name: 'task-edit',
      component: () => import('../views/TaskEdit.vue'),
      props: true,
    },
    {
      path: '/tasks/:id/search',
      name: 'comment-search',
      component: () => import('../views/CommentSearch.vue'),
      props: true,
    },
    {
      path: '/favorites',
      name: 'favorites',
      component: () => import('../views/Favorites.vue'),
    },
    {
      path: '/bead-studio',
      name: 'bead-studio',
      component: () => import('../views/BeadStudio.vue'),
    },
    {
      path: '/bead-studio/cards',
      name: 'bead-cards',
      component: () => import('../views/MardCards.vue'),
    },
    {
      path: '/bilibili',
      name: 'bilibili',
      component: () => import('../views/BilibiliSearch.vue'),
    },
  ],
})

export default router
