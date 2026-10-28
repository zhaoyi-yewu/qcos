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
  <div class="monitor-center-container">
    <div class="header">
      <h2>监控中心</h2>
      <div class="header-actions">
        <refresh-interval
          :default-interval="10"
          :refreshing="loading"
          @refresh="fetchAllData"
          @interval-change="onIntervalChange"
        />
      </div>
    </div>

    <el-tabs v-model="activeTab" class="monitor-tabs">
      <!-- ==================== Tab 1: 总览 ==================== -->
      <el-tab-pane label="总览" name="overview">
        <div ref="bigscreenRef" class="bigscreen-container">
          <div class="bigscreen-toolbar">
            <!-- Endpoint switcher is only visible while the bigscreen is
                 in browser fullscreen; in normal mode the sidebar already
                 offers the same selector and would be redundant here.
                 popper teleported=false keeps the dropdown attached to
                 this fullscreen container so options actually render. -->
            <div class="bigscreen-endpoint">
              <span class="bigscreen-endpoint-label">量子计算操作系统</span>
              <el-select
                v-model="bigscreenEndpointName"
                size="small"
                class="bigscreen-endpoint-select"
                popper-class="endpoint-switcher-popper"
                :teleported="false"
                @change="onBigscreenEndpointChange"
              >
                <template v-if="bigscreenEndpointStatus" #prefix>
                  <span
                    class="endpoint-state-dot"
                    :class="'state-' + bigscreenEndpointStatus"
                    :title="bigscreenEndpointStatus"
                  />
                </template>
                <el-option
                  v-for="ep in endpointOptions"
                  :key="ep.name"
                  :value="ep.name"
                  :label="ep.alias || ep.name"
                  :disabled="ep.usable === false"
                  :title="ep.status === 'ok' ? `平台版本: ${ep.platformVersion}\n版本: ${ep.version}\n系统状态: 可用` : ep.status === 'fail' ? `错误: ${ep.error}` : '探测中…'"
                >
                  <div class="endpoint-option">
                    <span
                      class="endpoint-state-dot"
                      :class="'state-' + (ep.status || 'probing')"
                      :title="ep.status || 'probing'"
                    />
                    <span class="endpoint-option-alias">{{ ep.alias || ep.name }}</span>
                    <span class="endpoint-option-meta">
                      <template v-if="ep.status === 'probing'">
                        <el-icon class="is-loading"><Loading /></el-icon>
                      </template>
                      <template v-else-if="ep.status === 'ok'">
                        <span class="endpoint-option-version">v{{ ep.version }}</span>
                      </template>
                    </span>
                  </div>
                </el-option>
              </el-select>
            </div>
            <el-tooltip :content="isBigscreenFullscreen ? '退出全屏' : '进入浏览器全屏'" placement="bottom">
              <el-button
                size="small"
                :icon="FullScreen"
                @click="toggleBigscreenFullscreen"
              >
                {{ isBigscreenFullscreen ? '退出全屏' : '全屏' }}
              </el-button>
            </el-tooltip>
          </div>

          <!-- 编辑模式提示 -->
          <div v-if="isOverviewEditMode" class="edit-mode-tip">
            <el-alert type="info" :closable="false" show-icon>
              <template #title>
                编辑模式已开启：可拖动 / 调整面板大小。点击右上角"完成"退出。
              </template>
            </el-alert>
            <el-button
              size="small"
              class="edit-mode-reset-btn"
              @click="resetLayout('overview')"
            >
              重置布局
            </el-button>
            <el-button
              size="small"
              type="primary"
              class="edit-mode-done-btn"
              @click="exitEditMode('overview')"
            >
              完成
            </el-button>
          </div>

          <GridLayout
            v-model:layout="overviewLayout"
            :col-num="12"
            :row-height="24"
            :is-draggable="isOverviewEditMode"
            :is-resizable="isOverviewEditMode"
            :vertical-compact="true"
            :use-css-transforms="true"
            :margin="[6, 6]"
          >
            <GridItem
              v-for="item in overviewLayout"
              :key="item.i"
              :x="item.x"
              :y="item.y"
              :w="item.w"
              :h="item.h"
              :i="item.i"
              :min-w="3"
              :min-h="4"
              drag-allow-from=".panel-header"
              class="chart-grid-item"
              :class="{ 'is-edit-mode': isOverviewEditMode }"
            >
              <!-- 8 stat cards -->
              <div
                v-if="item.i === 'stat-system'"
                class="panel-wrapper stat-panel"
                @pointerdown="onPanelPointerDown('overview', $event)"
                @pointerup="onPanelPointerUp"
                @pointerleave="onPanelPointerUp"
                @pointercancel="onPanelPointerUp"
              >
                <div class="panel-header">
                  <span class="panel-title">系统状态</span>
                </div>
                <div class="panel-body stat-content">
                  <el-tag
                    :type="systemHealthy ? 'success' : 'danger'"
                    size="large"
                    class="stat-tag"
                  >
                    {{ systemHealthy ? '健康' : '异常' }}
                  </el-tag>
                  <div class="stat-desc">系统整体运行状态</div>
                </div>
              </div>
              <div
                v-else-if="item.i === 'stat-jobs-total'"
                class="panel-wrapper stat-panel"
                @pointerdown="onPanelPointerDown('overview', $event)"
                @pointerup="onPanelPointerUp"
                @pointerleave="onPanelPointerUp"
                @pointercancel="onPanelPointerUp"
              >
                <div class="panel-header">
                  <span class="panel-title">作业总数</span>
                </div>
                <div class="panel-body stat-content">
                  <div class="stat-value">{{ jobStats.total }}</div>
                  <div class="stat-desc">作业总数</div>
                </div>
              </div>
              <div
                v-else-if="item.i === 'stat-jobs-running'"
                class="panel-wrapper stat-panel"
                @pointerdown="onPanelPointerDown('overview', $event)"
                @pointerup="onPanelPointerUp"
                @pointerleave="onPanelPointerUp"
                @pointercancel="onPanelPointerUp"
              >
                <div class="panel-header">
                  <span class="panel-title">运行中作业</span>
                </div>
                <div class="panel-body stat-content">
                  <div class="stat-value primary">{{ jobStats.running }}</div>
                  <div class="stat-desc">运行中作业</div>
                </div>
              </div>
              <div
                v-else-if="item.i === 'stat-jobs-queued'"
                class="panel-wrapper stat-panel"
                @pointerdown="onPanelPointerDown('overview', $event)"
                @pointerup="onPanelPointerUp"
                @pointerleave="onPanelPointerUp"
                @pointercancel="onPanelPointerUp"
              >
                <div class="panel-header">
                  <span class="panel-title">队列中作业</span>
                </div>
                <div class="panel-body stat-content">
                  <div class="stat-value warning">{{ jobStats.queued }}</div>
                  <div class="stat-desc">队列中作业</div>
                </div>
              </div>
              <div
                v-else-if="item.i === 'stat-jobs-completed'"
                class="panel-wrapper stat-panel"
                @pointerdown="onPanelPointerDown('overview', $event)"
                @pointerup="onPanelPointerUp"
                @pointerleave="onPanelPointerUp"
                @pointercancel="onPanelPointerUp"
              >
                <div class="panel-header">
                  <span class="panel-title">已完成作业</span>
                </div>
                <div class="panel-body stat-content">
                  <div class="stat-value success">{{ jobStats.completed }}</div>
                  <div class="stat-desc">已完成作业</div>
                </div>
              </div>
              <div
                v-else-if="item.i === 'stat-jobs-failed'"
                class="panel-wrapper stat-panel"
                @pointerdown="onPanelPointerDown('overview', $event)"
                @pointerup="onPanelPointerUp"
                @pointerleave="onPanelPointerUp"
                @pointercancel="onPanelPointerUp"
              >
                <div class="panel-header">
                  <span class="panel-title">失败作业</span>
                </div>
                <div class="panel-body stat-content">
                  <div class="stat-value danger">{{ jobStats.failed }}</div>
                  <div class="stat-desc">失败作业</div>
                </div>
              </div>
              <div
                v-else-if="item.i === 'stat-api-requests'"
                class="panel-wrapper stat-panel"
                @pointerdown="onPanelPointerDown('overview', $event)"
                @pointerup="onPanelPointerUp"
                @pointerleave="onPanelPointerUp"
                @pointercancel="onPanelPointerUp"
              >
                <div class="panel-header">
                  <span class="panel-title">API 总请求数</span>
                </div>
                <div class="panel-body stat-content">
                  <div class="stat-value">{{ apiStats.totalRequests }}</div>
                  <div class="stat-desc">API 总请求数</div>
                </div>
              </div>
              <div
                v-else-if="item.i === 'stat-api-progress'"
                class="panel-wrapper stat-panel"
                @pointerdown="onPanelPointerDown('overview', $event)"
                @pointerup="onPanelPointerUp"
                @pointerleave="onPanelPointerUp"
                @pointercancel="onPanelPointerUp"
              >
                <div class="panel-header">
                  <span class="panel-title">API 并发请求</span>
                </div>
                <div class="panel-body stat-content">
                  <div class="stat-value primary">{{ apiStats.inProgress }}</div>
                  <div class="stat-desc">API 并发请求</div>
                </div>
              </div>
              <!-- 3 gauge cards -->
              <div
                v-else-if="item.i === 'gauge-cpu'"
                class="panel-wrapper stat-panel gauge-panel"
                @pointerdown="onPanelPointerDown('overview', $event)"
                @pointerup="onPanelPointerUp"
                @pointerleave="onPanelPointerUp"
                @pointercancel="onPanelPointerUp"
              >
                <div class="panel-header">
                  <span class="panel-title">节点CPU总使用率</span>
                </div>
                <div class="panel-body stat-content">
                  <el-progress
                    type="dashboard"
                    :width="110"
                    :stroke-width="10"
                    :percentage="clampPercent(systemStats.host_cpu_percent)"
                    :color="percentColor(systemStats.host_cpu_percent)"
                  />
                  <div class="stat-desc">
                    {{ systemStats.host_cpu_percent.toFixed(1) }}% ·
                    {{ systemStats.cpu_count }} 核
                  </div>
                </div>
              </div>
              <div
                v-else-if="item.i === 'gauge-mem'"
                class="panel-wrapper stat-panel gauge-panel"
                @pointerdown="onPanelPointerDown('overview', $event)"
                @pointerup="onPanelPointerUp"
                @pointerleave="onPanelPointerUp"
                @pointercancel="onPanelPointerUp"
              >
                <div class="panel-header">
                  <span class="panel-title">节点内存总使用率</span>
                </div>
                <div class="panel-body stat-content">
                  <el-progress
                    type="dashboard"
                    :width="110"
                    :stroke-width="10"
                    :percentage="clampPercent(systemStats.mem_percent)"
                    :color="percentColor(systemStats.mem_percent)"
                  />
                  <div class="stat-desc">
                    {{ systemStats.mem_percent.toFixed(1) }}% ·
                    共 {{ formatMb(systemStats.mem_total_mb) }}
                  </div>
                </div>
              </div>
              <div
                v-else-if="item.i === 'gauge-disk'"
                class="panel-wrapper stat-panel gauge-panel"
                @pointerdown="onPanelPointerDown('overview', $event)"
                @pointerup="onPanelPointerUp"
                @pointerleave="onPanelPointerUp"
                @pointercancel="onPanelPointerUp"
              >
                <div class="panel-header">
                  <span class="panel-title">磁盘总使用率</span>
                </div>
                <div class="panel-body stat-content">
                  <el-progress
                    type="dashboard"
                    :width="110"
                    :stroke-width="10"
                    :percentage="clampPercent(systemStats.disk_percent)"
                    :color="percentColor(systemStats.disk_percent)"
                  />
                  <div class="stat-desc">
                    {{ systemStats.disk_percent.toFixed(1) }}% ·
                    剩余 {{ formatMb(systemStats.disk_free_mb) }}
                  </div>
                </div>
              </div>
              <!-- 4 chart panels -->
              <div
                v-else-if="findPanel(item.i)"
                class="panel-wrapper chart-panel"
                @pointerdown="onPanelPointerDown('overview', $event)"
                @pointerup="onPanelPointerUp"
                @pointerleave="onPanelPointerUp"
                @pointercancel="onPanelPointerUp"
              >
                <div class="panel-header">
                  <span class="panel-title">{{ findPanel(item.i)?.title }}</span>
                  <div class="panel-toolbar" @pointerdown.stop>
                    <el-select
                      v-model="findPanel(item.i).timeRange"
                      size="small"
                      class="toolbar-select"
                      @change="onChartParamsChange(item.i)"
                    >
                      <el-option
                        v-for="opt in TIME_RANGE_OPTIONS"
                        :key="opt.value"
                        :label="opt.label"
                        :value="opt.value"
                      />
                    </el-select>
                    <el-select
                      v-model="findPanel(item.i).step"
                      size="small"
                      class="toolbar-select"
                      @change="onChartParamsChange(item.i)"
                    >
                      <el-option
                        v-for="opt in getSafeStepOptions(findPanel(item.i).timeRange)"
                        :key="opt.value"
                        :label="opt.label"
                        :value="opt.value"
                      />
                    </el-select>
                    <el-button
                      size="small"
                      :icon="FullScreen"
                      circle
                      @click="toggleFullscreen(item.i)"
                    />
                  </div>
                </div>
                <div class="panel-body chart-body">
                  <v-chart
                    class="chart"
                    :option="findPanel(item.i).option"
                    :autoresize="true"
                  />
                </div>
              </div>
              <!-- Alert panel -->
              <div
                v-else-if="item.i === 'panel-alerts'"
                class="panel-wrapper alert-panel"
                @pointerdown="onPanelPointerDown('overview', $event)"
                @pointerup="onPanelPointerUp"
                @pointerleave="onPanelPointerUp"
                @pointercancel="onPanelPointerUp"
              >
                <div class="panel-header">
                  <span class="panel-title">告警信息</span>
                  <div class="panel-toolbar" @pointerdown.stop>
                    <el-tag v-if="activeAlertCount > 0" type="danger" size="small">
                      {{ activeAlertCount }} 条活跃 / 共 {{ alerts.length }} 条
                    </el-tag>
                    <el-tag v-else-if="alerts.length > 0" type="info" size="small">
                      共 {{ alerts.length }} 条历史告警
                    </el-tag>
                    <el-tag v-else type="success" size="small">无告警</el-tag>
                  </div>
                </div>
                <div class="panel-body alerts-body alerts-body-pagetable">
                  <PageTable
                    ref="alertsOverviewTableRef"
                    :fetch-data="fetchAlertsTable"
                    search-placeholder="全局搜索：告警名称 / 实例 / 描述 …"
                    :default-page-size="10"
                    :page-size-options="[
                      { label: '10 条/页', value: 10 },
                      { label: '20 条/页', value: 20 },
                      { label: '50 条/页', value: 50 }
                    ]"
                  >
                    <filterable-table-column
                      prop="alertname"
                      label="告警名称"
                      class-name="left-column" sortable="custom" label-class-name="col-nowrap"
                    >
                      <template #default="scope">
                        <el-icon class="alert-icon"><Warning /></el-icon>
                        <span>{{ scope.row.alertname }}</span>
                      </template>
                    </filterable-table-column>
                    <filterable-table-column
                      prop="severity"
                      label="级别"
                      width="140"
                      class-name="center-column"
                      sortable="custom"
                      label-class-name="col-nowrap"
                    >
                      <template #default="scope">
                        <el-tag :type="getSeverityType(scope.row.severity)" size="small">
                          {{ scope.row.severity }}
                        </el-tag>
                      </template>
                    </filterable-table-column>
                    <filterable-table-column
                      prop="status"
                      label="状态"
                      width="100"
                      class-name="center-column"
                      sortable="custom"
                      label-class-name="col-nowrap"
                    >
                      <template #default="scope">
                        <el-tag :type="getStatusType(scope.row.status)" size="small">
                          {{ scope.row.status }}
                        </el-tag>
                      </template>
                    </filterable-table-column>
                    <filterable-table-column
                      prop="instance"
                      label="实例"
                      class-name="left-column" sortable="custom" label-class-name="col-nowrap"
                    />
                    <filterable-table-column
                      prop="startsAt"
                      label="开始时间"
                      width="160"
                      class-name="center-column"
                      sortable="custom"
                      label-class-name="col-nowrap"
                    />
                    <filterable-table-column
                      prop="endsAt"
                      label="结束时间"
                      width="160"
                      class-name="center-column"
                      sortable="custom"
                      label-class-name="col-nowrap"
                    />
                    <filterable-table-column
                      prop="summary"
                      label="描述"
                      class-name="left-column" sortable="custom" label-class-name="col-nowrap"
                    />
                  </PageTable>
                </div>
              </div>
            </GridItem>
          </GridLayout>
        </div>
      </el-tab-pane>

      <!-- ==================== Tab 3: 监控指标 ==================== -->
      <el-tab-pane label="监控指标" name="metrics">
        <!-- 编辑模式提示 -->
        <div v-if="isMetricsEditMode" class="edit-mode-tip">
          <el-alert type="info" :closable="false" show-icon>
            <template #title>
              编辑模式已开启：可拖动 / 调整面板大小。点击右上角"完成"退出。
            </template>
          </el-alert>
          <el-button
            size="small"
            class="edit-mode-reset-btn"
            @click="resetLayout('metrics')"
          >
            重置布局
          </el-button>
          <el-button
            size="small"
            type="primary"
            class="edit-mode-done-btn"
            @click="exitEditMode('metrics')"
          >
            完成
          </el-button>
        </div>
        <GridLayout
          v-model:layout="metricsLayout"
          :col-num="12"
          :row-height="30"
          :is-draggable="isMetricsEditMode"
          :is-resizable="isMetricsEditMode"
          :vertical-compact="true"
          :use-css-transforms="true"
          :margin="[8, 8]"
        >
          <GridItem
            v-for="item in metricsLayout"
            :key="item.i"
            :x="item.x"
            :y="item.y"
            :w="item.w"
            :h="item.h"
            :i="item.i"
            :min-w="3"
            :min-h="4"
            drag-allow-from=".panel-header"
            class="chart-grid-item"
            :class="{ 'is-edit-mode': isMetricsEditMode }"
          >
            <!-- Gauge cards -->
            <div
              v-if="item.i === 'gauge-cpu'"
              class="panel-wrapper stat-panel gauge-panel"
              @pointerdown="onPanelPointerDown('metrics', $event)"
              @pointerup="onPanelPointerUp"
              @pointerleave="onPanelPointerUp"
              @pointercancel="onPanelPointerUp"
            >
              <div class="panel-header">
                <span class="panel-title">节点CPU总使用率</span>
              </div>
              <div class="panel-body stat-content">
                <el-progress
                  type="dashboard"
                  :width="100"
                  :stroke-width="9"
                  :percentage="clampPercent(systemStats.host_cpu_percent)"
                  :color="percentColor(systemStats.host_cpu_percent)"
                />
                <div class="stat-desc">
                  {{ systemStats.host_cpu_percent.toFixed(1) }}% ·
                  {{ systemStats.cpu_count }} 核
                </div>
              </div>
            </div>
            <div
              v-else-if="item.i === 'gauge-mem'"
              class="panel-wrapper stat-panel gauge-panel"
              @pointerdown="onPanelPointerDown('metrics', $event)"
              @pointerup="onPanelPointerUp"
              @pointerleave="onPanelPointerUp"
              @pointercancel="onPanelPointerUp"
            >
              <div class="panel-header">
                <span class="panel-title">节点内存总使用率</span>
              </div>
              <div class="panel-body stat-content">
                <el-progress
                  type="dashboard"
                  :width="100"
                  :stroke-width="9"
                  :percentage="clampPercent(systemStats.mem_percent)"
                  :color="percentColor(systemStats.mem_percent)"
                />
                <div class="stat-desc">
                  {{ systemStats.mem_percent.toFixed(1) }}% ·
                  共 {{ formatMb(systemStats.mem_total_mb) }}
                </div>
              </div>
            </div>
            <div
              v-else-if="item.i === 'gauge-disk'"
              class="panel-wrapper stat-panel gauge-panel"
              @pointerdown="onPanelPointerDown('metrics', $event)"
              @pointerup="onPanelPointerUp"
              @pointerleave="onPanelPointerUp"
              @pointercancel="onPanelPointerUp"
            >
              <div class="panel-header">
                <span class="panel-title">磁盘总使用率</span>
              </div>
              <div class="panel-body stat-content">
                <el-progress
                  type="dashboard"
                  :width="100"
                  :stroke-width="9"
                  :percentage="clampPercent(systemStats.disk_percent)"
                  :color="percentColor(systemStats.disk_percent)"
                />
                <div class="stat-desc">
                  {{ systemStats.disk_percent.toFixed(1) }}% ·
                  剩余 {{ formatMb(systemStats.disk_free_mb) }}
                </div>
              </div>
            </div>
            <!-- Chart panels -->
            <div
              v-else
              class="panel-wrapper chart-panel"
              @pointerdown="onPanelPointerDown('metrics', $event)"
              @pointerup="onPanelPointerUp"
              @pointerleave="onPanelPointerUp"
              @pointercancel="onPanelPointerUp"
            >
              <div class="panel-header">
                <span class="panel-title">{{ findPanel(item.i)?.title }}</span>
                <div class="panel-toolbar" @pointerdown.stop>
                  <template v-if="findPanel(item.i)">
                    <el-select
                      v-model="findPanel(item.i).timeRange"
                      size="small"
                      class="toolbar-select"
                      @change="onChartParamsChange(item.i)"
                    >
                      <el-option
                        v-for="opt in TIME_RANGE_OPTIONS"
                        :key="opt.value"
                        :label="opt.label"
                        :value="opt.value"
                      />
                    </el-select>
                    <el-select
                      v-model="findPanel(item.i).step"
                      size="small"
                      class="toolbar-select"
                      @change="onChartParamsChange(item.i)"
                    >
                      <el-option
                        v-for="opt in getSafeStepOptions(findPanel(item.i).timeRange)"
                        :key="opt.value"
                        :label="opt.label"
                        :value="opt.value"
                      />
                    </el-select>
                    <el-button
                      size="small"
                      :icon="FullScreen"
                      circle
                      @click="toggleFullscreen(item.i)"
                    />
                  </template>
                </div>
              </div>
              <div class="panel-body chart-body">
                <v-chart
                  v-if="findPanel(item.i)"
                  class="chart"
                  :option="findPanel(item.i).option"
                  :autoresize="true"
                />
              </div>
            </div>
          </GridItem>
        </GridLayout>
      </el-tab-pane>

      <!-- ==================== Tab 3: 告警 ==================== -->
      <el-tab-pane label="告警" name="alerts">
        <div class="panel-wrapper alert-panel alert-panel-pagetable">
          <PageTable
            ref="alertsTableRef"
            :fetch-data="fetchAlertsTable"
            search-placeholder="全局搜索：告警名称 / 实例 / 描述 …"
            :default-page-size="20"
          >
            <template #toolbar-actions>
              <el-tag v-if="activeAlertCount > 0" type="danger" size="small">
                {{ activeAlertCount }} 条活跃 / 共 {{ alerts.length }} 条
              </el-tag>
              <el-tag v-else-if="alerts.length > 0" type="info" size="small">
                共 {{ alerts.length }} 条历史告警
              </el-tag>
              <el-tag v-else type="success" size="small">无告警</el-tag>
            </template>
            <filterable-table-column
              prop="alertname"
              label="告警名称"
              class-name="left-column" sortable="custom" label-class-name="col-nowrap"
            >
              <template #default="scope">
                <el-icon class="alert-icon"><Warning /></el-icon>
                <span>{{ scope.row.alertname }}</span>
              </template>
            </filterable-table-column>
            <filterable-table-column
              prop="severity"
              label="级别"
              width="140"
              class-name="center-column"
              sortable="custom"
              label-class-name="col-nowrap"
            >
              <template #default="scope">
                <el-tag :type="getSeverityType(scope.row.severity)" size="small">
                  {{ scope.row.severity }}
                </el-tag>
              </template>
            </filterable-table-column>
            <filterable-table-column
              prop="status"
              label="状态"
              width="100"
              class-name="center-column"
              sortable="custom"
              label-class-name="col-nowrap"
            >
              <template #default="scope">
                <el-tag :type="getStatusType(scope.row.status)" size="small">
                  {{ scope.row.status }}
                </el-tag>
              </template>
            </filterable-table-column>
            <filterable-table-column
              prop="instance"
              label="实例"
              class-name="left-column" sortable="custom" label-class-name="col-nowrap"
            />
            <filterable-table-column
              prop="startsAt"
              label="开始时间"
              width="160"
              class-name="center-column"
              sortable="custom"
              label-class-name="col-nowrap"
            />
            <filterable-table-column
              prop="endsAt"
              label="结束时间"
              width="160"
              class-name="center-column"
              sortable="custom"
              label-class-name="col-nowrap"
            />
            <filterable-table-column
              prop="summary"
              label="描述"
              class-name="left-column" sortable="custom" label-class-name="col-nowrap"
            />
          </PageTable>
        </div>
      </el-tab-pane>

      <!-- ==================== Tab 5: 日志 ==================== -->
      <el-tab-pane label="日志" name="logs">
        <div class="panel-wrapper logs-panel">
          <div class="panel-header">
            <span class="panel-title">日志</span>
          </div>
          <div class="panel-body logs-body">
            <el-empty description="开发中" />
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- 全屏对话框 -->
    <el-dialog
      v-model="fullscreenVisible"
      :title="fullscreenTitle"
      fullscreen
      destroy-on-close
      append-to-body
    >
      <div class="fullscreen-wrapper">
        <div v-if="fullscreenPanel" class="fullscreen-toolbar">
          <el-select
            v-model="fullscreenPanel.timeRange"
            size="small"
            class="toolbar-select"
            @change="onChartParamsChange(fullscreenPanel.id)"
          >
            <el-option
              v-for="opt in TIME_RANGE_OPTIONS"
              :key="opt.value"
              :label="opt.label"
              :value="opt.value"
            />
          </el-select>
          <el-select
            v-model="fullscreenPanel.step"
            size="small"
            class="toolbar-select"
            @change="onChartParamsChange(fullscreenPanel.id)"
          >
            <el-option
              v-for="opt in getSafeStepOptions(fullscreenPanel.timeRange)"
              :key="opt.value"
              :label="opt.label"
              :value="opt.value"
            />
          </el-select>
        </div>
        <div class="fullscreen-chart-container">
          <v-chart
            v-if="currentFullscreenOption"
            class="chart-fullscreen"
            :option="currentFullscreenOption"
            :autoresize="true"
          />
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script>
import { markRaw } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Warning, FullScreen, Loading } from '@element-plus/icons-vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, PieChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent
} from 'echarts/components'
import { GridLayout, GridItem } from 'grid-layout-plus'

