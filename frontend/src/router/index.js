import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import StockDetail from '../views/StockDetail.vue'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: Home
  },
  {
    path: '/stock/:code',
    name: 'StockDetail',
    component: StockDetail
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router 