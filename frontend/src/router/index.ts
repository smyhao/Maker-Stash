import { createRouter, createWebHistory } from 'vue-router'

import InventoryView from '@/views/InventoryView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'inventory',
      component: InventoryView,
    },
  ],
})

export default router
