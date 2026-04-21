import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    component: () => import('@/layouts/MainLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        name: 'Chat',
        component: () => import('@/views/Chat.vue')
      },
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/Dashboard.vue'),
        meta: { requiresAdmin: true }
      },
      {
        path: 'orders',
        name: 'Orders',
        component: () => import('@/views/Orders.vue')
      },
      {
        path: 'knowledge',
        name: 'Knowledge',
        component: () => import('@/views/Knowledge.vue'),
        meta: { requiresAdmin: true }
      },
      {
        path: 'chat-logs',
        name: 'ChatLogs',
        component: () => import('@/views/ChatLogs.vue'),
        meta: { requiresAdmin: true }
      },
      {
        path: 'service-desk',
        name: 'ServiceDesk',
        component: () => import('@/views/ServiceDesk.vue'),
        meta: { requiresAdmin: true }
      },
      {
        path: 'cache',
        name: 'CacheManage',
        component: () => import('@/views/CacheManage.vue'),
        meta: { requiresAdmin: true }
      },
      {
        path: 'builtin-evaluation',
        name: 'BuiltinEvaluation',
        component: () => import('@/views/BuiltinEvaluation.vue'),
        meta: { requiresAdmin: true }
      },
      {
        path: 'recall-comparison',
        name: 'RecallComparison',
        component: () => import('@/views/RecallComparison.vue'),
        meta: { requiresAdmin: true }
      },
      {
        path: 'profile',
        name: 'Profile',
        component: () => import('@/views/Profile.vue')
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')
  const role = localStorage.getItem('userRole') || 'user'
  
  if (to.meta.requiresAuth !== false && !token) {
    next('/login')
  } else if (to.path === '/login' && token) {
    if (role === 'admin') {
      next('/service-desk')
    } else {
      next('/')
    }
  } else if (to.path === '/' && role === 'admin' && token && !to.query.ticket_id) {
    next('/service-desk')
  } else if (to.meta.requiresAdmin && role !== 'admin') {
    next('/')
  } else {
    next()
  }
})

export default router