use([
  CanvasRenderer,
  LineChart,
  PieChart,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent
])

import {
  getSystemHealth,
  getJobStats,
  getApiStats,
  getSystemStats
} from '@/api/system'
import {
  queryPrometheus,
  queryPrometheusRange,
  getAlerts,
  extractLatestValue,
  extractMultiTimeSeries,
  formatAlerts,
  PROMQL
} from '@/api/monitor'
import RefreshInterval from '@/components/RefreshInterval/index.vue'
import PageTable from '@/components/PageTable/index.vue'
import FilterableTableColumn from '@/components/PageTable/FilterableTableColumn.vue'
import { useConfigStore } from '@/store/modules/config'

// Chart color palette. The first four entries match the job status tag
// colors used in the job list page (see webui/src/common/library.js
// getJobStatusTag), so the charts and the job table tell the same story:
//   running  → green   (#67c23a)
//   queued   → orange  (#e6a23c)
//   failed   → red     (#f56c6c)
//   completed→ blue    (#409eff)
//   other    → grey    (#909399)
const CHART_COLORS = ['#409eff', '#67c23a', '#e6a23c', '#f56c6c', '#909399', '#b37feb']

// Status-aware color map for the "作业统计趋势" / "作业状态分布" charts,
// aligned with the tag colors used in the job list page.
const JOB_STATUS_COLORS = {
  total: '#909399',
  completed: '#409eff',
  failed: '#f56c6c',
  running: '#67c23a',
  queued: '#e6a23c',
  cancelling: '#909399',
  cancelled: '#909399'
}

