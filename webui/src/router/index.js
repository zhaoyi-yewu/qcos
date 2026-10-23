
/**
 * Copyright© 2024-2026 China Mobile (SuZhou) Software Technology Co.,Ltd.
 *
 * qcos is licensed under Mulan PSL v2.
 * You can use this software according to the terms and conditions
 * of the Mulan PSL v2.
 * You may obtain a copy of Mulan PSL v2 at:
 *         http://license.coscl.org.cn/MulanPSL2
 * THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS,
 *     WITHOUT WARRANTIES OF ANY KIND,
 * EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
 * MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
 * See the Mulan PSL v2 for more details.
 */

// 这个js文件是，整个页面最左侧的黑色树状长条目标
import { createRouter, createWebHistory } from 'vue-router'

/* Layout */
import Layout from '@/layout'

/**
 * Note: sub-menu only appear when route children.length >= 1
 * Detail see: https://panjiachen.github.io/vue-element-admin-site/guide/essentials/router-and-nav.html
 *
 * hidden: true                   if set true, item will not show in the sidebar(default is false)
 * alwaysShow: true               if set true, will always show the root menu
 *                                if not set alwaysShow, when item has more than one children route,
 *                                it will becomes nested mode, otherwise not show the root menu
 * redirect: noRedirect           if set noRedirect will no redirect in the breadcrumb
 * name:'router-name'             the name is used by <keep-alive> (must set!!!)
 * meta : {
    roles: ['admin','editor']    control the page roles (you can set multiple roles)
    title: 'title'               the name show in sidebar and breadcrumb (recommend set)
    icon: 'svg-name'/'el-icon-x' the icon show in the sidebar
    breadcrumb: false            if set false, the item will hidden in breadcrumb(default is true)
    activeMenu: '/example/list'  if set path, the sidebar will highlight the path you set
  }
 */

/**
 * constantRoutes
 * a base page that does not have permission requirements
 * all roles can be accessed
 */
