import { createRouter, createWebHistory } from 'vue-router'

import BackupView from '@/views/BackupView.vue'
import CategoryView from '@/views/CategoryView.vue'
import FavoritesView from '@/views/FavoritesView.vue'
import HomeView from '@/views/HomeView.vue'
import InventoryView from '@/views/InventoryView.vue'
import ItemListView from '@/views/ItemListView.vue'
import LocationView from '@/views/LocationView.vue'
import ManagementView from '@/views/ManagementView.vue'
import RestockView from '@/views/RestockView.vue'
import SettingsView from '@/views/SettingsView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView,
    },
    {
      path: '/items',
      name: 'items',
      component: ItemListView,
    },
    {
      path: '/locations',
      name: 'locations',
      component: LocationView,
    },
    {
      path: '/categories',
      name: 'categories',
      component: CategoryView,
    },
    {
      path: '/backups',
      name: 'backups',
      component: BackupView,
    },
    {
      path: '/favorites',
      name: 'favorites',
      component: FavoritesView,
    },
    {
      path: '/restock',
      name: 'restock',
      component: RestockView,
    },
    {
      path: '/settings',
      name: 'settings',
      component: SettingsView,
    },
    {
      path: '/extension-settings',
      name: 'extension-settings',
      component: SettingsView,
    },
    {
      path: '/management',
      name: 'management',
      component: ManagementView,
    },
    {
      path: '/extensions/:extensionId',
      name: 'extension-tool',
      component: InventoryView,
    },
  ],
})

export default router