// 时间范围选项（秒）
const TIME_RANGE_OPTIONS = [
  { label: '近 15 分钟', value: 15 * 60 },
  { label: '近 1 小时', value: 60 * 60 },
  { label: '近 6 小时', value: 6 * 60 * 60 },
  { label: '近 24 小时', value: 24 * 60 * 60 },
  { label: '近 7 天', value: 7 * 24 * 60 * 60 },
  { label: '近 30 天', value: 30 * 24 * 60 * 60 }
]

// 采样周期选项（Prometheus step 参数）
// value 为 Prometheus duration 字符串，seconds 用于内部计算
const STEP_OPTIONS = [
  { label: '按分钟', value: '60s', seconds: 60 },
  { label: '按 5 分钟', value: '5m', seconds: 5 * 60 },
  { label: '按小时', value: '1h', seconds: 60 * 60 },
  { label: '按天', value: '1d', seconds: 24 * 60 * 60 },
  { label: '按周', value: '1w', seconds: 7 * 24 * 60 * 60 }
]

// Prometheus query_range 单次查询最大数据点数（硬编码限制）
const PROMETHEUS_MAX_POINTS = 11000

/**
 * 根据时间范围（秒）计算最小安全 step 秒数
 * @param {number} timeRange - 时间范围（秒）
 * @returns {number} 最小安全 step 秒数
 */
