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

    <!-- Feature-disabled notice: shown when Prometheus / Alertmanager /
         VictoriaLogs switches are off on the backend. Each metric fetch
         already fails silently to null, this banner explains why. -->
    <el-alert
      v-if="!prometheusEnabled"
      type="warning"
      :closable="false"
      show-icon
      class="feature-disabled-alert"
      title="监控功能未开启"
      description="Prometheus 反向代理未启用，监控数据不可用。请联系管理员在 qcos.toml 中配置 [PROXY] PROMETHEUS_BASE_URL。"
    />
    <el-alert
      v-if="!alertmanagerEnabled"
      type="warning"
      :closable="false"
      show-icon
      class="feature-disabled-alert"
      title="告警功能未开启"
      description="Alertmanager 反向代理未启用，告警数据不可用。请联系管理员在 qcos.toml 中配置 [PROXY] ALERTMANAGER_BASE_URL。"
    />
    <el-alert
      v-if="!victorialogsEnabled"
      type="warning"
      :closable="false"
      show-icon
      class="feature-disabled-alert"
      title="日志功能未开启"
      description="VictoriaLogs 反向代理未启用，日志查询不可用。请联系管理员在 qcos.toml 中配置 [PROXY] VICTORIALOGS_BASE_URL。"
    />

    <el-tabs v-model="activeTab" class="monitor-tabs">
      <!-- ==================== Tab 1: 总览 ==================== -->
      <el-tab-pane label="总览" name="overview">
        <div ref="browserFullscreenRef" class="browser-fullscreen-container">
          <div class="browser-fullscreen-toolbar">
            <!-- Endpoint switcher is only visible while the browser-fullscreen is
                 in browser fullscreen; in normal mode the sidebar already
                 offers the same selector and would be redundant here.
                 popper teleported=false keeps the dropdown attached to
                 this fullscreen container so options actually render. -->
            <div class="browser-fullscreen-endpoint">
              <span class="browser-fullscreen-endpoint-label">量子计算操作系统</span>
              <el-select
                v-model="browserFullscreenEndpointName"
                size="small"
                class="browser-fullscreen-endpoint-select"
                popper-class="endpoint-switcher-popper"
                :teleported="false"
                @change="onBrowserFullscreenEndpointChange"
              >
                <template v-if="browserFullscreenEndpointStatus" #prefix>
                  <span
                    class="endpoint-state-dot"
                    :class="'state-' + browserFullscreenEndpointStatus"
                    :title="browserFullscreenEndpointStatus"
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
            <el-tooltip :content="isBrowserFullscreen ? '退出全屏' : '进入浏览器全屏'" placement="bottom">
              <el-button
                size="small"
                :icon="FullScreen"
                @click="toggleBrowserFullscreen"
              >
                {{ isBrowserFullscreen ? '退出全屏' : '全屏' }}
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
              class="edit-mode-cancel-btn"
              @click="cancelEditMode('overview')"
            >
              取消
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
              <!-- ==================== 分组 1：操作系统指标 ==================== -->
              <div
                v-if="item.i === 'group-os'"
                class="panel-wrapper group-panel"
                @pointerdown="onPanelPointerDown('overview', $event)"
                @pointerup="onPanelPointerUp"
                @pointerleave="onPanelPointerUp"
                @pointercancel="onPanelPointerUp"
              >
                <div class="panel-header">
                  <span class="panel-title">操作系统指标</span>
                  <span class="group-subtitle">系统状态 · 作业 · API</span>
                </div>
                <div class="panel-body group-body">
                  <!-- 系统状态 / 各作业数 / API 请求（紧凑 8 项） -->
                  <div class="os-stats-row">
                    <div class="mini-stat">
                      <span class="mini-stat-label">系统状态</span>
                      <el-tag :type="systemHealthy ? 'success' : 'danger'" size="small">
                        {{ systemHealthy ? '健康' : '异常' }}
                      </el-tag>
                    </div>
                    <div class="mini-stat">
                      <span class="mini-stat-label">作业总数</span>
                      <span class="mini-stat-value">{{ jobStats.total }}</span>
                    </div>
                    <div class="mini-stat">
                      <span class="mini-stat-label">运行中</span>
                      <span class="mini-stat-value primary">{{ jobStats.running }}</span>
                    </div>
                    <div class="mini-stat">
                      <span class="mini-stat-label">队列中</span>
                      <span class="mini-stat-value warning">{{ jobStats.queued }}</span>
                    </div>
                    <div class="mini-stat">
                      <span class="mini-stat-label">已完成</span>
                      <span class="mini-stat-value success">{{ jobStats.completed }}</span>
                    </div>
                    <div class="mini-stat">
                      <span class="mini-stat-label">失败</span>
                      <span class="mini-stat-value danger">{{ jobStats.failed }}</span>
                    </div>
                    <div class="mini-stat">
                      <span class="mini-stat-label">API 总请求</span>
                      <span class="mini-stat-value">{{ apiStats.totalRequests }}</span>
                    </div>
                    <div class="mini-stat">
                      <span class="mini-stat-label">API 并发</span>
                      <span class="mini-stat-value primary">{{ apiStats.inProgress }}</span>
                    </div>
                  </div>
                  <!-- QCOS 进程指标单行摘要 -->
                  <div class="os-proc-line">
                    进程：API {{ qcosProcessStats.apiCpu || '--' }}% / {{ qcosProcessStats.apiMem || '--' }} ·
                    Prefect {{ qcosProcessStats.prefectCpu || '--' }}% / {{ qcosProcessStats.prefectMem || '--' }} ·
                    PostgreSQL {{ qcosProcessStats.pgCpu || '--' }}% ·
                    Redis {{ qcosProcessStats.redisCpu || '--' }}% ·
                    共 {{ qcosProcessStats.totalProcs || '--' }} 进程
                  </div>
                  <!-- 2x2 紧凑折线图：作业数量（总数/运行中/队列中/已完成/失败）、
                       API 总请求数、API 请求速率、API 响应时长 -->
                  <div class="os-charts-row">
                    <div
                      v-for="cid in OVERVIEW_OS_CHART_IDS"
                      :key="cid"
                      class="compact-chart-card"
                    >
                      <template v-if="findPanel(cid)">
                        <div class="compact-chart-header">
                          <span class="compact-chart-title">{{ findPanel(cid).title }}</span>
                          <div class="panel-toolbar" @pointerdown.stop>
                            <el-select
                              v-model="findPanel(cid).timeRange"
                              size="small"
                              class="toolbar-select"
                              @change="onChartParamsChange(cid)"
                            >
                              <el-option
                                v-for="opt in TIME_RANGE_OPTIONS"
                                :key="opt.value"
                                :label="opt.label"
                                :value="opt.value"
                              />
                            </el-select>
                            <el-select
                              v-model="findPanel(cid).step"
                              size="small"
                              class="toolbar-select"
                              @change="onChartParamsChange(cid)"
                            >
                              <el-option
                                v-for="opt in getSafeStepOptions(findPanel(cid).timeRange)"
                                :key="opt.value"
                                :label="opt.label"
                                :value="opt.value"
                              />
                            </el-select>
                            <el-button
                              size="small"
                              :icon="FullScreen"
                              circle
                              @click="toggleFullscreen(cid)"
                            />
                          </div>
                        </div>
                        <div class="compact-chart-body">
                          <sized-chart class="chart" :option="findPanel(cid).option" />
                        </div>
                      </template>
                    </div>
                  </div>
                </div>
              </div>
              <!-- ==================== 分组 2：节点信息 ==================== -->
              <div
                v-else-if="item.i === 'group-node'"
                class="panel-wrapper group-panel"
                @pointerdown="onPanelPointerDown('overview', $event)"
                @pointerup="onPanelPointerUp"
                @pointerleave="onPanelPointerUp"
                @pointercancel="onPanelPointerUp"
              >
                <div class="panel-header">
                  <span class="panel-title">节点信息</span>
                  <span class="group-subtitle">CPU · 内存 · 磁盘</span>
                </div>
                <div class="panel-body group-body">
                  <!-- node-exporter 主机指标 -->
                  <div class="node-host-grid">
                    <div class="host-chip">
                      <span class="host-chip-label">主机负载</span>
                      <span class="host-chip-value">{{ hostExtendedStats.load1 || '--' }}<em> ({{ hostExtendedStats.load5 || '--' }} / {{ hostExtendedStats.load15 || '--' }})</em></span>
                    </div>
                    <div class="host-chip">
                      <span class="host-chip-label">主机内存</span>
                      <span class="host-chip-value">{{ hostExtendedStats.memUsagePercent || '--' }}%</span>
                    </div>
                    <div class="host-chip">
                      <span class="host-chip-label">磁盘 IO</span>
                      <span class="host-chip-value">读 {{ hostExtendedStats.diskReadRate || '--' }}<em> / 写 {{ hostExtendedStats.diskWriteRate || '--' }}</em></span>
                    </div>
                    <div class="host-chip">
                      <span class="host-chip-label">网络 IO</span>
                      <span class="host-chip-value">收 {{ hostExtendedStats.netRecvRate || '--' }}<em> / 发 {{ hostExtendedStats.netSentRate || '--' }}</em></span>
                    </div>
                    <div class="host-chip">
                      <span class="host-chip-label">文件句柄</span>
                      <span class="host-chip-value">{{ hostExtendedStats.fdUsagePercent || '--' }}%</span>
                    </div>
                    <div class="host-chip">
                      <span class="host-chip-label">磁盘容量</span>
                      <span class="host-chip-value">{{ formatMb(systemStats.disk_total_mb) }}<em> · 剩余 {{ formatMb(systemStats.disk_free_mb) }}</em></span>
                    </div>
                  </div>
                  <!-- CPU / 内存 / 磁盘 / 网络历史折线图（2x2） -->
                  <div class="node-charts-row">
                    <div
                      v-for="cid in OVERVIEW_NODE_CHART_IDS"
                      :key="cid"
                      class="compact-chart-card"
                    >
                      <template v-if="findPanel(cid)">
                        <div class="compact-chart-header">
                          <span class="compact-chart-title">{{ findPanel(cid).title }}</span>
                          <div class="panel-toolbar" @pointerdown.stop>
                            <el-select
                              v-model="findPanel(cid).timeRange"
                              size="small"
                              class="toolbar-select"
                              @change="onChartParamsChange(cid)"
                            >
                              <el-option
                                v-for="opt in TIME_RANGE_OPTIONS"
                                :key="opt.value"
                                :label="opt.label"
                                :value="opt.value"
                              />
                            </el-select>
                            <el-select
                              v-model="findPanel(cid).step"
                              size="small"
                              class="toolbar-select"
                              @change="onChartParamsChange(cid)"
                            >
                              <el-option
                                v-for="opt in getSafeStepOptions(findPanel(cid).timeRange)"
                                :key="opt.value"
                                :label="opt.label"
                                :value="opt.value"
                              />
                            </el-select>
                            <el-button
                              size="small"
                              :icon="FullScreen"
                              circle
                              @click="toggleFullscreen(cid)"
                            />
                          </div>
                        </div>
                        <div class="compact-chart-body">
                          <sized-chart class="chart" :option="findPanel(cid).option" />
                        </div>
                      </template>
                    </div>
                  </div>
                </div>
              </div>
              <!-- ==================== 分组 3：告警列表 ==================== -->
              <div
                v-else-if="item.i === 'group-alerts'"
                class="panel-wrapper group-panel alert-panel"
                @pointerdown="onPanelPointerDown('overview', $event)"
                @pointerup="onPanelPointerUp"
                @pointerleave="onPanelPointerUp"
                @pointercancel="onPanelPointerUp"
              >
                <div class="panel-header">
                  <span class="panel-title">告警列表</span>
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
                    :default-page-size="5"
                    :page-size-options="[
                      { label: '5 条/页', value: 5 },
                      { label: '10 条/页', value: 10 },
                      { label: '20 条/页', value: 20 }
                    ]"
                  >
                    <filterable-table-column
                      prop="alertname"
                      label="告警名称"
                      class-name="left-column"
                      sortable="custom"
                      label-class-name="col-nowrap"
                    >
                      <template #default="scope">
                        <el-icon class="alert-icon"><Warning /></el-icon>
                        <span>{{ scope.row.alertname }}</span>
                      </template>
                    </filterable-table-column>
                    <filterable-table-column
                      prop="severity"
                      label="级别"
                      width="120"
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
                      class-name="left-column"
                      sortable="custom"
                      label-class-name="col-nowrap"
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
                      class-name="left-column"
                      sortable="custom"
                      label-class-name="col-nowrap"
                    />
                  </PageTable>
                </div>
              </div>
              <!-- ==================== 分组 4：日志列表 ==================== -->
              <div
                v-else-if="item.i === 'group-logs'"
                class="panel-wrapper group-panel logs-group"
                @pointerdown="onPanelPointerDown('overview', $event)"
                @pointerup="onPanelPointerUp"
                @pointerleave="onPanelPointerUp"
                @pointercancel="onPanelPointerUp"
              >
                <div class="panel-header">
                  <span class="panel-title">日志列表</span>
                  <span class="group-subtitle">VictoriaLogs</span>
                </div>
                <div class="panel-body logs-group-body">
                  <LogsPanel :auto-refresh="overviewLogsAutoRefresh" />
                </div>
              </div>

            </GridItem>
          </GridLayout>
        </div>
      </el-tab-pane>

      <!-- ==================== Tab 3: 操作系统指标 ==================== -->
      <!-- lazy: only mount this pane's DOM when the tab is first activated.
           Without it the pane is rendered but display:none, so every
           v-chart inside initialises against a 0x0 container and ECharts
           logs "Can't get DOM width or height" on page mount. -->
      <el-tab-pane label="操作系统指标" name="metrics" lazy>
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
            class="edit-mode-cancel-btn"
            @click="cancelEditMode('metrics')"
          >
            取消
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
                <div class="panel-toolbar" @pointerdown.stop>
                  <el-button
                    size="small"
                    :icon="FullScreen"
                    circle
                    @click="toggleFullscreen('gauge-cpu')"
                  />
                </div>
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
                <div class="panel-toolbar" @pointerdown.stop>
                  <el-button
                    size="small"
                    :icon="FullScreen"
                    circle
                    @click="toggleFullscreen('gauge-mem')"
                  />
                </div>
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
                <div class="panel-toolbar" @pointerdown.stop>
                  <el-button
                    size="small"
                    :icon="FullScreen"
                    circle
                    @click="toggleFullscreen('gauge-disk')"
                  />
                </div>
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
                <sized-chart
                  v-if="findPanel(item.i)"
                  class="chart"
                  :option="findPanel(item.i).option"
                />
              </div>
            </div>
          </GridItem>
        </GridLayout>
      </el-tab-pane>

      <!-- ==================== Tab 3.5: 节点信息 ==================== -->
      <!-- lazy: same 0x0-container rationale as the metrics tab above. -->
      <el-tab-pane label="节点信息" name="node-info" lazy>
        <NodeInfoPanel />
      </el-tab-pane>

      <!-- ==================== Tab 3: 告警 ==================== -->
      <el-tab-pane label="告警" name="alerts" lazy>
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
              class-name="left-column"
              sortable="custom"
              label-class-name="col-nowrap"
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
              class-name="left-column"
              sortable="custom"
              label-class-name="col-nowrap"
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
              class-name="left-column"
              sortable="custom"
              label-class-name="col-nowrap"
            />
          </PageTable>
        </div>
      </el-tab-pane>

      <!-- ==================== Tab 5: 日志 ==================== -->
      <el-tab-pane label="日志" name="logs" lazy>
        <LogsPanel />
      </el-tab-pane>
    </el-tabs>

    <!-- 全屏对话框 -->
    <el-dialog
      v-model="fullscreenVisible"
      :title="fullscreenTitle"
      fullscreen
      destroy-on-close
      append-to-body
      @opened="onFullscreenDialogOpened"
    >
      <div class="fullscreen-wrapper">
        <div v-if="fullscreenPanel" class="fullscreen-toolbar">
          <!-- Gauge panels (CPU / memory / disk) support switching between
               the dashboard ring and the history line chart inside the
               fullscreen dialog, mirroring the in-grid panel toolbar. -->
          <el-select
            v-if="isGaugePanel"
            v-model="fullscreenGaugeView"
            size="small"
            class="toolbar-select gauge-view-select"
            @change="onFullscreenGaugeViewChange"
          >
            <el-option label="仪表盘" value="gauge" />
            <el-option label="折线图" value="chart" />
          </el-select>
          <template v-if="!isGaugePanel || fullscreenGaugeView === 'chart'">
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
          </template>
        </div>
        <div class="fullscreen-chart-container">
          <!-- SizedChart observes its host with ResizeObserver and only
               mounts the inner v-chart once the dialog content has a
               non-zero size, so the ECharts "Can't get DOM width or
               height" warning cannot occur. The fullscreenDialogOpened
               flag still guards against mounting before the dialog has
               even opened (saves an unnecessary observer). -->
          <template v-if="isGaugePanel && fullscreenGaugeView === 'gauge'">
            <!-- Dashboard ring enlarged for the fullscreen dialog. The ring
                 itself stays a fixed pixel size (360px reads well on any
                 viewport), centered by the flex container. -->
            <div class="fullscreen-gauge">
              <el-progress
                type="dashboard"
                :width="360"
                :stroke-width="22"
                :percentage="clampPercent(currentGaugeValue)"
                :color="percentColor(currentGaugeValue)"
              />
              <div class="fullscreen-gauge-desc">
                {{ currentGaugeValue.toFixed(1) }}% · {{ currentGaugeSubText }}
              </div>
            </div>
          </template>
          <sized-chart
            v-else-if="currentFullscreenOption && fullscreenDialogOpened"
            :key="fullscreenChart + fullscreenRenderKey"
            class="chart-fullscreen"
            :option="currentFullscreenOption"
          />
          <div v-else class="fullscreen-empty">
            <el-empty description="暂无数据" />
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script>
import { markRaw } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Warning, FullScreen, Loading, TrendCharts } from '@element-plus/icons-vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, PieChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  VisualMapComponent
} from 'echarts/components'
import { GridLayout, GridItem } from 'grid-layout-plus'

