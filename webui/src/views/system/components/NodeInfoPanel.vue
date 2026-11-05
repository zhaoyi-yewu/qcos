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
  <div class="node-info-panel">
    <!-- Toolbar: time range + refresh -->
    <div class="node-info-toolbar">
      <el-select
        v-model="timeRange"
        size="small"
        class="time-range-select"
        @change="onSearch"
      >
        <el-option
          v-for="opt in TIME_RANGE_OPTIONS"
          :key="opt.value"
          :label="opt.label"
          :value="opt.value"
        />
      </el-select>

      <el-button
        size="small"
        :icon="Refresh"
        circle
        :loading="loading"
        @click="onSearch"
      />
    </div>

    <!-- Chart grid: two columns, one card per metric family -->
    <div class="node-info-grid">
      <div
        v-for="panel in panels"
        :key="panel.id"
        class="node-info-card"
      >
        <div class="card-header">
          <span class="card-title">{{ panel.title }}</span>
          <el-tag v-if="panel.unit" size="small" type="info">{{ panel.unit }}</el-tag>
        </div>
        <!-- Empty/error hint overlays the chart area, centered both
             ways, so "暂无数据" / "查询失败" reads as part of the panel. -->
        <div class="card-chart">
          <sized-chart :option="panel.option" autoresize />
          <div v-if="panel.empty" class="card-empty">
            {{ panel.emptyText }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { Refresh } from '@element-plus/icons-vue'
import { queryPrometheusRange } from '@/api/monitor'
import SizedChart from '@/components/SizedChart/index.vue'

const TIME_RANGE_OPTIONS = [
  { label: '近 15 分钟', value: 15 * 60 },
  { label: '近 30 分钟', value: 30 * 60 },
  { label: '近 1 小时', value: 60 * 60 },
  { label: '近 6 小时', value: 6 * 60 * 60 },
  { label: '近 24 小时', value: 24 * 60 * 60 }
]

// Chart color palette, aligned with the monitor-center palette so the
// two tabs look consistent.
const SERIES_COLORS = [
  '#409EFF', '#67C23A', '#E6A23C', '#F56C6C',
  '#8e71f1', '#36CBCB', '#F6903D', '#00B0FF'
]

/**
 * PromQL definitions per panel. A panel may run several queries; the
 * resulting series are merged into one chart (legend shows one line
 * per splitLabel value, or per `seriesName` when set explicitly).
 */
// Row 1: node CPU usage  |  process CPU (per feedback)
// Row 2: memory usage %  |  memory total/used MB
// Row 3/4: network + disk panels. The two-column grid renders the
// panels in array order, so this layout is purely the def order.
const PANEL_DEFS = [
  {
    id: 'cpu-usage',
    title: '节点 CPU 使用率',
    unit: '%',
    splitLabel: 'instance',
    // Idle-average complement over all cores per node.
    query:
      '100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[2m])) * 100)'
  },
  {
    id: 'proc-cpu',
    title: '主机进程 CPU 耗时',
    unit: 'cores',
    splitLabel: 'groupname',
    // process-exporter: CPU seconds per second per process group,
    // top 8 groups only to keep the chart readable.
    query:
      'topk(8, sum by (groupname) (rate(namedprocess_namegroup_cpu_seconds_total[2m])))'
  },
  {
    id: 'mem-bytes',
    title: '节点内存空间',
    unit: 'GB',
    splitLabel: 'instance',
    queries: [
      {
        // Total memory per node in GB.
        seriesName: '总内存',
        splitLabel: 'instance',
        query: 'node_memory_MemTotal_bytes / 1024 / 1024 / 1024'
      },
      {
        // Used memory (total - available) per node in GB.
        seriesName: '已用内存',
        splitLabel: 'instance',
        query:
          '(node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / 1024 / 1024 / 1024'
      }
    ]
  },
  {
    id: 'mem-usage',
    title: '节点内存使用率',
    unit: '%',
    splitLabel: 'instance',
    query:
      '100 * (1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)'
  },
  {
    id: 'net-recv',
    title: '网络接收速率',
    unit: 'bytes/s',
    splitLabel: 'instance',
    // Sum over physical interfaces per node (loopback/veth excluded).
    query:
      'sum by (instance) (rate(node_network_receive_bytes_total{device!~"lo|veth.*"}[2m]))'
  },
  {
    id: 'net-send',
    title: '网络发送速率',
    unit: 'bytes/s',
    splitLabel: 'instance',
    query:
      'sum by (instance) (rate(node_network_transmit_bytes_total{device!~"lo|veth.*"}[2m]))'
  },
  {
    id: 'disk-space',
    title: '磁盘空间',
    unit: 'GB',
    // Absolute sizes in GB: the whole-disk totals plus one series per
    // partition mountpoint, so the numbers read like `df -h` output.
    splitLabel: 'mountpoint',
    queries: [
      {
        // Whole-disk total across all non-pseudo filesystems.
        seriesName: '整盘总量',
        splitLabel: 'instance',
        query:
          'sum by (instance) (node_filesystem_size_bytes{fstype!~"tmpfs|overlay|squashfs"}) / 1024 / 1024 / 1024'
      },
      {
        // Whole-disk used (size - avail) across all filesystems.
        seriesName: '整盘已用',
        splitLabel: 'instance',
        query:
          'sum by (instance) (node_filesystem_size_bytes{fstype!~"tmpfs|overlay|squashfs"} - node_filesystem_avail_bytes{fstype!~"tmpfs|overlay|squashfs"}) / 1024 / 1024 / 1024'
      },
      {
        // Per-partition total, one series per mountpoint.
        seriesName: '总量',
        splitLabel: 'mountpoint',
        query:
          'node_filesystem_size_bytes{fstype!~"tmpfs|overlay|squashfs"} / 1024 / 1024 / 1024'
      },
      {
        // Per-partition used, one series per mountpoint.
        seriesName: '已用',
        splitLabel: 'mountpoint',
        query:
          '(node_filesystem_size_bytes{fstype!~"tmpfs|overlay|squashfs"} - node_filesystem_avail_bytes{fstype!~"tmpfs|overlay|squashfs"}) / 1024 / 1024 / 1024'
      }
    ]
  },
  {
    id: 'disk-usage',
    title: '磁盘使用率',
    unit: '%',
    // Usage ratio per partition mountpoint (/, /home, /var, ...),
    // one line per partition.
    splitLabel: 'mountpoint',
    query:
      '100 * (1 - node_filesystem_avail_bytes{fstype!~"tmpfs|overlay|squashfs"} / node_filesystem_size_bytes{fstype!~"tmpfs|overlay|squashfs"})'
  },
  {
    id: 'disk-io',
    title: '磁盘读写速率',
    unit: 'bytes/s',
    splitLabel: 'instance',
    // Read + write combined per node; read/write split shown in the
    // series legend via the legend formatter.
    query:
      'sum by (instance) (rate(node_disk_read_bytes_total[2m])) + sum by (instance) (rate(node_disk_written_bytes_total[2m]))'
  }
]

export default {
  name: 'NodeInfoPanel',
  components: { SizedChart },
  data() {
    return {
      Refresh,
      TIME_RANGE_OPTIONS,
      timeRange: 30 * 60,
      loading: false,
      panels: PANEL_DEFS.map(def => ({
        ...def,
        option: this.buildEmptyOption(def.title),
        empty: true,
        emptyText: '暂无数据'
      }))
    }
  },
  computed: {
    // Auto step: keep the point count under Prometheus's 11000 limit,
    // same heuristic as the monitor-center chart panels.
    stepSeconds() {
      const points = 300
      return Math.max(5, Math.floor(this.timeRange / points))
    }
  },
  mounted() {
    this.onSearch()
  },
  methods: {
    /**
     * Build an ECharts line-chart option from Prometheus range series.
     *
     * @param {string} title - panel title
     * @param {Array} seriesData - [{name, points: [[ts, value], ...]}]
     * @param {string} unit - y-axis unit label
     */
    buildLineOption(title, seriesData, unit) {
      return {
        title: { text: '', left: 0 },
        tooltip: {
          trigger: 'axis',
          valueFormatter: v => this.formatValue(v, unit)
        },
        legend: {
          type: 'scroll',
          bottom: 0,
          textStyle: { fontSize: 11 }
        },
        grid: { left: 50, right: 16, top: 16, bottom: 34 },
        xAxis: {
          type: 'time',
          axisLabel: { formatter: '{HH}:{mm}' }
        },
        yAxis: {
          type: 'value',
          axisLabel: {
            formatter: v => this.formatValue(v, unit)
          }
        },
        color: SERIES_COLORS,
        series: seriesData.map(s => ({
          name: s.name,
          type: 'line',
          showSymbol: false,
          smooth: true,
          data: s.points
        }))
      }
    },

    /** Empty-state option (axes only, so the chart renders a frame). */
    buildEmptyOption(title) {
      return this.buildLineOption(title, [], '')
    },

    /**
     * Human-friendly value formatting per unit family: percentages
     * keep 1 decimal, byte rates scale to KB/MB/GB, and the mixed
     * memory panel renders % series vs MB series by magnitude
     * (percentages never exceed 100, MB totals do).
     */
    formatValue(v, unit) {
      if (v === null || v === undefined || Number.isNaN(v)) return '-'
      if (unit === '%') return `${Number(v).toFixed(1)}%`
      if (unit === 'mixed') {
        return Math.abs(v) > 100
          ? `${Number(v).toFixed(0)} MB`
          : `${Number(v).toFixed(1)}%`
      }
      if (unit === 'bytes/s') {
        const n = Number(v)
        if (n >= 1024 ** 3) return `${(n / 1024 ** 3).toFixed(2)} GB/s`
        if (n >= 1024 ** 2) return `${(n / 1024 ** 2).toFixed(2)} MB/s`
        if (n >= 1024) return `${(n / 1024).toFixed(2)} KB/s`
        return `${n.toFixed(0)} B/s`
      }
      if (unit === 'cores') return Number(v).toFixed(2)
      return Number(v).toFixed(2)
    },

    /**
     * Convert one Prometheus range-query result into chart series.
     * Each result entry becomes one series named "<instance> - <seriesName>"
     * (instance part dropped in single-node deployments for a compact
     * legend like "使用率" / "总内存" / "已用内存").
     */
    toSeries(result, splitLabel, seriesName) {
      const series = []
      const entries = (result && result.result) || []
      for (const entry of entries) {
        const label = (entry.metric || {})[splitLabel]
        const name = seriesName
          ? (label ? `${label} - ${seriesName}` : seriesName)
          : (label || entry.metric.instance || 'series')
        series.push({
          name,
          points: (entry.values || []).map(([ts, v]) => [
            ts * 1000,
            Number(v)
          ])
        })
      }
      return series
    },

    /**
     * Collect the effective query list for a panel: panels may declare
     * a single `query` or multiple `queries` (each with its own
     * seriesName/splitLabel), merged into one chart.
     */
    panelQueries(panel) {
      if (Array.isArray(panel.queries) && panel.queries.length > 0) {
        return panel.queries
      }
      if (panel.query) {
        return [{
          query: panel.query,
          splitLabel: panel.splitLabel,
          seriesName: ''
        }]
      }
      return []
    },

    async fetchPanel(panel) {
      const end = Math.floor(Date.now() / 1000)
      const start = end - this.timeRange
      try {
        // The axios wrapper unwraps the HTTP envelope, so each resolved
        // value IS the Prometheus JSON body: {status, data: {result}}.
        // monitor_center reads the same shape via extractMultiTimeSeries.
        const responses = await Promise.all(
          this.panelQueries(panel).map(q =>
            queryPrometheusRange(q.query, start, end, this.stepSeconds)
              .then(resp => {
                const ok = resp && resp.status === 'success' && resp.data
                return this.toSeries(
                  ok ? resp.data : null,
                  q.splitLabel,
                  q.seriesName
                )
              })
              .catch(err => {
                console.error(`获取 ${panel.title} 数据失败:`, err)
                return []
              })
          )
        )
        const series = responses.flat()
        panel.empty = series.length === 0
        panel.emptyText = '暂无数据'
        panel.option = this.buildLineOption(panel.title, series, panel.unit)
      } catch (error) {
        console.error(`获取 ${panel.title} 数据失败:`, error)
        panel.empty = true
        panel.emptyText = '查询失败'
        panel.option = this.buildEmptyOption(panel.title)
      }
    },

    async onSearch() {
      this.loading = true
      try {
        await Promise.all(this.panels.map(p => this.fetchPanel(p)))
      } finally {
        this.loading = false
      }
    }
  }
}
</script>

<style scoped>
.node-info-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--el-bg-color);
  border-radius: 8px;
  overflow: hidden;
}

.node-info-toolbar {
  display: flex;
  gap: 8px;
  padding: 12px;
  border-bottom: 1px solid var(--el-border-color-light);
  align-items: center;
}

.time-range-select {
  width: 140px;
}

.node-info-grid {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  padding: 12px;
}

.node-info-card {
  display: flex;
  flex-direction: column;
  min-height: 260px;
  border: 1px solid var(--el-border-color-light);
  border-radius: 6px;
  background: var(--el-fill-color-blank);
  overflow: hidden;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.card-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.card-chart {
  position: relative;
  flex: 1;
  min-height: 200px;
  padding: 4px;
}

/* Centered overlay for the empty/error hint, covering the chart. */
.card-empty {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--el-text-color-secondary);
  font-size: 13px;
  pointer-events: none;
  background: var(--el-mask-color, rgba(255, 255, 255, 0.6));
}
</style>