function getMinSafeStepSeconds(timeRange) {
  return Math.ceil(timeRange / PROMETHEUS_MAX_POINTS)
}

/**
 * 根据时间范围过滤出安全的 step 选项
 * @param {number} timeRange - 时间范围（秒）
 * @returns {Array} 过滤后的 step 选项
 */
function filterSafeStepOptions(timeRange) {
  const minSeconds = getMinSafeStepSeconds(timeRange)
  return STEP_OPTIONS.filter(opt => opt.seconds >= minSeconds)
}

/**
 * 获取指定时间范围下最接近且不小于 minSafe 的 step 选项
 * @param {number} timeRange - 时间范围（秒）
 * @returns {object} 安全的 step 选项
 */
function getDefaultSafeStepOption(timeRange) {
  const safeOptions = filterSafeStepOptions(timeRange)
  // 返回第一个安全选项（即最小安全步长）
  return safeOptions[0] || STEP_OPTIONS[STEP_OPTIONS.length - 1]
}

// 默认每个图表面板的查询参数
const DEFAULT_CHART_PARAMS = {
  timeRange: 60 * 60, // 近 1 小时
  step: '60s'
}

export default {
  name: 'MonitorCenter',
  components: {
    RefreshInterval,
    VChart,
    Warning,
    FullScreen,
    Loading,
    GridLayout,
    GridItem,
    PageTable,
    FilterableTableColumn
  },
  data() {
    return {
      FullScreen: markRaw(FullScreen),
      activeTab: 'overview',
      // Endpoint switcher in the overview toolbar (mirrors the sidebar
      // "当前系统" selector; the active endpoint drives every API call
      // on this page).
      bigscreenEndpointName: '',
      // True while the overview bigscreen is in browser-native fullscreen
      // (tracked via fullscreenchange so the button label / endpoint
      // selector can react even if the user pressed ESC to exit).
      isBigscreenFullscreen: false,
      loading: false,
      alertsLoading: false,
      systemHealthy: false,
      jobStats: {
        total: 0,
        running: 0,
        queued: 0,
        completed: 0,
        failed: 0,
        submittedRate: 0,
        completedRate: 0
      },
      apiStats: {
        inProgress: 0,
        totalRequests: 0
      },
      systemStats: {
        host_cpu_percent: 0,
        cpu_count: 0,
        mem_percent: 0,
        mem_total_mb: 0,
        disk_percent: 0,
        disk_free_mb: 0,
        disk_total_mb: 0
      },
      alerts: [],
      // 图表面板配置（每个面板有独立的查询参数）
      chartPanels: [
        {
          id: 'chart-job-trend',
          title: '作业统计趋势',
          ref: 'jobTrendChart',
          option: {},
          ...JSON.parse(JSON.stringify(DEFAULT_CHART_PARAMS))
        },
        {
          id: 'chart-api-rate',
          title: 'API 请求速率',
          ref: 'apiRateChart',
          option: {},
          ...JSON.parse(JSON.stringify(DEFAULT_CHART_PARAMS))
        },
        {
          id: 'chart-api-duration',
          title: 'API 响应时长 (P50/P95)',
          ref: 'apiDurationChart',
          option: {},
          ...JSON.parse(JSON.stringify(DEFAULT_CHART_PARAMS))
        },
        {
          id: 'chart-job-status',
          title: '作业状态分布',
          ref: 'jobStatusChart',
          option: {},
          ...JSON.parse(JSON.stringify(DEFAULT_CHART_PARAMS))
        }
      ],
      TIME_RANGE_OPTIONS,
      // 全屏
      fullscreenVisible: false,
      fullscreenChart: '',
      fullscreenTitle: '',
      // Metrics tab grid layout: 3 gauge cards (top row) + 4 charts (2x2)
      metricsLayout: [
        { i: 'gauge-cpu', x: 0, y: 0, w: 4, h: 5 },
        { i: 'gauge-mem', x: 4, y: 0, w: 4, h: 5 },
        { i: 'gauge-disk', x: 8, y: 0, w: 4, h: 5 },
        { i: 'chart-job-trend', x: 0, y: 5, w: 6, h: 12 },
        { i: 'chart-api-rate', x: 6, y: 5, w: 6, h: 12 },
        { i: 'chart-api-duration', x: 0, y: 17, w: 6, h: 12 },
        { i: 'chart-job-status', x: 6, y: 17, w: 6, h: 12 }
      ],
      // Overview tab grid layout: 8 stat cards (top rows) + 3 gauges +
      // 4 charts + 1 alert. Kept compact so the whole bigscreen fits on
      // a single 1080p fullscreen page (row-height=24, margin=6).
      overviewLayout: [
        { i: 'stat-system', x: 0, y: 0, w: 3, h: 4 },
        { i: 'stat-jobs-total', x: 3, y: 0, w: 3, h: 4 },
        { i: 'stat-jobs-running', x: 6, y: 0, w: 3, h: 4 },
        { i: 'stat-jobs-queued', x: 9, y: 0, w: 3, h: 4 },
        { i: 'stat-jobs-completed', x: 0, y: 4, w: 3, h: 4 },
        { i: 'stat-jobs-failed', x: 3, y: 4, w: 3, h: 4 },
        { i: 'stat-api-requests', x: 6, y: 4, w: 3, h: 4 },
        { i: 'stat-api-progress', x: 9, y: 4, w: 3, h: 4 },
        { i: 'gauge-cpu', x: 0, y: 8, w: 4, h: 7 },
        { i: 'gauge-mem', x: 4, y: 8, w: 4, h: 7 },
        { i: 'gauge-disk', x: 8, y: 8, w: 4, h: 7 },
        { i: 'chart-job-trend', x: 0, y: 15, w: 3, h: 9 },
        { i: 'chart-api-rate', x: 3, y: 15, w: 3, h: 9 },
        { i: 'chart-api-duration', x: 6, y: 15, w: 3, h: 9 },
        { i: 'chart-job-status', x: 9, y: 15, w: 3, h: 9 },
        { i: 'panel-alerts', x: 0, y: 24, w: 12, h: 14 }
      ],
      // Edit-mode flags (long-press to enter, "完成" to exit).
      // Each tab tracks its own edit-mode state so switching tabs doesn't
      // accidentally leave the other tab in edit mode.
      isOverviewEditMode: false,
      isMetricsEditMode: false,
      _longPressTimer: null,
      _longPressDuration: 600, // ms; press and hold to enter edit mode
      // Bump this whenever the default grid layout shape changes (panel
      // ids added/removed, default x/y/w/h rearranged). Saved layouts
      // whose embedded version does not match are discarded on load so
      // users always land on the current default after an upgrade.
      _layoutVersion: 4
    }
  },

  computed: {
    fullscreenPanel() {
      return (
        this.chartPanels.find(p => p.id === this.fullscreenChart) || null
      )
    },
    currentFullscreenOption() {
      return this.fullscreenPanel ? this.fullscreenPanel.option : null
    },
    // Endpoint options for the overview toolbar selector. Mirrors the
    // sidebar EndpointSwitcher: each option carries its probe status
    // (ok / fail / probing) so the dropdown can render a status dot
    // and disable broken endpoints.
    endpointOptions() {
      const cfg = useConfigStore()
      return cfg.endpoints.map(ep => {
        const h = cfg.healthMap[ep.name] || {}
        return {
          ...ep,
          status: h.status || 'probing',
          version: h.version || '',
          platformVersion: h.platformVersion || '',
          error: h.error || '',
          usable: h.status === 'ok'
        }
      })
    },
    bigscreenEndpointStatus() {
      const cfg = useConfigStore()
      const h = cfg.healthMap[this.bigscreenEndpointName] || {}
      return h.status || ''
    },
    // Alerts whose Alertmanager state is still "active" (i.e. currently
    // firing) vs the full list which also includes resolved / silenced /
    // inhibited records pulled for history display.
    activeAlertCount() {
      return this.alerts.filter(a => a.status === 'active').length
    }
  },

  mounted() {
    this.initChartOptions()
    this._loadLayout('overview')
    this._loadLayout('metrics')
    // Initialize the overview endpoint selector from the active endpoint
    // so the dropdown reflects whatever was picked in the sidebar.
    const cfg = useConfigStore()
    this.bigscreenEndpointName = cfg.activeEndpointName
    this.fetchAllData()
    this._onFullscreenChange = () => {
      this.isBigscreenFullscreen =
        document.fullscreenElement === this.$refs.bigscreenRef
    }
    document.addEventListener('fullscreenchange', this._onFullscreenChange)
  },

  beforeUnmount() {
    this._clearLongPressTimer()
    if (this._onFullscreenChange) {
      document.removeEventListener('fullscreenchange', this._onFullscreenChange)
      this._onFullscreenChange = null
    }
  },

  methods: {
    // ==================== 数据获取 ====================
    async fetchAllData() {
      this.loading = true
      try {
        await Promise.all([
          this.fetchSystemHealth(),
          this.fetchJobStats(),
          this.fetchApiStats(),
          this.fetchSystemStats(),
          this.fetchAlerts()
        ])
        // Fetch chart data for every chart panel using its own params
        await Promise.all(
          this.chartPanels.map(p => this.fetchChartDataById(p.id))
        )
      } finally {
        this.loading = false
      }
    },

    async fetchSystemHealth() {
      try {
        const response = await getSystemHealth()
        if (!response.error) {
          this.systemHealthy = response.result?.system_healthy || false
        }
      } catch (error) {
        console.error('获取系统健康状态失败:', error)
      }
    },

    async fetchJobStats() {
      try {
        const [total, running, queued, completed, failed, submittedRate, completedRate] = await Promise.all([
          queryPrometheus(PROMQL.jobTotal).then(extractLatestValue).catch(() => null),
          queryPrometheus(PROMQL.jobRunning).then(extractLatestValue).catch(() => null),
          queryPrometheus(PROMQL.jobQueued).then(extractLatestValue).catch(() => null),
          queryPrometheus(PROMQL.jobCompleted).then(extractLatestValue).catch(() => null),
          queryPrometheus(PROMQL.jobFailed).then(extractLatestValue).catch(() => null),
          queryPrometheus(PROMQL.jobSubmittedRate).then(extractLatestValue).catch(() => null),
          queryPrometheus(PROMQL.jobCompletedRate).then(extractLatestValue).catch(() => null)
        ])

        if (total !== null) {
          this.jobStats.total = Math.round(total)
          this.jobStats.running = Math.round(running || 0)
          this.jobStats.queued = Math.round(queued || 0)
          this.jobStats.completed = Math.round(completed || 0)
          this.jobStats.failed = Math.round(failed || 0)
          this.jobStats.submittedRate = parseFloat((submittedRate || 0).toFixed(2))
          this.jobStats.completedRate = parseFloat((completedRate || 0).toFixed(2))
        } else {
          const response = await getJobStats()
          if (!response.error) {
            const r = response.result
            this.jobStats.total = r.total || 0
            this.jobStats.running = r.running || 0
            this.jobStats.queued = r.queued || 0
            this.jobStats.completed = r.completed || 0
            this.jobStats.failed = r.failed || 0
            this.jobStats.submittedRate = r.submitted_job_rate_min || 0
            this.jobStats.completedRate = r.completed_job_rate_min || 0
          }
        }
      } catch (error) {
        console.error('获取作业统计失败:', error)
      }
    },

    async fetchApiStats() {
      try {
        const [inProgress, totalRequests] = await Promise.all([
          queryPrometheus(PROMQL.apiInProgress).then(extractLatestValue).catch(() => null),
          queryPrometheus('sum(api_requests_total) or vector(0)').then(extractLatestValue).catch(() => null)
        ])

        if (inProgress !== null || totalRequests !== null) {
          this.apiStats.inProgress = Math.round(inProgress || 0)
          this.apiStats.totalRequests = Math.round(totalRequests || 0)
        } else {
          const response = await getApiStats()
          if (!response.error) {
            this.apiStats.totalRequests = response.result?.total_requests || 0
            this.apiStats.inProgress = response.result?.requests_in_progress || 0
          }
        }
      } catch (error) {
        console.error('获取 API 统计失败:', error)
      }
    },

    async fetchSystemStats() {
      try {
        const response = await getSystemStats()
        if (!response.error && response.result) {
          const r = response.result
          this.systemStats.host_cpu_percent = r.host_cpu_percent || 0
          this.systemStats.cpu_count = r.cpu_count || 0
          this.systemStats.mem_percent = r.mem_percent || 0
          this.systemStats.mem_total_mb = r.mem_total_mb || 0
          this.systemStats.disk_percent = r.disk_percent || 0
          this.systemStats.disk_free_mb = r.disk_free_mb || 0
          this.systemStats.disk_total_mb = r.disk_total_mb || 0
        }
      } catch (error) {
        console.error('获取系统资源失败:', error)
      }
    },

    async fetchAlerts() {
      this.alertsLoading = true
      try {
        // Pull every alert Alertmanager still knows about: active (firing),
        // resolved-but-not-yet-expired, silenced, inhibited. Without these
        // flags the endpoint only returns `active=true` and the table would
        // hide historical / recently-resolved alerts the user wants to see.
        const response = await getAlerts({
          active: true,
          silenced: true,
          inhibited: true,
          unprocessed: true
        })
        if (response && Array.isArray(response)) {
          this.alerts = formatAlerts(response)
        } else if (response && response.status === 'success' && Array.isArray(response.data)) {
          this.alerts = formatAlerts(response.data)
        } else {
          this.alerts = []
        }
      } catch (error) {
        console.error('获取告警信息失败:', error)
        this.alerts = []
      } finally {
        this.alertsLoading = false
        // If the alerts tab is showing a PageTable instance, force it to
        // re-pull (its fetch callback reads this.alerts, so a silent
        // background refresh would otherwise leave the table stale).
        // Defer via nextTick so we don't re-enter the table's fetcher
        // while the previous fetch is still resolving.
        this.$nextTick(() => {
          // Refresh both alerts tables (the standalone alerts tab and the
          // overview-tab embedded panel). They share `this.alerts`, so a
          // silent background refresh would otherwise leave either stale.
          // We call refresh() unconditionally — even before the table's
          // first load completes — because the table may have already
          // rendered an empty list from an empty cache, and we want it to
          // re-pull now that this.alerts is populated.
          for (const key of ['alertsTableRef', 'alertsOverviewTableRef']) {
            const t = this.$refs[key]
            if (t && typeof t.refresh === 'function') {
              t.refresh()
            }
          }
        })
      }
    },

    /**
     * PageTable fetch callback for the alerts tab. Alertmanager does not
     * support server-side filter/search/sort, so we apply everything
     * client-side against the cached `this.alerts` array (already pulled
     * by fetchAlerts()). Params come from PageTable:
     *   { page, page_size, search, filters, sort }
     */
    async fetchAlertsTable(params) {
      // Pull the latest alerts directly here instead of relying on the
      // this.alerts cache. The two PageTable instances (overview grid
      // + alerts tab) would otherwise race with the periodic
      // fetchAlerts() triggered by the refresh-interval timer, and one
      // of them ends up rendering an empty list because the cache was
      // empty at mount time.
      let raw = []
      try {
        const response = await getAlerts({
          active: true,
          silenced: true,
          inhibited: true,
          unprocessed: true
        })
        if (response && Array.isArray(response)) {
          raw = formatAlerts(response)
        } else if (response && response.status === 'success' && Array.isArray(response.data)) {
          raw = formatAlerts(response.data)
        }
      } catch (e) {
        console.error('fetchAlertsTable failed:', e)
        raw = []
      }
      // Keep the shared cache in sync so the badge counters in the
      // parent component (activeAlertCount etc.) still see fresh data.
      this.alerts = raw
      let rows = raw.slice()

      // Global search across alertname / instance / summary / severity /
      // status (case-insensitive substring).
      const kw = (params.search || '').trim().toLowerCase()
      if (kw) {
        rows = rows.filter(r => {
          return (
            (r.alertname || '').toLowerCase().includes(kw) ||
            (r.instance || '').toLowerCase().includes(kw) ||
            (r.summary || '').toLowerCase().includes(kw) ||
            (r.severity || '').toLowerCase().includes(kw) ||
            (r.status || '').toLowerCase().includes(kw)
          )
        })
      }

      // Per-column filters (substring, case-insensitive).
      const filters = params.filters || {}
      for (const key of Object.keys(filters)) {
        const v = String(filters[key] || '').trim().toLowerCase()
        if (!v) continue
        rows = rows.filter(r =>
          String(r[key] || '').toLowerCase().includes(v)
        )
      }

      // Sort: PageTable emits ["-field"] for desc, ["field"] for asc.
      if (Array.isArray(params.sort) && params.sort.length > 0) {
        const f = params.sort[0]
        const desc = f.startsWith('-')
        const prop = desc ? f.slice(1) : f
        rows.sort((a, b) => {
          const va = a[prop] || ''
          const vb = b[prop] || ''
          if (va === vb) return 0
          const cmp = va < vb ? -1 : 1
          return desc ? -cmp : cmp
        })
      }

      const total = rows.length
      const page = params.page || 1
      const size = params.page_size || 20
      const start = (page - 1) * size
      const items = rows.slice(start, start + size)
      return { result: { items, total } }
    },

    // ==================== 图表配置 ====================
    getBaseChartOption(title, yAxisName = '') {
      return {
        title: { show: false },
        tooltip: {
          trigger: 'axis',
          axisPointer: { type: 'cross' }
        },
        legend: {
          bottom: 0,
          data: [],
          textStyle: { fontSize: 10 },
          itemWidth: 12,
          itemHeight: 8,
          itemGap: 6
        },
        grid: {
          left: '3%',
          right: '4%',
          bottom: '15%',
          top: '8%',
          containLabel: true
        },
        xAxis: {
          type: 'time',
          splitLine: { show: false },
          axisLabel: { fontSize: 10 }
        },
        yAxis: {
          type: 'value',
          name: yAxisName,
          nameTextStyle: { fontSize: 10 },
          axisLabel: { fontSize: 10 },
          splitLine: { lineStyle: { type: 'dashed' } }
        },
        series: []
      }
    },

    /**
     * Build a pie (donut) chart option for the job status distribution panel.
     * Shows an empty placeholder when there is no data.
     * @param {Array} pieData - [{ name, value }, ...]
     * @returns {object} ECharts option
     */
    buildPieChartOption(pieData) {
      const hasData = Array.isArray(pieData) && pieData.length > 0
      return {
        title: hasData
          ? { show: false }
          : {
              text: '暂无数据',
              left: 'center',
              top: 'center',
              textStyle: {
                color: '#909399',
                fontSize: 14,
                fontWeight: 'normal'
              }
            },
        tooltip: {
          trigger: 'item',
          formatter: '{b}: {c} ({d}%)'
        },
        legend: {
          bottom: 0,
          data: hasData ? pieData.map(d => d.name) : [],
          textStyle: { fontSize: 10 },
          itemWidth: 12,
          itemHeight: 8,
          itemGap: 6
        },
        series: [
          {
            name: '作业状态分布',
            type: 'pie',
            radius: ['40%', '65%'],
            center: ['50%', '45%'],
            avoidLabelOverlap: true,
            itemStyle: {
              borderRadius: 6,
              borderColor: '#fff',
              borderWidth: 2
            },
            label: {
              formatter: '{b}: {c}',
              fontSize: 10
            },
            emphasis: {
              label: { show: true, fontWeight: 'bold' }
            },
            color: hasData
              ? pieData.map(d => JOB_STATUS_COLORS[d.key] || CHART_COLORS[0])
              : CHART_COLORS,
            data: hasData ? pieData : []
          }
        ]
      }
    },

    initChartOptions() {
      for (const panel of this.chartPanels) {
        if (panel.id === 'chart-job-status') {
          panel.option = this.buildPieChartOption([])
        } else {
          panel.option = this.getBaseChartOption(panel.title)
        }
      }
    },

    findPanel(id) {
      return this.chartPanels.find(p => p.id === id)
    },

    /**
     * 根据时间范围获取安全的 step 选项列表（暴露给模板使用）
     * @param {number} timeRange - 时间范围（秒）
     * @returns {Array} 安全的 step 选项
     */
    getSafeStepOptions(timeRange) {
      return filterSafeStepOptions(timeRange)
    },

    onChartParamsChange(id) {
      const panel = this.findPanel(id)
      if (!panel) return
      // 当时间范围变化时，若当前 step 已不安全，自动调整为最近合法档位
      const minSafeSeconds = getMinSafeStepSeconds(panel.timeRange)
      const currentStepOption = STEP_OPTIONS.find(opt => opt.value === panel.step)
      const currentStepSeconds = currentStepOption ? currentStepOption.seconds : 60
      if (currentStepSeconds < minSafeSeconds) {
        const safeOption = getDefaultSafeStepOption(panel.timeRange)
        panel.step = safeOption.value
        ElMessage.warning(
          `时间范围过大，采样周期已自动调整为「${safeOption.label}」以避免超出 Prometheus 单次查询点数限制`
        )
      }
      this.fetchChartDataById(id)
    },

    async fetchChartDataById(id) {
      const panel = this.findPanel(id)
      if (!panel) return
      const end = Math.floor(Date.now() / 1000)
      const start = end - panel.timeRange
      const step = panel.step

      // 兜底校验：确保 step 不会导致数据点超限
      const minSafeSeconds = getMinSafeStepSeconds(panel.timeRange)
      const stepOption = STEP_OPTIONS.find(opt => opt.value === step)
      const stepSeconds = stepOption ? stepOption.seconds : 60
      if (stepSeconds < minSafeSeconds) {
        const safeOption = getDefaultSafeStepOption(panel.timeRange)
        panel.step = safeOption.value
        ElMessage.warning(
          `采样周期过细，已自动调整为「${safeOption.label}」以避免超出 Prometheus 单次查询点数限制`
        )
        // 使用调整后的 step 重新发起查询
        this.fetchChartDataById(id)
        return
      }

      switch (id) {
        case 'chart-job-trend':
          await this.fetchJobTrendData(panel, start, end, step)
          break
        case 'chart-api-rate':
          await this.fetchApiRateData(panel, start, end, step)
          break
        case 'chart-api-duration':
          await this.fetchApiDurationData(panel, start, end, step)
          break
        case 'chart-job-status':
          await this.fetchJobStatusData(panel, start, end, step)
          break
      }
    },

    buildSeries(seriesData, colors) {
      return seriesData.map((s, i) => ({
        name: s.name,
        type: 'line',
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 2 },
        itemStyle: { color: colors[i % colors.length] },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: colors[i % colors.length] + '40' },
              { offset: 1, color: colors[i % colors.length] + '10' }
            ]
          }
        },
        data: s.data
      }))
    },

    async fetchJobTrendData(panel, start, end, step) {
      // Show ALL job statuses so the trend chart matches the pie chart
      // (and the job list page). Series colors come from JOB_STATUS_COLORS
      // keyed by status so the same status is always rendered with the
      // same color across charts and the job list tags.
      try {
        const queries = [
          { key: 'running', label: '运行中' },
          { key: 'queued', label: '队列中' },
          { key: 'completed', label: '已完成' },
          { key: 'failed', label: '失败' },
          { key: 'cancelling', label: '取消中' },
          { key: 'cancelled', label: '已取消' }
        ]
        const results = await Promise.all(
          queries.map(q =>
            queryPrometheusRange(
              `sum(job_count{status="${q.key}"})`,
              start,
              end,
              step
            )
              .then(r => extractMultiTimeSeries(r))
              .catch(() => [])
          )
        )

        const seriesData = queries.map((q, i) => ({
          name: q.label,
          data: results[i][0]?.data || []
        }))
        const colors = queries.map(q => JOB_STATUS_COLORS[q.key])

        panel.option.legend.data = seriesData.map(s => s.name)
        panel.option.series = this.buildSeries(seriesData, colors)
      } catch (error) {
        console.error('获取作业趋势数据失败:', error)
      }
    },

    async fetchApiRateData(panel, start, end, step) {
      try {
        const result = await queryPrometheusRange(PROMQL.apiRequestRate, start, end, step)
          .then(r => extractMultiTimeSeries(r))
          .catch(() => [])

        const seriesData = result.map(s => ({ name: s.name, data: s.data }))
        panel.option.legend.data = seriesData.map(s => s.name)
        panel.option.series = this.buildSeries(seriesData, CHART_COLORS)
      } catch (error) {
        console.error('获取 API 速率数据失败:', error)
      }
    },

    async fetchApiDurationData(panel, start, end, step) {
      try {
        const [p95, p50] = await Promise.all([
          queryPrometheusRange(PROMQL.apiDurationP95, start, end, step).then(r => extractMultiTimeSeries(r, 'P95')).catch(() => []),
          queryPrometheusRange(PROMQL.apiDurationP50, start, end, step).then(r => extractMultiTimeSeries(r, 'P50')).catch(() => [])
        ])

        const seriesData = [
          { name: 'P95', data: p95[0]?.data || [] },
          { name: 'P50', data: p50[0]?.data || [] }
        ]

        panel.option.legend.data = seriesData.map(s => s.name)
        panel.option.series = this.buildSeries(seriesData, ['#f56c6c', '#409eff'])
      } catch (error) {
        console.error('获取 API 时长数据失败:', error)
      }
    },

    async fetchJobStatusData(panel) {
      // Pie chart shows the CURRENT distribution, so use instant queries
      // (queryPrometheus + extractLatestValue) rather than range queries.
      try {
        const [running, queued, completed, failed, cancelling, cancelled] =
          await Promise.all([
            queryPrometheus('sum(job_count{status="running"})').then(extractLatestValue).catch(() => null),
            queryPrometheus('sum(job_count{status="queued"})').then(extractLatestValue).catch(() => null),
            queryPrometheus('sum(job_count{status="completed"})').then(extractLatestValue).catch(() => null),
            queryPrometheus('sum(job_count{status="failed"})').then(extractLatestValue).catch(() => null),
            queryPrometheus('sum(job_count{status="cancelling"})').then(extractLatestValue).catch(() => null),
            queryPrometheus('sum(job_count{status="cancelled"})').then(extractLatestValue).catch(() => null)
          ])

        // Each entry carries the raw status key so buildPieChartOption
        // can look up the matching color from JOB_STATUS_COLORS.
        const pieData = [
          { key: 'running', name: '运行中', value: Math.round(running || 0) },
          { key: 'queued', name: '队列中', value: Math.round(queued || 0) },
          { key: 'completed', name: '已完成', value: Math.round(completed || 0) },
          { key: 'failed', name: '失败', value: Math.round(failed || 0) },
          { key: 'cancelling', name: '取消中', value: Math.round(cancelling || 0) },
          { key: 'cancelled', name: '已取消', value: Math.round(cancelled || 0) }
        ].filter(item => item.value > 0)

        panel.option = this.buildPieChartOption(pieData)
      } catch (error) {
        console.error('获取作业状态分布数据失败:', error)
        panel.option = this.buildPieChartOption([])
      }
    },

    // ==================== 全屏 ====================
    toggleFullscreen(id) {
      const panel = this.findPanel(id)
      if (!panel) return
      this.fullscreenChart = id
      this.fullscreenTitle = panel.title
      this.fullscreenVisible = true
    },

    // Bigscreen tab: toggle browser-native fullscreen on the whole
    // bigscreen container so the user can put the dashboard on a
    // large TV / projector without browser chrome.
    toggleBigscreenFullscreen() {
      const el = this.$refs.bigscreenRef
      if (!el) return
      const doc = document
      if (doc.fullscreenElement) {
        doc.exitFullscreen().catch(() => {})
      } else if (el.requestFullscreen) {
        el.requestFullscreen().catch(err => {
          console.error('requestFullscreen failed:', err)
          this.$message.error('进入全屏失败')
        })
      }
    },

    // ==================== 工具方法 ====================
    clampPercent(v) {
      const n = Number(v) || 0
      return Math.min(100, Math.max(0, Math.round(n * 10) / 10))
    },

    percentColor(v) {
      const n = Number(v) || 0
      if (n >= 90) return '#f56c6c'
      if (n >= 70) return '#e6a23c'
      return '#67c23a'
    },

    formatMb(mb) {
      const n = Number(mb) || 0
      if (n >= 1024) {
        return `${(n / 1024).toFixed(1)} GB`
      }
      return `${n.toFixed(0)} MB`
    },

    getSeverityType(severity) {
      const map = {
        critical: 'danger',
        warning: 'warning',
        info: 'info'
      }
      return map[severity] || 'info'
    },

    getStatusType(status) {
      const map = {
        active: 'danger',
        resolved: 'success',
        suppressed: 'info',
        silenced: 'info',
        inhibited: 'warning',
        unprocessed: 'warning'
      }
      return map[status] || 'info'
    },

    onIntervalChange() {
      this.fetchAllData()
    },

    // ==================== 长按进入编辑模式 ====================
    // Each tab (overview / metrics) has its own GridLayout, its own
    // edit-mode flag, and its own localStorage key. All four methods
    // below take a `tab` argument ('overview' | 'metrics') so the same
    // long-press handlers can be reused across both tabs.
    onPanelPointerDown(tab, event) {
      const isEditMode = tab === 'overview'
        ? this.isOverviewEditMode
        : this.isMetricsEditMode
      if (isEditMode) return
      if (event.button !== undefined && event.button !== 0) return
      this._clearLongPressTimer()
      this._longPressTimer = setTimeout(() => {
        this.enterEditMode(tab)
      }, this._longPressDuration)
    },

    onPanelPointerUp() {
      this._clearLongPressTimer()
    },

    _clearLongPressTimer() {
      if (this._longPressTimer) {
        clearTimeout(this._longPressTimer)
        this._longPressTimer = null
      }
    },

    enterEditMode(tab) {
      if (tab === 'overview') {
        if (this.isOverviewEditMode) return
        this.isOverviewEditMode = true
      } else {
        if (this.isMetricsEditMode) return
        this.isMetricsEditMode = true
      }
      this.$message.info(
        '已进入编辑模式，可拖动 / 调整面板大小。点击"完成"退出。'
      )
    },

    exitEditMode(tab) {
      if (tab === 'overview') {
        this.isOverviewEditMode = false
      } else {
        this.isMetricsEditMode = false
      }
      this._saveLayout(tab)
      this.$message.success('布局已保存')
    },

    resetLayout(tab) {
      const defaultLayout = tab === 'overview'
        ? this._getDefaultOverviewLayout()
        : this._getDefaultMetricsLayout()
      ElMessageBox.confirm(
        '确定要将所有面板重置为默认布局吗？此操作不可撤销。',
        '重置布局',
        {
          confirmButtonText: '确定',
          cancelButtonText: '取消',
          type: 'warning'
        }
      ).then(() => {
        if (tab === 'overview') {
          this.overviewLayout = defaultLayout
        } else {
          this.metricsLayout = defaultLayout
        }
        this._saveLayout(tab)
        this.$message.success('布局已重置为默认')
      }).catch(() => {
        // User cancelled
      })
    },

    _saveLayout(tab) {
      try {
        const layout = tab === 'overview'
          ? this.overviewLayout
          : this.metricsLayout
        localStorage.setItem(
          `monitor-center-${tab}-layout`,
          JSON.stringify({ v: this._layoutVersion, layout })
        )
      } catch (e) {
        console.error('Failed to save layout:', e)
      }
    },

    _loadLayout(tab) {
      try {
        const saved = localStorage.getItem(`monitor-center-${tab}-layout`)
        if (!saved) return
        const parsed = JSON.parse(saved)
        // Accept both the legacy bare-array format and the new
        // { v, layout } envelope. Layout shape is bumped whenever the
        // default grid changes (e.g. stat cards resized, charts
        // rearranged into a single row); on mismatch the saved layout
        // is dropped so users land on the new default instead of the
        // stale one from a previous release.
        let layout = null
        if (Array.isArray(parsed)) {
          // legacy: no version tag -> treat as outdated
          layout = null
        } else if (parsed && parsed.v === this._layoutVersion && Array.isArray(parsed.layout)) {
          layout = parsed.layout
        }
        if (!layout) return
        if (tab === 'overview') {
          this.overviewLayout = layout
        } else {
          this.metricsLayout = layout
        }
      } catch (e) {
        console.error('Failed to load layout:', e)
      }
    },

    _getDefaultOverviewLayout() {
      return [
        { i: 'stat-system', x: 0, y: 0, w: 3, h: 4 },
        { i: 'stat-jobs-total', x: 3, y: 0, w: 3, h: 4 },
        { i: 'stat-jobs-running', x: 6, y: 0, w: 3, h: 4 },
        { i: 'stat-jobs-queued', x: 9, y: 0, w: 3, h: 4 },
        { i: 'stat-jobs-completed', x: 0, y: 4, w: 3, h: 4 },
        { i: 'stat-jobs-failed', x: 3, y: 4, w: 3, h: 4 },
        { i: 'stat-api-requests', x: 6, y: 4, w: 3, h: 4 },
        { i: 'stat-api-progress', x: 9, y: 4, w: 3, h: 4 },
        { i: 'gauge-cpu', x: 0, y: 8, w: 4, h: 7 },
        { i: 'gauge-mem', x: 4, y: 8, w: 4, h: 7 },
        { i: 'gauge-disk', x: 8, y: 8, w: 4, h: 7 },
        { i: 'chart-job-trend', x: 0, y: 15, w: 3, h: 9 },
        { i: 'chart-api-rate', x: 3, y: 15, w: 3, h: 9 },
        { i: 'chart-api-duration', x: 6, y: 15, w: 3, h: 9 },
        { i: 'chart-job-status', x: 9, y: 15, w: 3, h: 9 },
        { i: 'panel-alerts', x: 0, y: 24, w: 12, h: 14 }
      ]
    },

    _getDefaultMetricsLayout() {
      return [
        { i: 'gauge-cpu', x: 0, y: 0, w: 4, h: 5 },
        { i: 'gauge-mem', x: 4, y: 0, w: 4, h: 5 },
        { i: 'gauge-disk', x: 8, y: 0, w: 4, h: 5 },
        { i: 'chart-job-trend', x: 0, y: 5, w: 6, h: 12 },
        { i: 'chart-api-rate', x: 6, y: 5, w: 6, h: 12 },
        { i: 'chart-api-duration', x: 0, y: 17, w: 6, h: 12 },
        { i: 'chart-job-status', x: 6, y: 17, w: 6, h: 12 }
      ]
    }
  }
}
</script>

