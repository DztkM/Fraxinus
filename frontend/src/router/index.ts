import { createRouter, createWebHistory } from 'vue-router'
import FileManager from '../components/FileManager.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: FileManager,
    },
    {
      path: '/folders/:id',
      name: 'folder',
      component: FileManager,
    },
    {
      path: '/files/:id',
      name: 'file-download',
      component: () => import('../views/FileDownload.vue'),
    }
  ],
})

export default router
