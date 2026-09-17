<template>
  <div class="monitor-container">
    <div
      v-for="(item, index) in indicators"
      :key="item.type"
      class="indicator-column"
      :class="{ 'loading': loadingStatus[index] }"
    >
      <!-- 上方当前数据以仪表盘的形式表示 -->
      <div class="indicator-card">
        <h3 class="indicator-title">{{ item.name }}</h3>
        <template v-if="!loadingStatus[index]">
          <div :ref="'gauge'+index" class="gauge-container" />
          <div class="indicator-value-container">
            <div class="indicator-value">
              {{ currentValues[index] }}
              <span class="unit">{{ item.unit }}</span>
            </div>
          </div>
          <div class="status" :style="getStatusStyle(item)" />
        </template>
        <div v-else class="loading-text">数据加载中...</div>
      </div>
      <!-- 下方历史数据图表 -->
      <div :ref="'chart'+index" class="chart-container" />
    </div>
  </div>
</template>

<script>
import * as echarts from 'echarts'
import { getEnvironmentInfo } from '@/api/job'

export default {
  data() {
    return {
      indicators: [
        { type: 'temperature', name: '温度', unit: '℃', status: 0, min: 0, max: 50 },
        { type: 'humidity', name: '湿度', unit: '%RH', status: 1, min: 0, max: 50 },
        { type: 'electric_field', name: '电场', unit: 'kV/m', status: 2, min: 0, max: 50 },
        { type: 'magnetic_field', name: '磁场', unit: 'μT', status: 3, min: 0, max: 50 }
      ],
      colors: ['#5470C6', '#EE6666', '#FAC858', '#73C0DE'],
      charts: [],
      gauges: [],
      currentValues: [0, 0, 0, 0],
      loadingStatus: [true, true, true, true],
      refreshInterval: null
    }
  },
  mounted() {
    this.initCharts()
    this.startAutoRefresh()
    window.addEventListener('resize', this.handleResize)
  },
  beforeUnmount() {
    clearInterval(this.refreshInterval)
    window.removeEventListener('resize', this.handleResize)
    this.charts.forEach(chart => chart.dispose())
    this.gauges.forEach(gauge => gauge.dispose())
  },
  methods: {
    async initCharts() {
      try {
        const requests = this.indicators.map((item, index) =>
          this.fetchChartData(item.type, index)
        )
        await Promise.all(requests)
      } catch (error) {
        console.error('初始化失败:', error)
      }
    },

    async fetchChartData(type, index) {
      try {
        const { data } = await getEnvironmentInfo(type)
        const currentValue = parseFloat(data.current_val.toFixed(1))

        this.currentValues[index] = currentValue

        this.$nextTick(() => {
          if (!this.gauges[index]) {
            this.initGauge(index, currentValue)
          } else {
            this.updateGauge(index, currentValue)
          }

          const chartData = data.history.map(item => [item.timestamp, item.value])
          if (!this.charts[index]) {
            this.initChart(index, chartData)
          } else {
            this.updateChart(index, chartData)
          }
        })
        this.loadingStatus[index] = false
      } catch (error) {
        console.error(`[${type}] 数据加载失败:`, error)
        this.loadingStatus[index] = false
      }
    },

    initChart(index, data) {
      this.$nextTick(() => {
        const chartRefs = this.$refs[`chart${index}`]
        const chartDom = Array.isArray(chartRefs) ? chartRefs[0] : chartRefs
        if (!chartDom) return

        const chart = echarts.init(chartDom)

        const option = {
          title: {
            text: `${this.indicators[index].name}趋势`,
            top: 20,
            left: 'center',
            textStyle: {
              fontSize: 18,
              fontWeight: 500
            }
          },
          tooltip: {
            trigger: 'axis',
            formatter: params => {
              return `时间戳: ${params[0].value[0]}<br/>数值: ${params[0].value[1]} ${this.indicators[index].unit}`
            }
          },
          xAxis: {
            type: 'value',
            name: '时间(h)',
            nameLocation: 'middle',
            nameGap: 25,
            axisLabel: {
              show: true,
              color: '#666',
              formatter: (value) => {
                return `${value}h`
              }
            },
            min: (value) => Math.floor(value.min + 1),
            max: (value) => Math.ceil(value.max + 1)
          },
          yAxis: {
            type: 'value',
            name: `${this.indicators[index].name}(${this.indicators[index].unit})`,
            axisLabel: {
              formatter: `{value}`
            }
          },

          grid: { top: 80, bottom: 50, left: 50, right: 40 },
          series: [{
            name: this.indicators[index].name,
            type: 'line',
            smooth: true,
            symbol: 'none',
            itemStyle: { color: this.colors[index] },
            areaStyle: {
              color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: this.colors[index] + '99' },
                { offset: 1, color: this.colors[index] + '11' }
              ])
            },
            data: data.sort((a, b) => a[0] - b[0])
          }]
        }

        chart.setOption(option)
        this.charts[index] = chart
      })
    },

    initGauge(index, value) {
      this.$nextTick(() => {
        const gaugeRefs = this.$refs[`gauge${index}`]
        const gaugeDom = Array.isArray(gaugeRefs) ? gaugeRefs[0] : gaugeRefs
        if (!gaugeDom) return

        const gauge = echarts.init(gaugeDom)
        const indicator = this.indicators[index]

        const option = {
          series: [{
            type: 'gauge',
            center: ['50%', '55%'],
            startAngle: 180,
            endAngle: 0,
            min: indicator.min,
            max: indicator.max,
            splitNumber: 2, // 仅显示首尾刻度
            radius: '100%',
            axisLine: {
              lineStyle: {
                width: 12,
                color: [[1, '#F0F2F5']],
                cap: 'round'
              }
            },
            progress: {
              show: true,
              width: 12,
              roundCap: true,
              itemStyle: {
                // color: '#1E88E5'
                color: this.colors[index]
              }
            },
            pointer: {
              show: false
            },
            axisTick: {
              show: false
            },
            splitLine: {
              length: 6,
              lineStyle: {
                width: 2,
                color: '#E0E0E0',
                cap: 'round'
              }
            },
            axisLabel: {
              color: '#90A4AE',
              fontSize: 12,
              distance: 15,
              formatter: (value) => value === indicator.min || value === indicator.max ? value : ''
            },
            detail: {
              fontSize: 18,
              fontWeight: 300,
              offsetCenter: [0, '0%'],
              color: '#263238',
              formatter: `{value} ${indicator.unit}`,
              valueAnimation: {
                duration: 300,
                easing: 'cubicOut' // 平滑动画
              }
            },
            data: [{ value }]
          }]
        }

        gauge.setOption(option)
        this.gauges[index] = gauge
      })
    },

    updateChart(index, data) {
      const chart = this.charts[index]
      chart.setOption({
        series: [{
          data: data
        }]
      })
      chart.resize()
    },

    updateGauge(index, value) {
      const gauge = this.gauges[index]
      gauge.setOption({
        series: [{
          data: [{
            value: value
          }]
        }]
      })
    },

    startAutoRefresh() {
      this.refreshInterval = setInterval(() => {
        this.indicators.forEach((item, index) => {
          this.fetchChartData(item.type, index)
        })
      }, 10000) // 每10秒刷新一次
    },

    getStatusStyle(item) {
      const colors = ['#5470C6', '#EE6666', '#FAC858', '#73C0DE']
      return {
        backgroundColor: colors[item.status],
        boxShadow: `0 0 8px ${colors[item.status]}66`
      }
    },

    handleResize() {
      this.charts.forEach(chart => chart?.resize())
      this.gauges.forEach(gauge => gauge?.resize())
    }
  }
}
</script>