<style scoped>
.monitor-center-container {
  display: flex;
  flex-direction: column;
  background: var(--el-fill-color-light);
  padding: 20px;
  box-sizing: border-box;
  min-height: 100%;
}

.header {
  margin: 0;
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-bottom: 16px;
}

.header-actions {
  display: flex;
  gap: 10px;
  align-items: center;
  padding-bottom: 5px;
}

.monitor-tabs {
  flex: 1;
}

/* 通用面板 */
.panel-wrapper {
  display: flex;
  flex-direction: column;
  background: var(--el-bg-color);
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.05);
  overflow: hidden;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  border-bottom: 1px solid var(--el-border-color-light);
}

.panel-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--el-text-color-primary);
}

.panel-toolbar {
  display: flex;
  gap: 8px;
  align-items: center;
}

.toolbar-select {
  width: 92px;
}

.toolbar-select :deep(.el-select__wrapper) {
  padding: 0 8px;
  min-height: 24px;
  font-size: 12px;
}

.panel-body {
  flex: 1;
  padding: 12px;
  overflow: auto;
}

/* 总览 tab：每行 4 列网格 */
.stat-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 16px;
}

.stat-row:last-child {
  margin-bottom: 0;
}

/* 系统状态行只放一个，仍占一行 */
.stat-row:not(.stat-row-4):not(.stat-row-3) {
  grid-template-columns: 1fr;
}