use([
  CanvasRenderer,
  LineChart,
  PieChart,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  VisualMapComponent
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
import SizedChart from '@/components/SizedChart/index.vue'
import PageTable from '@/components/PageTable/index.vue'
import FilterableTableColumn from '@/components/PageTable/FilterableTableColumn.vue'
import LogsPanel from '@/views/system/components/LogsPanel.vue'
import NodeInfoPanel from '@/views/system/components/NodeInfoPanel.vue'
import { useConfigStore } from '@/store/modules/config'
import { useUserStore } from '@/store/modules/user'
import { useComponentsStore } from '@/store/modules/components'
import { removeSession } from '@/utils/session'

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

// Non-reactive per-instance values that should NOT live in `data()`:
// Vue reserves `_`-prefixed keys on the component proxy and the ESLint
// vue/no-reserved-keys rule flags them. Keep them as module-level
// constants / instance fields assigned in `created()`.
const LONG_PRESS_DURATION_MS = 600 // press-and-hold to enter edit mode
// Bump whenever the default grid layout shape changes (panel ids
// added/removed, default x/y/w/h rearranged). Saved layouts whose
// embedded version does not match are discarded on load so users
// always land on the current default after an upgrade.
const LAYOUT_VERSION = 7

// Overview-tab grouped panel constants. The overview grid hosts three
// grouped border panels; each group renders a fixed set of inner
// panels (charts / gauges) declared here so the template can loop
// over them while the draggable grid item stays a single unit.
// Rendered as a 2x2 grid: row 1 = job counts + API total requests,
// row 2 = API request rate + API response duration.
const OVERVIEW_OS_CHART_IDS = [
  'chart-overview-jobs',
  'chart-overview-api-total',
  'chart-api-rate',
  'chart-api-duration'
]
// Node-info group history line charts (CPU / memory / disk / network),
// rendered as a 2x2 compact chart grid below the numeric chips.
const OVERVIEW_NODE_CHART_IDS = [
  'chart-overview-node-cpu',
  'chart-overview-node-mem',
  'chart-overview-node-disk',
  'chart-overview-node-net'
]

export default {
  name: 'MonitorCenter',
  components: {
    RefreshInterval,
    SizedChart,
    Warning,
    NodeInfoPanel,
    Loading,
    GridLayout,
    GridItem,
    PageTable,
    FilterableTableColumn,
    LogsPanel
  },
  data() {
    return {
      FullScreen: markRaw(FullScreen),
      TrendCharts: markRaw(TrendCharts),
      activeTab: 'overview',
      // Endpoint switcher in the overview toolbar (mirrors the sidebar
      // "当前系统" selector; the active endpoint drives every API call
      // on this page).
      browserFullscreenEndpointName: '',
      // True while the overview browser-fullscreen is in browser-native fullscreen
      // (tracked via fullscreenchange so the button label / endpoint
      // selector can react even if the user pressed ESC to exit).
      isBrowserFullscreen: false,
      loading: false,
      alertsLoading: false,
      systemHealthy: false,
      // Current refresh interval in seconds (mirrors the RefreshInterval
      // header selector). Passed to the overview logs group so the
      // embedded LogsPanel refreshes in sync with the other panels.
      refreshIntervalSec: 10,
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
      // Host extended stats from node-exporter
      hostExtendedStats: {
        load1: null,
        load5: null,
        load15: null,
        memUsagePercent: null,
        diskReadRate: null,
        diskWriteRate: null,
        netRecvRate: null,
        netSentRate: null,
        fdUsagePercent: null
      },
      // QCOS process stats from process-exporter
      qcosProcessStats: {
        apiCpu: null,
        apiMem: null,
        prefectCpu: null,
        prefectMem: null,
        pgCpu: null,
        pgMem: null,
        redisCpu: null,
        redisMem: null,
        totalProcs: null
      },
      alerts: [],
      // Gauge panels (CPU / memory / disk). Each has a viewMode toggle
      // ('gauge' = dashboard ring, 'chart' = history line chart) plus
      // its own timeRange/step for the Prometheus range query when in
      // chart mode.
      gaugePanels: {
        'gauge-cpu': {
          viewMode: 'gauge',
          timeRange: DEFAULT_CHART_PARAMS.timeRange,
          step: DEFAULT_CHART_PARAMS.step,
          option: {}
        },
        'gauge-mem': {
          viewMode: 'gauge',
          timeRange: DEFAULT_CHART_PARAMS.timeRange,
          step: DEFAULT_CHART_PARAMS.step,
          option: {}
        },
        'gauge-disk': {
          viewMode: 'gauge',
          timeRange: DEFAULT_CHART_PARAMS.timeRange,
          step: DEFAULT_CHART_PARAMS.step,
          option: {}
        }
      },
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
        },
        // Overview-tab only compact charts: job counts (total / running /
        // queued / completed / failed in one line chart) and cumulative
        // API total requests.
        {
          id: 'chart-overview-jobs',
          title: '作业数量',
          ref: 'overviewJobsChart',
          option: {},
          ...JSON.parse(JSON.stringify(DEFAULT_CHART_PARAMS))
        },
        {
          id: 'chart-overview-api-total',
          title: 'API 总请求数',
          ref: 'overviewApiTotalChart',
          option: {},
          ...JSON.parse(JSON.stringify(DEFAULT_CHART_PARAMS))
        },
        // Overview node-info group history line charts: CPU / memory /
        // disk percent plus network IO rates, rendered as a 2x2 grid
        // below the numeric chips.
        {
          id: 'chart-overview-node-cpu',
          title: '节点 CPU 使用率',
          ref: 'overviewNodeCpuChart',
          option: {},
          ...JSON.parse(JSON.stringify(DEFAULT_CHART_PARAMS))
        },
        {
          id: 'chart-overview-node-mem',
          title: '节点内存使用率',
          ref: 'overviewNodeMemChart',
          option: {},
          ...JSON.parse(JSON.stringify(DEFAULT_CHART_PARAMS))
        },
        {
          id: 'chart-overview-node-disk',
          title: '节点磁盘使用率',
          ref: 'overviewNodeDiskChart',
          option: {},
          ...JSON.parse(JSON.stringify(DEFAULT_CHART_PARAMS))
        },
        {
          id: 'chart-overview-node-net',
          title: '节点网络 IO',
          ref: 'overviewNodeNetChart',
          option: {},
          ...JSON.parse(JSON.stringify(DEFAULT_CHART_PARAMS))
        }
      ],
      TIME_RANGE_OPTIONS,
      // Expose the overview group panel id lists to the template loops.
      OVERVIEW_OS_CHART_IDS,
      OVERVIEW_NODE_CHART_IDS,
      // 全屏
      fullscreenVisible: false,
      fullscreenChart: '',
      fullscreenTitle: '',
      // Incremented every time the fullscreen dialog opens so v-chart
      // re-mounts after the dialog has finished its CSS transition and
      // has non-zero dimensions.
      fullscreenRenderKey: 0,
      // True only after the fullscreen dialog has finished its open
      // transition (@opened). v-chart stays unmounted until then so
      // ECharts always initialises against a container with real
      // dimensions; mounting earlier triggers "Can't get DOM width or
      // height" and leaves the dialog showing only the panel title.
      fullscreenDialogOpened: false,
      // View mode shown inside the fullscreen dialog when the panel is a
      // gauge (CPU / memory / disk): 'gauge' = dashboard ring, 'chart' =
      // history line chart. Kept separate from gaugePanels[id].viewMode
      // so opening the fullscreen dialog never mutates the in-grid view.
      fullscreenGaugeView: 'gauge',
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
      // Overview tab grid layout. Three grouped border panels fit one
      // screen: 1) OS metrics (system status / job counts / API requests
      // + process stats + API charts), 2) node info (CPU / memory / disk
      // gauges + node-exporter chips), 3) alert list table.
      overviewLayout: [
        { i: 'group-os', x: 0, y: 0, w: 8, h: 22 },
        { i: 'group-node', x: 8, y: 0, w: 4, h: 22 },
        { i: 'group-alerts', x: 0, y: 22, w: 6, h: 10 },
        { i: 'group-logs', x: 6, y: 22, w: 6, h: 10 }
      ],
      // Edit-mode flags (long-press to enter, "完成" to exit).
      // Each tab tracks its own edit-mode state so switching tabs doesn't
      // accidentally leave the other tab in edit mode.
      isOverviewEditMode: false,
      isMetricsEditMode: false
    }
  },

  computed: {
    // Feature flags sourced from the components store. When the backend
    // turns one of these off, the corresponding data fetches short-circuit
    // in webui/src/api/monitor.js / logs.js and the warning banners at the
    // top of the page explain why the panels are empty.
    prometheusEnabled() {
      return useComponentsStore().proxyPrometheusEnabled
    },
    alertmanagerEnabled() {
      return useComponentsStore().proxyAlertmanagerEnabled
    },
    victorialogsEnabled() {
      return useComponentsStore().proxyVictorialogsEnabled
    },
    fullscreenPanel() {
      // Chart panels first, then gauge panels so both can be opened in
      // the fullscreen dialog.
      const chart = this.chartPanels.find(p => p.id === this.fullscreenChart)
      if (chart) return chart
      const gauge = this.gaugePanels[this.fullscreenChart]
      if (gauge) {
        const titleMap = {
          'gauge-cpu': '节点CPU总使用率',
          'gauge-mem': '节点内存总使用率',
          'gauge-disk': '磁盘总使用率'
        }
        // Getter/setter write-through: the dialog toolbar binds
        // v-model="fullscreenPanel.timeRange" / ".step". Returning a plain
        // copy would silently discard those writes for gauge panels
        // (fetchGaugeHistory re-reads gaugePanels[id]), so the chart mode
        // could never pick up a new time range. The accessors delegate
        // straight to the source-of-truth panel object.
        return {
          id: this.fullscreenChart,
          title: titleMap[this.fullscreenChart] || this.fullscreenChart,
          get timeRange() {
            return gauge.timeRange
          },
          set timeRange(v) {
            gauge.timeRange = v
          },
          get step() {
            return gauge.step
          },
          set step(v) {
            gauge.step = v
          },
          option: gauge.option
        }
      }
      return null
    },
    currentFullscreenOption() {
      const option = this.fullscreenPanel ? this.fullscreenPanel.option : null
      // Guard against empty option objects (e.g. gauge panels before
      // history data has been fetched). ECharts throws when initialised
      // with an empty option on a zero-size DOM element.
      if (!option || typeof option !== 'object' || !option.series) {
        return null
      }
      return option
    },
    // True when the panel opened in the fullscreen dialog is one of the
    // three gauge panels (CPU / memory / disk), which support the
    // gauge / chart view switch inside the dialog.
    isGaugePanel() {
      return Boolean(this.gaugePanels[this.fullscreenChart])
    },
    // Live percentage of the gauge panel currently shown in the
    // fullscreen dialog, read from the latest system stats snapshot.
    currentGaugeValue() {
      switch (this.fullscreenChart) {
        case 'gauge-cpu':
          return this.systemStats.host_cpu_percent
        case 'gauge-mem':
          return this.systemStats.mem_percent
        case 'gauge-disk':
          return this.systemStats.disk_percent
        default:
          return 0
      }
    },
    // Secondary line under the fullscreen gauge ring, mirroring the
    // in-grid gauge panel descriptions (cores / total / free).
    currentGaugeSubText() {
      switch (this.fullscreenChart) {
        case 'gauge-cpu':
          return `${this.systemStats.cpu_count} 核`
        case 'gauge-mem':
          return `共 ${this.formatMb(this.systemStats.mem_total_mb)}`
        case 'gauge-disk':
          return `剩余 ${this.formatMb(this.systemStats.disk_free_mb)}`
        default:
          return ''
      }
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
    browserFullscreenEndpointStatus() {
      const cfg = useConfigStore()
      const h = cfg.healthMap[this.browserFullscreenEndpointName] || {}
      return h.status || ''
    },
    // Alerts whose Alertmanager state is still "active" (i.e. currently
    // firing) vs the full list which also includes resolved / silenced /
    // inhibited records pulled for history display.
    activeAlertCount() {
      return this.alerts.filter(a => a.status === 'active').length
    },
    // Auto-refresh interval forwarded to the overview embedded LogsPanel.
    // Clamped to a minimum of 10s so a very short global interval does
    // not hammer VictoriaLogs; 0 disables (interval selector "off").
    overviewLogsAutoRefresh() {
      if (!this.refreshIntervalSec) return 0
      return Math.max(10, this.refreshIntervalSec)
    }
  },

  created() {
    // Non-reactive instance fields (see module-level comment above).
    // Assigned here so every component instance gets its own timer
    // handle without going through the reactive proxy.
    this.longPressTimer = null
    // Layout snapshots taken when entering edit mode. Used by
    // cancelEditMode() to restore the previous layout. Not part of
    // data() because we never want these to be reactive (would deep-
    // watch large layout arrays on every drag tick for no benefit).
    this._editModeSnapshotOverview = null
    this._editModeSnapshotMetrics = null
  },

  mounted() {
    this.initChartOptions()
    this._loadLayout('overview')
    this._loadLayout('metrics')
    // Initialize the overview endpoint selector from the active endpoint
    // so the dropdown reflects whatever was picked in the sidebar.
    const cfg = useConfigStore()
    this.browserFullscreenEndpointName = cfg.activeEndpointName
    this.fetchAllData()
    this._onFullscreenChange = () => {
      this.isBrowserFullscreen =
        document.fullscreenElement === this.$refs.browserFullscreenRef
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
          this.fetchAlerts(),
          this.fetchHostExtendedStats(),
          this.fetchQcosProcessStats()
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

    async fetchHostExtendedStats() {
      try {
        const [load1, load5, load15, memUsage, diskRead, diskWrite, netRecv, netSent, fdUsage] = await Promise.all([
          queryPrometheus('node_load1').then(extractLatestValue).catch(() => null),
          queryPrometheus('node_load5').then(extractLatestValue).catch(() => null),
          queryPrometheus('node_load15').then(extractLatestValue).catch(() => null),
          queryPrometheus('(1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100').then(extractLatestValue).catch(() => null),
          queryPrometheus('sum(rate(node_disk_read_bytes_total[5m]))').then(extractLatestValue).catch(() => null),
          queryPrometheus('sum(rate(node_disk_written_bytes_total[5m]))').then(extractLatestValue).catch(() => null),
          queryPrometheus('sum(rate(node_network_receive_bytes_total[5m]))').then(extractLatestValue).catch(() => null),
          queryPrometheus('sum(rate(node_network_transmit_bytes_total[5m]))').then(extractLatestValue).catch(() => null),
          queryPrometheus('node_filefd_allocated / node_filefd_maximum * 100').then(extractLatestValue).catch(() => null)
        ])

        this.hostExtendedStats.load1 = load1 !== null ? load1.toFixed(2) : '--'
        this.hostExtendedStats.load5 = load5 !== null ? load5.toFixed(2) : '--'
        this.hostExtendedStats.load15 = load15 !== null ? load15.toFixed(2) : '--'
        this.hostExtendedStats.memUsagePercent = memUsage !== null ? memUsage.toFixed(1) : '--'
        this.hostExtendedStats.diskReadRate = diskRead !== null ? this.formatBytesPerSecond(diskRead) : '--'
        this.hostExtendedStats.diskWriteRate = diskWrite !== null ? this.formatBytesPerSecond(diskWrite) : '--'
        this.hostExtendedStats.netRecvRate = netRecv !== null ? this.formatBytesPerSecond(netRecv) : '--'
        this.hostExtendedStats.netSentRate = netSent !== null ? this.formatBytesPerSecond(netSent) : '--'
        this.hostExtendedStats.fdUsagePercent = fdUsage !== null ? fdUsage.toFixed(1) : '--'
      } catch (error) {
        console.error('获取主机扩展指标失败:', error)
      }
    },

    async fetchQcosProcessStats() {
      try {
        const [apiCpu, apiMem, prefectCpu, prefectMem, pgCpu, pgMem, redisCpu, redisMem, totalProcs] = await Promise.all([
          queryPrometheus('sum(rate(namedprocess_namegroup_cpu_seconds_total{groupname="qcos-api"}[5m])) * 100').then(extractLatestValue).catch(() => null),
          queryPrometheus('sum(namedprocess_namegroup_memory_bytes{groupname="qcos-api", memtype="resident"}) / 1024 / 1024').then(extractLatestValue).catch(() => null),
          queryPrometheus('sum(rate(namedprocess_namegroup_cpu_seconds_total{groupname=~"qcos-prefect-.*"}[5m])) * 100').then(extractLatestValue).catch(() => null),
          queryPrometheus('sum(namedprocess_namegroup_memory_bytes{groupname=~"qcos-prefect-.*", memtype="resident"}) / 1024 / 1024').then(extractLatestValue).catch(() => null),
          queryPrometheus('sum(rate(namedprocess_namegroup_cpu_seconds_total{groupname="qcos-postgres"}[5m])) * 100').then(extractLatestValue).catch(() => null),
          queryPrometheus('sum(namedprocess_namegroup_memory_bytes{groupname="qcos-postgres", memtype="resident"}) / 1024 / 1024').then(extractLatestValue).catch(() => null),
          queryPrometheus('sum(rate(namedprocess_namegroup_cpu_seconds_total{groupname="qcos-redis"}[5m])) * 100').then(extractLatestValue).catch(() => null),
          queryPrometheus('sum(namedprocess_namegroup_memory_bytes{groupname="qcos-redis", memtype="resident"}) / 1024 / 1024').then(extractLatestValue).catch(() => null),
          queryPrometheus('sum(namedprocess_namegroup_num_procs{groupname=~"qcos-.*"})').then(extractLatestValue).catch(() => null)
        ])

        this.qcosProcessStats.apiCpu = apiCpu !== null ? apiCpu.toFixed(1) : '--'
        this.qcosProcessStats.apiMem = apiMem !== null ? this.formatMb(apiMem) : '--'
        this.qcosProcessStats.prefectCpu = prefectCpu !== null ? prefectCpu.toFixed(1) : '--'
        this.qcosProcessStats.prefectMem = prefectMem !== null ? this.formatMb(prefectMem) : '--'
        this.qcosProcessStats.pgCpu = pgCpu !== null ? pgCpu.toFixed(1) : '--'
        this.qcosProcessStats.pgMem = pgMem !== null ? this.formatMb(pgMem) : '--'
        this.qcosProcessStats.redisCpu = redisCpu !== null ? redisCpu.toFixed(1) : '--'
        this.qcosProcessStats.redisMem = redisMem !== null ? this.formatMb(redisMem) : '--'
        this.qcosProcessStats.totalProcs = totalProcs !== null ? Math.round(totalProcs) : '--'
      } catch (error) {
        console.error('获取 QCOS 进程指标失败:', error)
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
      return { result: { items, total }}
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
          splitLine: { lineStyle: { type: 'dashed' }}
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
      // Gauge panels live outside chartPanels; fall back to gaugePanels.
      const panel = this.findPanel(id) || this.gaugePanels[id]
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
      // Gauge panels fetch history via fetchGaugeHistory, not
      // fetchChartDataById which only handles chartPanels.
      if (this.gaugePanels[id]) {
        this.fetchGaugeHistory(id)
      } else {
        this.fetchChartDataById(id)
      }
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
        case 'chart-overview-jobs':
          await this.fetchOverviewJobsData(panel, start, end, step)
          break
        case 'chart-overview-api-total':
          await this.fetchOverviewApiTotalData(panel, start, end, step)
          break
        case 'chart-overview-node-cpu':
        case 'chart-overview-node-mem':
        case 'chart-overview-node-disk':
        case 'chart-overview-node-net':
          await this.fetchOverviewNodeChartData(id, panel, start, end, step)
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

    /**
     * Overview-tab compact chart: job counts as one line chart covering
     * total / running / queued / completed / failed. Colors come from
     * JOB_STATUS_COLORS (total uses grey) so the chart matches the job
     * list tag colors.
     */
    async fetchOverviewJobsData(panel, start, end, step) {
      try {
        const queries = [
          { key: 'total', label: '总数' },
          { key: 'running', label: '运行中' },
          { key: 'queued', label: '队列中' },
          { key: 'completed', label: '已完成' },
          { key: 'failed', label: '失败' }
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
        console.error('获取总览作业数量数据失败:', error)
      }
    },

    /**
     * Overview-tab compact chart: cumulative API total requests
     * (sum(api_requests_total)) as a single line.
     */
    async fetchOverviewApiTotalData(panel, start, end, step) {
      try {
        const result = await queryPrometheusRange(PROMQL.apiTotalRequests, start, end, step)
          .then(r => extractMultiTimeSeries(r, 'API 总请求数'))
          .catch(() => [])

        const seriesData = [
          { name: 'API 总请求数', data: result[0]?.data || [] }
        ]

        panel.option.legend.data = seriesData.map(s => s.name)
        panel.option.series = this.buildSeries(seriesData, ['#409eff'])
      } catch (error) {
        console.error('获取总览 API 总请求数数据失败:', error)
      }
    },

    /**
     * Overview node-info group history line charts: CPU / memory / disk
     * usage percentages and network IO rates. CPU / mem / disk reuse the
     * qcos_system_* percent gauges (same source as the gauge panels),
     * network uses node-exporter receive / transmit rates (bytes per
     * second, auto-scaled via the y-axis formatter).
     */
    async fetchOverviewNodeChartData(id, panel, start, end, step) {
      try {
        let seriesData = []
        let colors = []
        let yAxisFormatter = null

        switch (id) {
          case 'chart-overview-node-cpu':
            seriesData = [
              { name: 'CPU 使用率', data: await this.queryPercentRange('qcos_system_host_cpu_percent', 'CPU 使用率', start, end, step) }
            ]
            colors = ['#409eff']
            break
          case 'chart-overview-node-mem':
            seriesData = [
              { name: '内存使用率', data: await this.queryPercentRange('qcos_system_mem_percent', '内存使用率', start, end, step) }
            ]
            colors = ['#67c23a']
            break
          case 'chart-overview-node-disk':
            seriesData = [
              { name: '磁盘使用率', data: await this.queryPercentRange('qcos_system_disk_percent', '磁盘使用率', start, end, step) }
            ]
            colors = ['#e6a23c']
            break
          case 'chart-overview-node-net': {
            const [recv, sent] = await Promise.all([
              queryPrometheusRange('sum(rate(node_network_receive_bytes_total[5m]))', start, end, step)
                .then(r => extractMultiTimeSeries(r, '接收'))
                .catch(() => []),
              queryPrometheusRange('sum(rate(node_network_transmit_bytes_total[5m]))', start, end, step)
                .then(r => extractMultiTimeSeries(r, '发送'))
                .catch(() => [])
            ])
            seriesData = [
              { name: '接收', data: recv[0]?.data || [] },
              { name: '发送', data: sent[0]?.data || [] }
            ]
            colors = ['#409eff', '#67c23a']
            yAxisFormatter = v => this.formatBytesPerSecond(v)
            break
          }
          default:
            return
        }

        panel.option.legend.data = seriesData.map(s => s.name)
        panel.option.series = this.buildSeries(seriesData, colors)
        if (yAxisFormatter) {
          panel.option.yAxis.axisLabel = {
            ...panel.option.yAxis.axisLabel,
            formatter: yAxisFormatter
          }
        } else {
          panel.option.yAxis.min = 0
          panel.option.yAxis.max = 100
          panel.option.yAxis.name = '%'
        }
      } catch (error) {
        console.error('获取总览节点历史数据失败:', error)
      }
    },

    /**
     * Helper: run one Prometheus range query and return the first
     * time-series data array (empty array on failure).
     */
    async queryPercentRange(promql, label, start, end, step) {
      const result = await queryPrometheusRange(promql, start, end, step)
        .then(r => extractMultiTimeSeries(r, label))
        .catch(() => [])
      return result[0]?.data || []
    },

    // ==================== Gauge 面板切换 ====================
    onGaugeViewChange(id) {
      if (this.gaugePanels[id] && this.gaugePanels[id].viewMode === 'chart') {
        this.fetchGaugeHistory(id)
      }
    },

    onGaugeParamsChange(id) {
      const panel = this.gaugePanels[id]
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
      this.fetchGaugeHistory(id)
    },

    async fetchGaugeHistory(id) {
      const panel = this.gaugePanels[id]
      if (!panel) return
      const end = Math.floor(Date.now() / 1000)
      const start = end - panel.timeRange
      const step = panel.step

      let promql = ''
      let label = ''
      switch (id) {
        case 'gauge-cpu':
          promql = 'qcos_system_host_cpu_percent'
          label = 'CPU 使用率'
          break
        case 'gauge-mem':
          promql = 'qcos_system_mem_percent'
          label = '内存使用率'
          break
        case 'gauge-disk':
          promql = 'qcos_system_disk_percent'
          label = '磁盘使用率'
          break
        default:
          return
      }

      try {
        const result = await queryPrometheusRange(promql, start, end, step)
          .then(r => extractMultiTimeSeries(r, label))
          .catch(() => [])

        const seriesData = result.length > 0
          ? [{ name: label, data: result[0].data }]
          : [{ name: label, data: [] }]

        panel.option = {
          title: { show: false },
          tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'cross' },
            valueFormatter: v => v + ' %'
          },
          legend: { show: false },
          grid: {
            left: '3%',
            right: '4%',
            bottom: '10%',
            top: '10%',
            containLabel: true
          },
          xAxis: {
            type: 'time',
            splitLine: { show: false },
            axisLabel: { fontSize: 10 }
          },
          yAxis: {
            type: 'value',
            min: 0,
            max: 100,
            name: '%',
            nameTextStyle: { fontSize: 10 },
            axisLabel: { fontSize: 10 },
            splitLine: { lineStyle: { type: 'dashed' }}
          },
          // 按数值区间着色，与仪表盘颜色规则一致：
          // <70 绿 (#67c23a), 70-90 黄 (#e6a23c), >=90 红 (#f56c6c)
          visualMap: {
            show: false,
            dimension: 1,
            pieces: [
              { lt: 70, color: '#67c23a' },
              { gte: 70, lt: 90, color: '#e6a23c' },
              { gte: 90, color: '#f56c6c' }
            ]
          },
          series: this.buildSeries(seriesData, ['#67c23a'])
        }
      } catch (error) {
        console.error(`获取 ${label} 历史趋势失败:`, error)
        panel.option = {
          title: {
            text: '暂无数据',
            left: 'center',
            top: 'center',
            textStyle: { color: '#909399', fontSize: 14, fontWeight: 'normal' }
          }
        }
      }
    },

    // ==================== 全屏 ====================
    async toggleFullscreen(id) {
      // Support both chart panels and gauge panels. For gauge panels we
      // fabricate a panel-like object so the fullscreen dialog can reuse
      // the same rendering path.
      let panel = this.findPanel(id)
      if (!panel) {
        const gauge = this.gaugePanels[id]
        if (gauge) {
          const titleMap = {
            'gauge-cpu': '节点CPU总使用率',
            'gauge-mem': '节点内存总使用率',
            'gauge-disk': '磁盘总使用率'
          }
          panel = {
            id,
            title: titleMap[id] || id,
            timeRange: gauge.timeRange,
            step: gauge.step,
            option: gauge.option
          }
        }
      }
      if (!panel) return
      // Gauge panels support the gauge / chart view switch inside the
      // fullscreen dialog. Start from the panel's in-grid view mode so
      // the fullscreen dialog feels like a magnified version of it.
      if (this.gaugePanels[id]) {
        this.fullscreenGaugeView = this.gaugePanels[id].viewMode
        // Pre-fetch history (when not yet loaded) so the chart view has
        // data ready if/when the user switches to it inside the dialog.
        await this.fetchGaugeHistory(id)
        panel.option = this.gaugePanels[id].option
      }
      this.fullscreenChart = id
      this.fullscreenTitle = panel.title
      this.fullscreenVisible = true
      // Bump the render key so v-chart re-mounts after the dialog has
      // finished its CSS transition and has non-zero dimensions.
      this.fullscreenRenderKey += 1
      // Reset the opened flag so v-chart stays unmounted until the
      // dialog fires @opened (see onFullscreenDialogOpened).
      this.fullscreenDialogOpened = false
    },

    // View switch inside the fullscreen dialog for gauge panels. When
    // switching to the chart view, ensure history data has been fetched
    // for the panel's current timeRange/step and bump the render key so
    // SizedChart mounts fresh against the now-visible container.
    async onFullscreenGaugeViewChange() {
      if (this.fullscreenGaugeView !== 'chart') return
      const id = this.fullscreenChart
      if (!this.gaugePanels[id]) return
      await this.fetchGaugeHistory(id)
      this.fullscreenRenderKey += 1
    },

    // Called by el-dialog @opened: the dialog content now has its final
    // non-zero size, so it is safe to mount v-chart.
    onFullscreenDialogOpened() {
      this.fullscreenDialogOpened = true
      // Belt-and-braces: even with SizedChart's ResizeObserver +
      // double-rAF retry, force a window resize event on the next
      // frame so any v-chart that somehow mounted against a stale
      // 0x0 box gets one more chance to re-fit. Cheap because
      // listeners are throttled internally by vue-echarts.
      this.$nextTick(() => {
        window.dispatchEvent(new Event('resize'))
      })
    },

    // Endpoint selector embedded in the overview browser-fullscreen toolbar.
    // Mirrors the sidebar EndpointSwitcher.onChange flow: probe the target
    // endpoint, refuse the switch when unhealthy, restore the saved session
    // (or fall back to no-auth), then reload so every view fetches data
    // against the new endpoint.
    async onBrowserFullscreenEndpointChange(name) {
      const cfg = useConfigStore()
      if (!name || name === cfg.activeEndpointName) return
      // Ensure health info is up-to-date before switching.
      const health = await cfg.probeEndpoint(name)
      if (!health || health.status !== 'ok') {
        ElMessage.warning(`endpoint ${name} 当前不可用，无法切换`)
        this.browserFullscreenEndpointName = cfg.activeEndpointName
        return
      }
      cfg.setActive(name)

      const userStore = useUserStore()
      // auth mode "no": treat as authenticated and reload immediately.
      const authMode = String(health.authMode || '').toLowerCase().trim()
      if (authMode === 'no') {
        userStore.noAuthLogin()
        location.reload()
        return
      }

      // jwt (or other auth modes): restore the persisted session and
      // verify the token against the new endpoint before reloading.
      const hasSession = userStore.loadSessionForActiveEndpoint()
      if (!hasSession) {
        this.$router.push({
          path: '/login',
          query: { redirect: this.$route.fullPath, endpoint: name }
        })
        return
      }
      try {
        await userStore.getInfo()
        location.reload()
      } catch {
        // Token no longer valid on the target endpoint: drop the stored
        // session so the login page does not loop, then re-authenticate.
        removeSession(name)
        userStore.resetToken()
        ElMessage.warning(`endpoint ${name} 登录态已失效，请重新登录`)
        this.$router.push({
          path: '/login',
          query: { redirect: this.$route.fullPath, endpoint: name }
        })
      }
    },

    // Browser fullscreen tab: toggle browser-native fullscreen on the whole
    // browser-fullscreen container so the user can put the dashboard on a
    // large TV / projector without browser chrome.
    toggleBrowserFullscreen() {
      const el = this.$refs.browserFullscreenRef
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

    formatBytesPerSecond(bytes) {
      const n = Number(bytes) || 0
      if (n >= 1024 * 1024 * 1024) {
        return `${(n / (1024 * 1024 * 1024)).toFixed(2)} GB/s`
      }
      if (n >= 1024 * 1024) {
        return `${(n / (1024 * 1024)).toFixed(2)} MB/s`
      }
      if (n >= 1024) {
        return `${(n / 1024).toFixed(2)} KB/s`
      }
      return `${n.toFixed(0)} B/s`
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

    onIntervalChange(seconds) {
      // Track the interval (seconds; 0 = off) so the overview logs
      // group can sync its own auto-refresh timer.
      this.refreshIntervalSec = seconds
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
      this.longPressTimer = setTimeout(() => {
        this.enterEditMode(tab)
      }, LONG_PRESS_DURATION_MS)
    },

    onPanelPointerUp() {
      this._clearLongPressTimer()
    },

    _clearLongPressTimer() {
      if (this.longPressTimer) {
        clearTimeout(this.longPressTimer)
        this.longPressTimer = null
      }
    },

    enterEditMode(tab) {
      if (tab === 'overview') {
        if (this.isOverviewEditMode) return
        // Snapshot the current layout so "取消" can restore it later.
        this._editModeSnapshotOverview = JSON.parse(JSON.stringify(this.overviewLayout))
        this.isOverviewEditMode = true
      } else {
        if (this.isMetricsEditMode) return
        this._editModeSnapshotMetrics = JSON.parse(JSON.stringify(this.metricsLayout))
        this.isMetricsEditMode = true
      }
      this.$message.info(
        '已进入编辑模式，可拖动 / 调整面板大小。点击"完成"保存退出，点击"取消"放弃修改。'
      )
    },

    exitEditMode(tab) {
      if (tab === 'overview') {
        this.isOverviewEditMode = false
        this._editModeSnapshotOverview = null
      } else {
        this.isMetricsEditMode = false
        this._editModeSnapshotMetrics = null
      }
      this._saveLayout(tab)
      this.$message.success('布局已保存')
    },

    // Discard in-flight edits and leave edit mode without saving.
    // Restores the layout snapshot taken by enterEditMode().
    cancelEditMode(tab) {
      if (tab === 'overview') {
        if (this._editModeSnapshotOverview) {
          this.overviewLayout = this._editModeSnapshotOverview
          this._editModeSnapshotOverview = null
        }
        this.isOverviewEditMode = false
      } else {
        if (this._editModeSnapshotMetrics) {
          this.metricsLayout = this._editModeSnapshotMetrics
          this._editModeSnapshotMetrics = null
        }
        this.isMetricsEditMode = false
      }
      this.$message.info('已放弃布局修改')
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
          JSON.stringify({ v: LAYOUT_VERSION, layout })
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
        } else if (parsed && parsed.v === LAYOUT_VERSION && Array.isArray(parsed.layout)) {
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
        { i: 'group-os', x: 0, y: 0, w: 8, h: 22 },
        { i: 'group-node', x: 8, y: 0, w: 4, h: 22 },
        { i: 'group-alerts', x: 0, y: 22, w: 6, h: 10 },
        { i: 'group-logs', x: 6, y: 22, w: 6, h: 10 }
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
  /* Match .app-main / PageTable background so no seam shows between the
     container and the exposed area below short content. */
  background: var(--el-bg-color-page);
  padding: 20px;
  box-sizing: border-box;
  /* Fill the scrollable area so the page background never peeks
     through below short content (viewport minus the 50px navbar). */
  min-height: calc(100vh - 50px);
}

.header {
  margin: 0;
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-bottom: 16px;
}

/* feature-disabled banners (Prometheus / Alertmanager / VictoriaLogs) */
.feature-disabled-alert {
  margin-bottom: 10px;
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

.gauge-view-select {
  width: 78px;
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

/* When a gauge panel is toggled to history-chart mode the v-chart
   element replaces the el-progress ring. Force it to fill the same
   panel-body area so the layout doesn't jump. */
.gauge-chart {
  width: 100%;
  height: 100%;
  min-height: 0;
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

.edit-mode-cancel-btn {
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

/* SizedChart's host element must fill its parent even before the inner
   v-chart mounts. Inside flex containers that center their children
   (gauge panels, the fullscreen dialog), an empty host would otherwise
   collapse to 0x0 and the ResizeObserver inside SizedChart would never
   observe a non-zero size — deadlock. :deep() is required because
   .sized-chart-host is the root element of the child SizedChart
   component and does not carry this component's scoped attribute. */
.panel-body > :deep(.sized-chart-host),
.stat-content > :deep(.sized-chart-host),
.fullscreen-chart-container > :deep(.sized-chart-host) {
  align-self: stretch;
  flex: 1 1 auto;
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
  /* The dialog uses append-to-body, which teleports it to <body>. The
     scoped :deep() rule that used to give .el-dialog__body a fixed
     height could never match there (no ancestor carries this
     component's data-v attribute), so the body collapsed to auto
     height, this wrapper's height:100% resolved to 0 and the SizedChart
     host stayed 0px tall — the chart never mounted. Set a
     viewport-based height directly on the wrapper instead: 100vh minus
     the dialog's own padding (16px top + 16px bottom) and the header
     (24px title line + 16px padding-bottom). */
  height: calc(100vh - 72px);
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
  display: flex;
  align-items: center;
  justify-content: center;
}

/* SizedChart's host element must fill the whole flex container even
   before its inner v-chart mounts; otherwise an empty host collapses
   to 0x0 and the ResizeObserver inside SizedChart never fires. */
.fullscreen-chart-container > .sized-chart-host {
  align-self: stretch;
  flex: 1 1 auto;
  width: 100%;
  height: 100%;
}

/* Enlarged dashboard ring shown when a gauge panel is opened in the
   fullscreen dialog and the user keeps the "仪表盘" view. The container
   centers the ring + caption column via the flex parent. */
.fullscreen-gauge {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
}

.fullscreen-gauge-desc {
  font-size: 16px;
  color: var(--el-text-color-secondary);
  text-align: center;
}

.fullscreen-empty {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
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

/* ===== Browser fullscreen tab ===== */
.browser-fullscreen-container {
  background: var(--el-bg-color-page);
  padding: 4px 8px 8px;
  border-radius: 8px;
}

.browser-fullscreen-container:fullscreen {
  background: var(--el-bg-color-page);
  padding: 8px 16px 16px;
  overflow: auto;
}

.browser-fullscreen-toolbar {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
  margin-top: -4px;
}

.browser-fullscreen-endpoint {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-right: auto;
}

.browser-fullscreen-endpoint-label {
  font-size: 13px;
  color: var(--el-text-color-regular);
  white-space: nowrap;
}

.browser-fullscreen-endpoint-select {
  min-width: 200px;
}

/* Mirror the sidebar EndpointSwitcher's option layout / status dot so the
   browser-fullscreen selector looks identical to the one in the left sidebar.
   These styles need :deep() because the el-select dropdown popper is
   teleported inside the browser-fullscreen container (:teleported="false") but
   scoped CSS still doesn't reach the popper slot content reliably
   across Element Plus versions. */
.browser-fullscreen-endpoint-select :deep(.endpoint-option),
:deep(.endpoint-switcher-popper .endpoint-option) {
  display: flex;
  align-items: center;
  width: 100%;
  gap: 8px;
}

.browser-fullscreen-endpoint-select :deep(.endpoint-option-alias),
:deep(.endpoint-switcher-popper .endpoint-option-alias) {
  font-weight: 500;
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.browser-fullscreen-endpoint-select :deep(.endpoint-option-meta),
:deep(.endpoint-switcher-popper .endpoint-option-meta) {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  margin-left: auto;
}

.browser-fullscreen-endpoint-select :deep(.endpoint-option-version),
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

/* Overview logs group: the embedded LogsPanel ships a 480px min-height
   designed for the standalone logs tab; inside the compact overview
   grid cell the cell must fully control the height. */
.logs-group .logs-group-body {
  padding: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.logs-group :deep(.logs-panel) {
  min-height: 0;
  flex: 1;
  border: none;
  border-radius: 0;
}

/* tighten the logs toolbar / pagination inside the compact group */
.logs-group :deep(.logs-toolbar) {
  padding: 6px 8px;
}

.logs-group :deep(.logs-pagination) {
  padding: 4px 8px;
}

/* Panels hosted inside a GridItem (overview / metrics tabs) must ignore
   the page-level min-height so the grid cell fully controls the size;
   otherwise a too-tall panel overflows and visually covers the panels
   laid out below it (e.g. gauges overlapping the chart row). */
.chart-grid-item .panel-wrapper,
.chart-grid-item .stat-panel,
.chart-grid-item .gauge-panel,
.chart-grid-item .chart-panel,
.chart-grid-item .alert-panel,
.chart-grid-item .logs-group {
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

/* ===== 总览 tab：三个分组边框（操作系统指标 / 节点信息 / 告警列表） ===== */
.group-panel {
  border: 1px solid var(--el-border-color);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.group-panel .panel-header {
  background: var(--el-fill-color-light);
}

.group-subtitle {
  font-size: 12px;
  font-weight: 400;
  color: var(--el-text-color-secondary);
}

.group-body {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 8px;
  overflow: hidden;
  min-height: 0;
}

/* --- 分组 1：操作系统指标 --- */
.os-stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
}

.mini-stat {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 6px 10px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 6px;
  background: var(--el-bg-color);
  min-width: 0;
}

.mini-stat-label {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  white-space: nowrap;
}

.mini-stat-value {
  font-size: 20px;
  font-weight: 700;
  color: var(--el-text-color-primary);
  line-height: 1.1;
}

.mini-stat-value.primary {
  color: #409eff;
}

.mini-stat-value.warning {
  color: #e6a23c;
}

.mini-stat-value.success {
  color: #67c23a;
}

.mini-stat-value.danger {
  color: #f56c6c;
}

.os-proc-line {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.os-charts-row {
  flex: 1;
  display: grid;
  grid-template-columns: 1fr 1fr;
  /* Two rows of compact charts must share the space equally so the
     2x2 grid looks uniform; cap the total height so the group stays
     compact (each chart row is roughly half of ~300px). */
  grid-template-rows: repeat(2, 1fr);
  gap: 8px;
  min-height: 0;
}

.compact-chart-card {
  display: flex;
  flex-direction: column;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 6px;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
}

.compact-chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  padding: 4px 8px;
  border-bottom: 1px solid var(--el-border-color-lighter);
  flex-wrap: wrap;
  row-gap: 4px;
}

.compact-chart-header .panel-toolbar {
  flex-wrap: wrap;
  row-gap: 4px;
}

.compact-chart-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  white-space: nowrap;
}

.compact-chart-body {
  flex: 1;
  min-height: 0;
  padding: 4px;
}

.compact-chart-body > :deep(.sized-chart-host) {
  width: 100%;
  height: 100%;
}

/* 2x2 history line chart grid below the numeric chips; mirrors the OS
   group's chart grid (equal row heights, compact). */
.node-charts-row {
  flex: 1;
  display: grid;
  grid-template-columns: 1fr 1fr;
  grid-template-rows: repeat(2, 1fr);
  gap: 8px;
  min-height: 0;
}

.node-host-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}

.host-chip {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 6px 10px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 6px;
  min-width: 0;
}

.host-chip-label {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  white-space: nowrap;
}

.host-chip-value {
  font-size: 14px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.host-chip-value em {
  font-style: normal;
  font-size: 11px;
  color: var(--el-text-color-secondary);
}

@media (max-width: 1200px) {
  .os-stats-row {
    grid-template-columns: repeat(2, 1fr);
  }

  .os-charts-row {
    grid-template-columns: 1fr;
  }

  .node-charts-row {
    grid-template-columns: 1fr;
  }

  .node-host-grid {
    grid-template-columns: 1fr;
  }
}

</style>

<!-- Global (non-scoped) overrides for the endpoint-switcher popper: the
     dropdown is teleported into the fullscreen browser-fullscreen container via
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
.browser-fullscreen-endpoint .endpoint-state-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
  background: var(--el-color-info);
}

.endpoint-switcher-popper .endpoint-state-dot.state-ok,
.browser-fullscreen-endpoint .endpoint-state-dot.state-ok {
  background: var(--el-color-success);
}

.endpoint-switcher-popper .endpoint-state-dot.state-fail,
.browser-fullscreen-endpoint .endpoint-state-dot.state-fail {
  background: var(--el-color-danger);
}

.endpoint-switcher-popper .endpoint-state-dot.state-probing,
.browser-fullscreen-endpoint .endpoint-state-dot.state-probing {
  background: var(--el-color-info);
}
</style>
