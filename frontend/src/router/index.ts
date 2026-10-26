import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/station/summer-palace-east' },
    { path: '/station', redirect: '/station/summer-palace-east' },
    {
      path: '/station/:stationId', name: 'ServiceStation',
      component: () => import('@/views/station/StationServiceView.vue'),
      meta: {title:'景区数字人服务站',requiresAuth:false},
    },
    {
      path: '/login',
      name: 'Login',
      component: () => import('@/views/login/LoginView.vue'),
      meta: {
        title: '登录页' // 面包屑显示标题
      }
    },
    // 管理员端；个人游览和路线领取使用 app/。
    {
      path: '/admin',
      redirect: { name: 'Home' },
      component: () => import('@/layouts/BaseLayout.vue'),
      meta: {
        requiresAuth: true // 是否需要登录验证，配置根路由即可，子路由会继承
      },
      children: [
        {
          path:'/stations',name:'StationAdmin',
          component:()=>import('@/views/station/StationAdminView.vue'),
          meta:{title:'服务站管理'},
        },
        {
          path: '/home',
          name: 'Home',
          component: () => import('@/views/home/HomeView.vue'),
          meta: { title: '主页' }
        },
        // 景点管理
        {
          path: '/scenic-spot',
          name: 'ScenicSpot',
          redirect: { name: 'ScenicSpotList' },
          meta: { title: '景点管理' },
          children: [
            {
              path: '/scenic-spot/list',
              name: 'ScenicSpotList',
              component: () => import('@/views/scenic-spot/ScenicSpotListView.vue'),
              meta: { title: '景点列表' }
            },
            {
              path: '/scenic-spot/create',
              name: 'ScenicSpotCreate',
              component: () => import('@/views/scenic-spot/ScenicSpotEditView.vue'),
              meta: { title: '新增景点' }
            },
            {
              path: '/scenic-spot/:spotId/edit',
              name: 'ScenicSpotEdit',
              component: () => import('@/views/scenic-spot/ScenicSpotEditView.vue'),
              meta: { title: '编辑景点' },
              props: true
            }
          ]
        },
        // 知识库管理
        {
          path: '/knowledge/list',
          name: 'KnowledgeBaseList',
          component: () => import('@/views/knowledge/KnowledgeBaseView.vue'),
          meta: { title: '知识库管理' }
        },
        // 游览路线
        {
          path: '/tour-route/list',
          name: 'TourRouteList',
          component: () => import('@/views/tour-route/TourRouteView.vue'),
          meta: { title: '游览路线' }
        },
        // 数字导游管理
        {
          path: '/digital-guide/list',
          name: 'DigitalGuideList',
          component: () => import('@/views/digital-guide/DigitalGuideView.vue'),
          meta: { title: '数字导游管理' }
        },
        // 导览会话
        {
          path: '/tour-session/overview',
          name: 'TourSessionOverview',
          component: () => import('@/views/tour-session/TourSessionListView.vue'),
          meta: { title: '导览会话管理' }
        },
        {
          path: '/tour-session/:sessionId/detail',
          name: 'TourSessionDetail',
          component: () => import('@/views/tour-session/TourSessionDetailView.vue'),
          meta: { title: '会话详情' }
        },
        // 数据分析
        {
          path: '/analytics',
          name: 'Analytics',
          redirect: { name: 'AnalyticsDashboard' },
          meta: { title: '数据分析' },
          children: [
            {
              path: '/analytics/dashboard',
              name: 'AnalyticsDashboard',
              component: () => import('@/views/analytics/AnalyticsDashboardView.vue'),
              meta: { title: '综合分析看板' }
            },
            {
              path: '/analytics/feedback',
              name: 'FeedbackAnalytics',
              component: () => import('@/views/analytics/FeedbackAnalyticsView.vue'),
              meta: { title: '游客反馈分析' }
            }
          ]
        },
        // ---------------------
        //       系统管理
        // ---------------------
        {
          path: '/system',
          name: 'System',
          redirect: { name: 'SystemOverview' },
          meta: { title: '系统概览' },
          children: [
            {
              path: '/system/overview',
              name: 'SystemOverview',
              component: () => import('@/views/system/SystemOverviewView.vue'),
              meta: { title: '系统概览' }
            }
          ]
        }
      ]
    },
    {
      path: '/:pathMatch(.*)*',
      name: 'NotFound',
      component: () => import('@/views/error/NotFound.vue'),
      meta: { title: '404' }
    }
  ]
})

import { useTokenStore } from '@/stores/userToken'

router.beforeEach((to, from, next) => {
  if (to.matched.some((r) => r.meta?.requiresAuth)) {
    // 登录状态缓存
    const tokenStore = useTokenStore()

    if (!tokenStore.token.access_token) {
      // 没有登录，跳转登录页面，同时记录 想去的地址 to.fullPath，方便执行登陆后跳转回去
      next({ name: 'Login', query: { redirect: to.fullPath } })
      return
    }
  }
  // 动态更改页面 title
  to.matched.some((item) => {
    if (!item.meta.title) return ''

    const Title = '智游知境'
    if (Title) document.title = `${item.meta.title} | ${Title}`
    else document.title = item.meta.title as string
  })

  next()
})

export default router