/* 监控指标 tab 顶部系统资源 3 列布局 */
.stat-row-3 {
  grid-template-columns: repeat(3, 1fr);
}

.stat-panel {
  min-height: 140px;
}

.stat-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  box-sizing: border-box;
}

/* Gauge panels (CPU / memory / disk) use a fixed-size el-progress ring;
   center it vertically so any extra grid-cell height is split evenly
   above and below the content instead of leaving a blank strip at the
   bottom. The whole wrapper is forced to fill the grid cell so the
   panel-body's flex:1 actually receives the leftover height. */
.gauge-panel {
  min-height: 0 !important;
  overflow: hidden;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.gauge-panel .panel-body {
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 1 1 auto;
  padding: 4px;
  overflow: hidden;
  min-height: 0;
  height: 0; /* flex-basis trick: let flex:1 distribute the leftover height */
}

.gauge-panel .stat-content {
  height: 100%;
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.gauge-panel .stat-desc {
  margin-top: 4px;
  font-size: 12px;
  line-height: 1.3;
}

.stat-value {
  font-size: 24px;
  font-weight: 700;
  color: #409eff;
  line-height: 1.2;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
}

.stat-value.success {
  color: #67c23a;
}

.stat-value.warning {
  color: #e6a23c;
}

.stat-value.danger {
  color: #f56c6c;
}

.stat-value.primary {
  color: #409eff;
}

.stat-tag {
  font-size: 18px;
  padding: 8px 16px;
}

.stat-desc {
  margin-top: 4px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  text-align: center;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
}

.system-resource-row {
  margin-bottom: 16px;
}

.system-resource-row .stat-panel {
  min-height: 220px;
}

/* 图表网格（grid-layout-plus 接管，无需 display:grid） */
.edit-mode-tip {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  gap: 12px;
}

.edit-mode-tip .el-alert {
  flex: 1;
}

.edit-mode-done-btn {
  flex-shrink: 0;
}

.edit-mode-reset-btn {
  flex-shrink: 0;
}

:deep(.vue-grid-layout) {
  background: transparent;
}

:deep(.vue-grid-item) {
  background: var(--el-bg-color);
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.05);
  transition: box-shadow 0.3s;
}

/* 编辑模式下面板高亮虚线边框 */
:deep(.vue-grid-item.is-edit-mode) {
  outline: 1px dashed #409eff;
  outline-offset: -1px;
}

:deep(.vue-grid-item.is-edit-mode) .panel-header {
  cursor: move;
}

.chart-panel {
  height: 100%;
  user-select: none;
}

.chart-body {
  padding: 8px;
  height: calc(100% - 42px); /* panel-header height */
  box-sizing: border-box;
}

.chart {
  width: 100%;
  height: 100%;
}

.chart-fullscreen {
  width: 100%;
  height: 100%;
}

.fullscreen-wrapper {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.fullscreen-toolbar {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 4px 0 12px;
  border-bottom: 1px solid var(--el-border-color-light);
  margin-bottom: 12px;
}

.fullscreen-chart-container {
  width: 100%;
  flex: 1;
  min-height: 0;
}

/* 告警 tab */
.alert-panel {
  min-height: 480px;
}

.alerts-body {
  padding: 12px;
}

/* Alerts tab uses PageTable which ships its own toolbar / pagination
   layout; let it fill the panel body directly instead of relying on the
   default panel-body padding + flex layout. */
.alert-panel-pagetable {
  /* drop the panel wrapper flex column; PageTable manages its own box */
  display: block;
  background: transparent;
  box-shadow: none;
}

/* Embedded alerts PageTable inside the overview grid: remove the outer
   PageTable padding/background so it blends with the panel card, and
   tighten the search input width so the toolbar still fits in narrower
   grid cells. */
.alerts-body-pagetable {
  padding: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.alerts-body-pagetable :deep(.page-table-container) {
  padding: 0;
  background: transparent;
  flex: 1;
  min-height: 0;
}

.alerts-body-pagetable :deep(.global-search) {
  max-width: 260px;
}

.alerts-body-pagetable :deep(.table-container) {
  flex: 1;
  min-height: 0;
  overflow: auto;
}

/* Reduce the gap between the toolbar (search box) and the table below.
   PageTable's own .table-toolbar has margin-bottom: 12px; the alerts
   panel wants the table to hug the toolbar tighter. */
.alert-panel-pagetable :deep(.table-toolbar),
.alerts-body-pagetable :deep(.table-toolbar) {
  margin-bottom: 0;
}

/* Keep the severity column header on a single line so the label doesn't
   wrap onto two lines when the panel is narrow. */
.col-nowrap {
  white-space: nowrap;
}

.alert-icon {
  font-size: 14px;
  color: #e6a23c;
  vertical-align: middle;
  margin-right: 4px;
}

/* Element Plus 表格覆盖 */
:deep(.el-table) {
  font-size: 13px;
}

:deep(.el-table th) {
  padding: 8px 0;
  font-size: 13px;
}

:deep(.el-table .cell) {
  padding: 0 8px;
}

@media (max-width: 1200px) {
  .stat-row,
  .stat-row-3,
  .stat-row-4 {
    grid-template-columns: repeat(2, 1fr);
  }
}

/* ===== Bigscreen tab ===== */
.bigscreen-container {
  background: var(--el-bg-color-page);
  padding: 4px 8px 8px;
  border-radius: 8px;
}

.bigscreen-container:fullscreen {
  background: var(--el-bg-color-page);
  padding: 8px 16px 16px;
  overflow: auto;
}

.bigscreen-toolbar {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
  margin-top: -4px;
}

.bigscreen-endpoint {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-right: auto;
}

.bigscreen-endpoint-label {
  font-size: 13px;
  color: var(--el-text-color-regular);
  white-space: nowrap;
}

.bigscreen-endpoint-select {
  min-width: 200px;
}

/* Mirror the sidebar EndpointSwitcher's option layout / status dot so the
   bigscreen selector looks identical to the one in the left sidebar.
   These styles need :deep() because the el-select dropdown popper is
   teleported inside the bigscreen container (:teleported="false") but
   scoped CSS still doesn't reach the popper slot content reliably
   across Element Plus versions. */
.bigscreen-endpoint-select :deep(.endpoint-option),
:deep(.endpoint-switcher-popper .endpoint-option) {
  display: flex;
  align-items: center;
  width: 100%;
  gap: 8px;
}

.bigscreen-endpoint-select :deep(.endpoint-option-alias),
:deep(.endpoint-switcher-popper .endpoint-option-alias) {
  font-weight: 500;
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.bigscreen-endpoint-select :deep(.endpoint-option-meta),
:deep(.endpoint-switcher-popper .endpoint-option-meta) {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  margin-left: auto;
}

.bigscreen-endpoint-select :deep(.endpoint-option-version),
:deep(.endpoint-switcher-popper .endpoint-option-version) {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

/* Status dot: color reflects the endpoint health status. Apply both
   inside the select prefix slot and inside each dropdown option. */
:deep(.endpoint-state-dot) {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
  background: var(--el-color-info);
}

:deep(.endpoint-state-dot.state-ok) {
  background: var(--el-color-success);
}

:deep(.endpoint-state-dot.state-fail) {
  background: var(--el-color-danger);
}

:deep(.endpoint-state-dot.state-probing) {
  background: var(--el-color-info);
}

/* ===== Logs tab ===== */
.logs-panel {
  min-height: 480px;
}

/* Panels hosted inside a GridItem (overview / metrics tabs) must ignore
   the page-level min-height so the grid cell fully controls the size;
   otherwise a too-tall panel overflows and visually covers the panels
   laid out below it (e.g. gauges overlapping the chart row). */
.chart-grid-item .panel-wrapper,
.chart-grid-item .stat-panel,
.chart-grid-item .gauge-panel,
.chart-grid-item .chart-panel,
.chart-grid-item .alert-panel {
  min-height: 0;
  height: 100%;
}

.logs-body {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  padding: 60px 0;
}

</style>

<!-- Global (non-scoped) overrides for the endpoint-switcher popper: the
     dropdown is teleported into the fullscreen bigscreen container via
     :teleported="false", so scoped CSS rules above cannot reach it.
     Mirror the option layout / status dot styling used by the sidebar
     EndpointSwitcher so the two dropdowns look identical. -->
<style lang="scss">
.endpoint-switcher-popper .endpoint-option {
  display: flex;
  align-items: center;
  width: 100%;
  gap: 8px;
}

.endpoint-switcher-popper .endpoint-option-alias {
  font-weight: 500;
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.endpoint-switcher-popper .endpoint-option-meta {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  margin-left: auto;
}

.endpoint-switcher-popper .endpoint-option-version {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.endpoint-switcher-popper .endpoint-state-dot,
.bigscreen-endpoint .endpoint-state-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
  background: var(--el-color-info);
}

.endpoint-switcher-popper .endpoint-state-dot.state-ok,
.bigscreen-endpoint .endpoint-state-dot.state-ok {
  background: var(--el-color-success);
}

.endpoint-switcher-popper .endpoint-state-dot.state-fail,
.bigscreen-endpoint .endpoint-state-dot.state-fail {
  background: var(--el-color-danger);
}

.endpoint-switcher-popper .endpoint-state-dot.state-probing,
.bigscreen-endpoint .endpoint-state-dot.state-probing {
  background: var(--el-color-info);
}
</style>
