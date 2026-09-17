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
    path: '/',
    component: Layout,
    redirect: '/dashboard',
    children: [{
      path: 'dashboard',
      name: 'Dashboard',
      component: () => import('@/views/dashboard/index'),
      meta: { title: '项目概览', icon: 'el-icon-s-home' }
    }]
  },

  {
    path: '/',
    component: Layout,
    redirect: '/job_manager',
    children: [{
      path: 'job_manager',
      name: 'JobManager',
      component: () => import('@/views/job/job_list.vue'),
      meta: { title: '作业查询', icon: 'el-icon-s-management' }
    }]
  },

  {
    path: 'job_detail',
    name: 'JobDetail',
    component: () => import('@/views/job/job_detail.vue'),
    hidden: true,
    meta: { title: '作业详情' }
  },

  {
    path: '/job_submit',
    component: Layout,
    redirect: '/job_submit',
    name: 'JobSubmit',
    meta: { title: '作业提交', icon: 'el-icon-upload' },
    children: [
      {
        path: 'qasm',
        name: 'qasmTree',
        component: () => import('@/views/job/qasm.vue'),
        meta: { title: 'OpenQASM作业提交', icon: 'el-icon-s-unfold' }
      },
      {
        path: 'qubo',
        name: 'quboTree',
        component: () => import('@/views/job/qubo.vue'),
        meta: { title: 'QUBO矩阵作业提交', icon: 'el-icon-s-unfold' }
      }
      /*
      {
        path: 'sequence',
        name: 'sequenceTree',
        component: () => import('@/views/task_submit/sequence'),
        meta: { title: '序列作业提交', icon: 'el-icon-s-unfold' }
      }
      */
    ]
  },

  {
    path: '/device',
    component: Layout,
    redirect: '/device',
    meta: { title: '设备信息', icon: 'el-icon-s-platform' },
    children: [
      {
        path: 'devices',
        name: 'deviceTree',
        component: () => import('@/views/device/device_list.vue'),
        meta: { title: '设备列表', icon: 'el-icon-s-unfold' }
      },
      {
        path: 'drivers',
        name: 'driverTree',
        component: () => import('@/views/driver/driver_list.vue'),
        meta: { title: '驱动列表', icon: 'el-icon-s-unfold' }
      },
      {
        path: 'transpilers',
        name: 'transpilerTree',
        component: () => import('@/views/transpiler/transpiler_list.vue'),
        meta: { title: '转译器列表', icon: 'el-icon-s-unfold' }
      }
    ]
  },

  {
    path: 'device_details',
    name: 'DeviceDetails',
    component: () => import('@/views/device/device_details.vue'),
    hidden: true,
    meta: { title: '设备详情' }
  },

  {
    path: 'driver_details',
    name: 'DriverDetails',
    component: () => import('@/views/driver/driver_details.vue'),
    hidden: true,
    meta: { title: '驱动详情' }
  },

  {
    path: 'transpiler_details',
    name: 'TranspilerDetails',
    component: () => import('@/views/transpiler/transpiler_details.vue'),
    hidden: true,
    meta: { title: '转译器详情' }
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
        meta: { title: 'Rabi振荡扫描', icon: 'el-icon-s-unfold' }
      },
      {
        path: 'raman_ch1',
        name: 'raman_ch1Tree',
        component: () => import('@/views/calibration/sub_pages/raman_ch1'),
        meta: { title: '单比特对准阱扫描CH1通道', icon: 'el-icon-s-unfold' }
      },
      {
        path: 'raman_ch2',
        name: 'raman_ch2Table',
        component: () => import('@/views/calibration/sub_pages/raman_ch2'),
        meta: { title: '单比特对准阱扫描CH2通道', icon: 'el-icon-s-unfold' }
      },
      {
        path: 'arrange_ch1',
        name: 'arrange_ch1Tree',
        component: () => import('@/views/calibration/sub_pages/arrange_ch1'),
        meta: { title: '重排CH1频率扫描', icon: 'el-icon-s-unfold' }
      },
      {
        path: 'arrange_ch2',
        name: 'arrange_ch2Tree',
        component: () => import('@/views/calibration/sub_pages/arrange_ch2'),
        meta: { title: '重排CH2频率扫描', icon: 'el-icon-s-unfold' }
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