export const constantRoutes = [
  {
    path: '/login',
    component: () => import('@/views/login/index'),
    hidden: true
  },

  {
    path: '/404',
    component: () => import('@/views/404'),
    hidden: true
  },

  {
    path: '/profile',
    component: Layout,
    hidden: true,
    children: [
      {
        path: '',
        name: 'Profile',
        component: () => import('@/views/profile/index'),
        meta: { title: '用户信息' }
      }
    ]
  },

  {
    path: '/',
    component: Layout,
    redirect: '/dashboard',
    children: [{
      path: 'dashboard',
      name: 'Dashboard',
      component: () => import('@/views/dashboard/index'),
      meta: { title: '首页', icon: 'el-icon-home-filled' }
    }]
  },

  {
    path: '/jobs',
    component: Layout,
    redirect: '/jobs/',
    name: 'JobManager',
    meta: { title: '作业管理', icon: 'el-icon-tickets' },
    children: [
      {
        path: '',
        name: 'JobList',
        component: () => import('@/views/job/job_list.vue'),
        meta: { title: '作业列表', icon: 'el-icon-document' }
      },
      {
        path: 'submit',
        name: 'JobSubmit',
        component: () => import('@/views/job/job_submit.vue'),
        meta: { title: '作业提交', icon: 'el-icon-upload' }
      },
      {
        path: 'transpilers',
        name: 'transpilerTree',
        component: () => import('@/views/transpiler/transpiler_list.vue'),
        meta: { title: '转译器列表', icon: 'el-icon-magic-stick' }
      }
    ]
  },

  {
    path: '/jobs/:jobId',
    component: Layout,
    hidden: true,
    children: [
      {
        path: '',
        name: 'JobDetail',
        component: () => import('@/views/job/job_details.vue'),
        meta: { title: '作业详情', activeMenu: '/jobs/' }
      }
    ]
  },

  {
    path: '/device-mgmt',
    component: Layout,
    redirect: '/device-mgmt/devices',
    name: 'DeviceManager',
    meta: { title: '设备管理', icon: 'el-icon-cpu' },
    children: [
      {
        path: 'devices',
        name: 'deviceTree',
        component: () => import('@/views/device/device_list.vue'),
        meta: { title: '设备列表', icon: 'el-icon-monitor' }
      },
      {
        path: 'groups',
        name: 'deviceGroupTree',
        component: () => import('@/views/device/device_group_list.vue'),
        meta: { title: '设备组管理', icon: 'el-icon-files' }
      },
      {
        path: 'flavors',
        name: 'flavorTree',
        component: () => import('@/views/flavor/flavor_list.vue'),
        meta: { title: '资源规格列表', icon: 'el-icon-setting' }
      },
      {
        path: 'workers',
        name: 'workerTree',
        component: () => import('@/views/device/worker_list.vue'),
        meta: { title: '工作器列表', icon: 'el-icon-odometer', roles: ['admin'] }
      },
      {
        path: 'drivers',
        name: 'driverTree',
        component: () => import('@/views/driver/driver_list.vue'),
        meta: { title: '驱动列表', icon: 'el-icon-grid' }
      }
    ]
  },

  {
    path: '/user-settings',
    component: Layout,
    redirect: '/user-settings/profile',
    name: 'UserSettings',
    alwaysShow: true,
    meta: { title: '账户设置', icon: 'el-icon-user-filled' },
    children: [
      {
        path: 'profile',
        name: 'UserProfile',
        component: () => import('@/views/profile/index'),
        meta: { title: '用户信息', icon: 'el-icon-info-filled' }
      }
    ]
  },

  {
    path: '/account',
    component: Layout,
    redirect: '/account/projects',
    name: 'AccountManager',
    meta: { title: '身份与访问控制', icon: 'el-icon-user', roles: ['admin'] },
    children: [
      {
        path: 'projects',
        name: 'ProjectList',
        component: () => import('@/views/account/project_list.vue'),
        meta: { title: '项目管理', icon: 'el-icon-folder' }
      },
      {
        path: 'roles',
        name: 'RoleList',
        component: () => import('@/views/account/role_list.vue'),
        meta: { title: '角色管理', icon: 'el-icon-circle-check' }
      },
      {
        path: 'users',
        name: 'UserList',
        component: () => import('@/views/account/user_list.vue'),
        meta: { title: '用户管理', icon: 'el-icon-avatar' }
      },
      {
        path: 'login-logs',
        name: 'LoginLogList',
        component: () => import('@/views/account/login_log_list.vue'),
        meta: { title: '登录日志', icon: 'el-icon-clock' }
      }
    ]
  },

  {
    path: '/system-mgmt',
    component: Layout,
    redirect: '/system-mgmt/system-info',
    name: 'SystemManager',
    meta: { title: '系统监控', icon: 'el-icon-monitor', roles: ['admin'] },
    children: [
      {
        path: 'system-info',
        name: 'SystemInfo',
        component: () => import('@/views/system/system_info.vue'),
        meta: { title: '系统信息', icon: 'el-icon-info-filled' }
      },
      {
        path: 'component-status',
        name: 'ComponentStatus',
        component: () => import('@/views/system/component_status.vue'),
        meta: { title: '组件状态', icon: 'el-icon-data-line' }
      },
      {
        path: 'job-stats',
        name: 'JobStats',
        component: () => import('@/views/system/job_stats.vue'),
        meta: { title: '作业统计', icon: 'el-icon-histogram' }
      },
      {
        path: 'api-stats',
        name: 'ApiStats',
        component: () => import('@/views/system/api_stats.vue'),
        meta: { title: 'API访问统计', icon: 'el-icon-pie-chart' }
      }
    ]
  },

  {
    path: '/device-mgmt/devices/:deviceName',
    component: Layout,
    hidden: true,
    children: [
      {
        path: '',
        name: 'DeviceDetails',
        component: () => import('@/views/device/device_details.vue'),
        meta: { title: '设备详情', activeMenu: '/device-mgmt/devices' }
      }
    ]
  },

  {
    path: '/device-mgmt/drivers/:driverName',
    component: Layout,
    hidden: true,
    children: [
      {
        path: '',
        name: 'DriverDetails',
        component: () => import('@/views/driver/driver_details.vue'),
        meta: { title: '驱动详情', activeMenu: '/device-mgmt/drivers' }
      }
    ]
  },

  {
    path: '/device-mgmt/groups/:groupId',
    component: Layout,
    hidden: true,
    children: [
      {
        path: '',
        name: 'DeviceGroupDetails',
        component: () => import('@/views/device/device_group_details.vue'),
        meta: { title: '设备组详情', activeMenu: '/device-mgmt/groups' }
      }
    ]
  },

  {
    path: '/device-mgmt/workers/:workerName',
    component: Layout,
    hidden: true,
    children: [
      {
        path: '',
        name: 'WorkerDetails',
        component: () => import('@/views/device/worker_details.vue'),
        meta: { title: '工作器详情', activeMenu: '/device-mgmt/workers' }
      }
    ]
  },

  {
    path: '/account/projects/:projectId',
    component: Layout,
    hidden: true,
    children: [
      {
        path: '',
        name: 'ProjectDetails',
        component: () => import('@/views/account/project_details.vue'),
        meta: { title: '项目详情', activeMenu: '/account/projects' }
      }
    ]
  },

  {
    path: '/account/roles/:roleId',
    component: Layout,
    hidden: true,
    children: [
      {
        path: '',
        name: 'RoleDetails',
        component: () => import('@/views/account/role_details.vue'),
        meta: { title: '角色详情', activeMenu: '/account/roles' }
      }
    ]
  },

  {
    path: '/account/users/:userId',
    component: Layout,
    hidden: true,
    children: [
      {
        path: '',
        name: 'UserDetails',
        component: () => import('@/views/account/user_details.vue'),
        meta: { title: '用户详情', activeMenu: '/account/users' }
      }
    ]
  },

  {
    path: '/jobs/transpilers/:transpilerName',
    component: Layout,
    hidden: true,
    children: [
      {
        path: '',
        name: 'TranspilerDetails',
        component: () => import('@/views/transpiler/transpiler_details.vue'),
        meta: { title: '转译器详情', activeMenu: '/jobs/transpilers' }
      }
    ]
  },

  {
    path: '/flavors/:flavorId',
    component: Layout,
    hidden: true,
    children: [
      {
        path: '',
        name: 'FlavorDetails',
        component: () => import('@/views/flavor/flavor_details.vue'),
        meta: { title: '资源规格详情', activeMenu: '/device-mgmt/flavors' }
      }
    ]
  },

  /*
  {
    // 这个path好像并不和谁对应，貌似改成什么都可以
    path: '/calibration',
    component: Layout,
    redirect: '/example/table',
    name: 'Example',
    meta: { title: '校准实验', icon: 'el-icon-menu' },
    children: [
      {
        path: 'rabi',
        name: 'rabiTree',
        component: () => import('@/views/calibration/sub_pages/rabi'),
        meta: { title: 'Rabi振荡扫描', icon: 'el-icon-data-line' }
      },
      {
        path: 'raman_ch1',
        name: 'raman_ch1Tree',
        component: () => import('@/views/calibration/sub_pages/raman_ch1'),
        meta: { title: '单比特对准阱扫描CH1通道', icon: 'el-icon-data-line' }
      },
      {
        path: 'raman_ch2',
        name: 'raman_ch2Table',
        component: () => import('@/views/calibration/sub_pages/raman_ch2'),
        meta: { title: '单比特对准阱扫描CH2通道', icon: 'el-icon-data-line' }
      },
      {
        path: 'arrange_ch1',
        name: 'arrange_ch1Tree',
        component: () => import('@/views/calibration/sub_pages/arrange_ch1'),
        meta: { title: '重排CH1频率扫描', icon: 'el-icon-data-line' }
      },
      {
        path: 'arrange_ch2',
        name: 'arrange_ch2Tree',
        component: () => import('@/views/calibration/sub_pages/arrange_ch2'),
        meta: { title: '重排CH2频率扫描', icon: 'el-icon-data-line' }
      }
    ]
  },

  {
    path: '/',
    component: Layout,
    redirect: '/device',
    children: [{
      path: 'device',
      name: 'device',
      component: () => import('@/views/device/device.vue'),
      meta: { title: '设备信息', icon: 'el-icon-s-platform' }
    }]
  },
  */

  // 404 page must be placed at the end !!!
  { path: '/:pathMatch(.*)*', redirect: '/404', hidden: true }
]

const router = createRouter({
  history: createWebHistory(),
  scrollBehavior: () => ({ left: 0, top: 0 }),
  routes: constantRoutes
})

// Detail see: https://github.com/vuejs/vue-router/issues/1234#issuecomment-357941465
export function resetRouter() {
  const newRouter = createRouter({
    history: createWebHistory(),
    scrollBehavior: () => ({ left: 0, top: 0 }),
    routes: constantRoutes
  })
  router.matcher = newRouter.matcher // reset router
}

export default router
