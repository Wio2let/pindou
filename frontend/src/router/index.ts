import { createRouter, createWebHashHistory } from 'vue-router'

const router = createRouter({
  // Hash history works when opening dist/index.html directly via file://
  history: createWebHashHistory(),
  routes: [
    {
      path: '/',
      redirect: '/bead-studio',
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
      path: '/bead-studio/gallery',
      name: 'bead-gallery',
      component: () => import('../views/Gallery.vue'),
    },
    {
      path: '/bead-studio/inventory',
      name: 'bead-inventory',
      component: () => import('../views/Inventory.vue'),
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: '/bead-studio',
    },
  ],
})

export default router
