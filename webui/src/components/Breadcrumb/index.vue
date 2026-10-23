<!--
  Copyright© 2024-2026 China Mobile (SuZhou) Software Technology Co.,Ltd.

  qcos is licensed under Mulan PSL v2.
  You can use this software according to the terms and conditions
  of the Mulan PSL v2.
  You may obtain a copy of Mulan PSL v2 at:
          http://license.coscl.org.cn/MulanPSL2
  THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS,
      WITHOUT WARRANTIES OF ANY KIND,
  EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
  MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
  See the Mulan PSL v2 for more details.
-->

<template>
  <el-breadcrumb class="app-breadcrumb" separator="/">
    <transition-group name="breadcrumb">
      <el-breadcrumb-item v-for="(item,index) in levelList" :key="item.path">
        <span v-if="item.redirect==='noRedirect'||index==levelList.length-1" class="no-redirect">{{ item.meta.title }}</span>
        <a v-else @click.prevent="handleLink(item)">{{ item.meta.title }}</a>
      </el-breadcrumb-item>
    </transition-group>
  </el-breadcrumb>
</template>

<script>
import { compile } from 'path-to-regexp'

export default {
  name: 'BreadcrumbNav',
  data() {
    return {
      levelList: null
    }
  },
  watch: {
    $route() {
      this.getBreadcrumb()
    }
  },
  created() {
    this.getBreadcrumb()
  },
  methods: {
    getBreadcrumb() {
      // only show routes with meta.title
      let matched = this.$route.matched.filter(item => item.meta && item.meta.title)
      const first = matched[0]

      if (!this.isDashboard(first)) {
        matched = [{ path: '/dashboard', meta: { title: '首页' }}].concat(matched)
      }

      // insert parent list page when activeMenu is set
      const activeMenu = this.$route.meta && this.$route.meta.activeMenu
      if (activeMenu) {
        // find and insert ancestor menu routes (e.g. "身份与访问控制")
        // for activeMenu "/account/projects", parent path is "/account"
        const segments = activeMenu.split('/').filter(Boolean)
        const parentPaths = []
        for (let i = 1; i < segments.length; i++) {
          parentPaths.push('/' + segments.slice(0, i).join('/'))
        }
        for (const parentPath of parentPaths) {
          const parentRoute = this.$router.getRoutes().find(r => r.path === parentPath)
          if (parentRoute && parentRoute.meta && parentRoute.meta.title) {
            // avoid duplicate if already in matched
            const exists = matched.some(m => m.path === parentPath)
            if (!exists) {
              matched.splice(matched.length - 1, 0, {
                path: parentPath,
                meta: parentRoute.meta
              })
            }
          }
        }

        const menuRoute = this.$router.getRoutes().find(r => r.path === activeMenu)
        if (menuRoute && menuRoute.meta && menuRoute.meta.title) {
          // insert before the last item (the detail page itself)
          const lastItem = matched[matched.length - 1]
          if (lastItem && lastItem.path !== activeMenu) {
            matched.splice(matched.length - 1, 0, {
              path: activeMenu,
              meta: menuRoute.meta
            })
          }
        }
      }

      this.levelList = matched.filter(item => item.meta && item.meta.title && item.meta.breadcrumb !== false)
    },
    isDashboard(route) {
      const name = route && route.name
      if (!name) {
        return false
      }
      return name.trim().toLocaleLowerCase() === 'Dashboard'.toLocaleLowerCase()
    },
    pathCompile(path) {
      const { params } = this.$route
      var toPath = compile(path)
      return toPath(params)
    },
    handleLink(item) {
      const { redirect, path } = item
      if (redirect) {
        this.$router.push(redirect)
        return
      }
      this.$router.push(this.pathCompile(path))
    }
  }
}
</script>

<style lang="scss" scoped>
.app-breadcrumb.el-breadcrumb {
  display: inline-block;
  font-size: 14px;
  line-height: 50px;
  margin-left: 8px;

  .no-redirect {
    color: #97a8be;
    cursor: text;
  }
}
</style>
