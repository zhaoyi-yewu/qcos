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
  <div class="file-panel">
    <div class="file-panel-toolbar">
      <el-breadcrumb separator="/" class="file-panel-breadcrumb">
        <el-breadcrumb-item>
          <el-button link size="small" @click="goTo('')">/data</el-button>
        </el-breadcrumb-item>
        <el-breadcrumb-item v-for="(seg, idx) in pathSegments" :key="idx">
          <el-button link size="small" @click="goTo(segmentPath(idx))">{{ seg }}</el-button>
        </el-breadcrumb-item>
      </el-breadcrumb>
      <div class="file-panel-actions">
        <el-button size="small" @click="refresh">刷新</el-button>
        <el-upload
          :show-file-list="false"
          :http-request="onUpload"
          :disabled="uploading"
          accept="*/*"
        >
          <el-button size="small" type="primary" :loading="uploading">上传</el-button>
        </el-upload>
      </div>
    </div>

    <el-progress
      v-if="uploading"
      :percentage="uploadProgress"
      :stroke-width="4"
      class="file-panel-progress"
    />

    <el-table
      v-loading="loading"
      :data="files"
      size="small"
      class="file-panel-table"
      @row-dblclick="onRowDblClick"
    >
      <el-table-column label="名称" min-width="220">
        <template #default="{ row }">
          <span class="file-name">
            <el-icon v-if="row.is_dir"><Folder /></el-icon>
            <el-icon v-else><Document /></el-icon>
            <el-button v-if="row.is_dir" link type="primary" @click="enterDir(row.name)">
              {{ row.name }}
            </el-button>
            <span v-else>{{ row.name }}</span>
          </span>
        </template>
      </el-table-column>
      <el-table-column label="大小" width="110">
        <template #default="{ row }">
          <span v-if="!row.is_dir">{{ formatSize(row.size) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="修改时间" width="180">
        <template #default="{ row }">
          {{ formatTime(row.mtime) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="140">
        <template #default="{ row }">
          <el-button v-if="!row.is_dir" link size="small" @click="onDownload(row)">下载</el-button>
          <el-button link size="small" type="danger" @click="onDelete(row)">删除</el-button>
        </template>
      </el-table-column>
      <template #empty>
        <span>目录为空</span>
      </template>
    </el-table>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Document, Folder } from '@element-plus/icons-vue'
import { deleteFile, downloadFile, listFiles, uploadFile } from '@/api/terminal'
import { useTerminalStore } from '@/store/modules/terminal'

defineOptions({ name: 'TerminalFilePanel' })

const terminalStore = useTerminalStore()

const files = ref([])
const loading = ref(false)
const uploading = ref(false)
const uploadProgress = ref(0)

const currentPath = computed(() => terminalStore.currentPath || '')

const pathSegments = computed(() =>
  currentPath.value ? currentPath.value.split('/').filter(Boolean) : []
)

function segmentPath(idx) {
  return pathSegments.value.slice(0, idx + 1).join('/')
}

function normalize(path) {
  return (path || '').replace(/^\/+|\/+$/g, '')
}

function goTo(path) {
  terminalStore.setPath(normalize(path))
  refresh()
}

function enterDir(name) {
  const next = currentPath.value ? `${currentPath.value}/${name}` : name
  goTo(next)
}

async function refresh() {
  loading.value = true
  try {
    const list = await listFiles(currentPath.value)
    // directories first, then files, both alphabetical
    files.value = (list || []).slice().sort((a, b) => {
      if (!!a.is_dir === !!b.is_dir) {
        return String(a.name).localeCompare(String(b.name))
      }
      return a.is_dir ? -1 : 1
    })
  } catch (err) {
    ElMessage({ type: 'error', message: err && err.message ? err.message : '加载失败' })
    files.value = []
  } finally {
    loading.value = false
  }
}

function onRowDblClick(row) {
  if (row && row.is_dir) {
    enterDir(row.name)
  }
}

function joinPath(name) {
  return currentPath.value ? `${currentPath.value}/${name}` : name
}

async function onDownload(row) {
  try {
    await downloadFile(joinPath(row.name))
  } catch (err) {
    ElMessage({ type: 'error', message: err && err.message ? err.message : '下载失败' })
  }
}

async function onDelete(row) {
  try {
    await ElMessageBox.confirm(
      `确认删除 ${row.is_dir ? '目录' : '文件'} "${row.name}"？`,
      '删除确认',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
  } catch (e) {
    return
  }
  try {
    await deleteFile(joinPath(row.name))
    ElMessage({ type: 'success', message: '已删除' })
    refresh()
  } catch (err) {
    ElMessage({ type: 'error', message: err && err.message ? err.message : '删除失败' })
  }
}

async function onUpload(options) {
  if (!options || !options.file) return
  uploading.value = true
  uploadProgress.value = 0
  try {
    await uploadFile(currentPath.value, options.file, (p) => {
      uploadProgress.value = p
    })
    ElMessage({ type: 'success', message: '上传成功' })
    refresh()
  } catch (err) {
    ElMessage({ type: 'error', message: err && err.message ? err.message : '上传失败' })
  } finally {
    uploading.value = false
    uploadProgress.value = 0
  }
}

function formatSize(n) {
  if (n === undefined || n === null || isNaN(Number(n))) return ''
  let v = Number(n)
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let i = 0
  while (v >= 1024 && i < units.length - 1) {
    v /= 1024
    i += 1
  }
  return `${v.toFixed(v >= 100 || i === 0 ? 0 : 1)} ${units[i]}`
}

function formatTime(t) {
  if (!t) return ''
  // backend returns epoch seconds (number) or ISO string
  if (typeof t === 'number') {
    const d = new Date(t * 1000)
    return isNaN(d.getTime()) ? '' : d.toLocaleString()
  }
  const d = new Date(t)
  return isNaN(d.getTime()) ? String(t) : d.toLocaleString()
}

onMounted(() => {
  refresh()
})

defineExpose({ refresh })
</script>

<style lang="scss" scoped>
.file-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;

  .file-panel-toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 4px 8px;
    border-bottom: 1px solid #e4e7ed;
    // never wrap the toolbar onto multiple lines; wrapping pushes the
    // upload/refresh buttons out of the visible area at small panel heights
    flex-wrap: nowrap;
    min-height: 32px;

    .file-panel-breadcrumb {
      flex: 1;
      min-width: 0;
      overflow: hidden;
    }

    .file-panel-actions {
      display: flex;
      gap: 8px;
      align-items: center;
      // the action buttons must keep their natural size; without
      // flex-shrink: 0 the breadcrumb can squeeze them down to nothing
      // when the path is long or the dialog is narrow
      flex-shrink: 0;

      // el-upload wraps the inner el-button in an inline-block div; give
      // it an explicit flex layout so the button stays visible
      :deep(.el-upload) {
        display: inline-flex;
      }
    }
  }

  .file-panel-progress {
    margin: 4px 8px 0 8px;
  }

  .file-panel-table {
    flex: 1;
    overflow: auto;
  }

  .file-name {
    display: inline-flex;
    align-items: center;
    gap: 6px;
  }
}
</style>