<style scoped>
  .loading-text {
    color: #909399;
    text-align: center;
    padding: 20px 0;
  }

  .indicator-column.loading {
    background: #f5f7fa;
    animation: pulse 1.5s infinite;
  }

  @keyframes pulse {
    0% {
      opacity: 0.6;
    }

    50% {
      opacity: 1;
    }

    100% {
      opacity: 0.6;
    }
  }

  .monitor-container {
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: 20px;
    padding: 20px;
    min-height: 100vh;
    box-sizing: border-box;
    background: #f5f7fa;
  }

  .indicator-column {
    flex: 1 1 300px;
    max-width: 400px;
    display: flex;
    flex-direction: column;
    gap: 15px;
  }

  .indicator-card {
    background: white;
    border-radius: 8px;
    padding: 20px;
    position: relative;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.05);
    min-height: 250px;
    display: flex;
    flex-direction: column;
  }

  .indicator-title {
    color: #909399;
    font-size: 18px;
    margin-bottom: 8px;
  }

  .gauge-container {
    width: 100%;
    flex: 1;
    min-height: 200px;
    position: relative;
  }

  .indicator-value-container {
    text-align: center;
    margin-top: -10px;
    z-index: 2;
  }

  .indicator-value {
    font-size: clamp(18px, 2vw, 24px);
    font-weight: 600;
    color: #303133;
  }

  .unit {
    font-size: clamp(10px, 1.2vw, 12px);
  }

  .status {
    position: absolute;
    left: 60px;
    top: 43px;
    width: 8px;
    height: 8px;
    border-radius: 50%;
  }

  .chart-container {
    width: 100%;
    height: 500px;
    background: white;
    border-radius: 8px;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.05);
    overflow: auto;
  }

  /*禁止用户缩放（增强布局稳定性） */
  body {
    touch-action: pan-x pan-y;
    -webkit-text-size-adjust: 100%;
  }
</style>
