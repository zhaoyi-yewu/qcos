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
  <div class="dashboard-container">
    <!-- 新增文字容器 -->
    <div class="image-caption">
      <div class="title-row">
        <h1 class="title">WUYUEQbit量子计算操作系统 (QCOS)</h1>
      </div>
      <p class="subtitle">开源通用量子计算操作系统 · 统一适配多种量子硬件架构</p>
    </div>

    <!-- 新增三栏信息容器 -->
    <div class="info-blocks">
      <div class="info-card">
        <h3 class="info-title">系统介绍</h3>
        <div class="info-content">
          <p>
            WUYUEQbit量子计算操作系统（QCOS）是一款开源的通用量子计算操作系统，作为连接上层量子算法与下层量子硬件的桥梁，负责将量子算法转换为可在量子硬件上执行的指令，并管理和调度量子硬件资源。通过分层架构设计，有效解决了量子计算中的资源管理、任务调度、比特映射等挑战，提供稳定、可靠的量子计算服务。</p>
          <p>
            系统采用多任务电路并行技术和智能调度算法，实现了量子资源的高效利用。同时，通过量子异构硬件管理引擎，支持包括超导、中性原子、离子阱、光量子、相干伊辛机和量子模拟器在内的多种量子硬件平台，并通过插件式架构实现灵活扩展。系统还集成了设备配置管理和状态读取技术，确保量子操作的精确性和可靠性。</p>
          <p>
            QCOS 通过量子引擎完成 QASM 解析、逻辑门分解、量子比特映射、编译优化、线路聚合与拆分等核心流程，将高级量子算法描述转换为硬件可执行的指令序列，并应用高保真优化机制和误差缓解技术，最大限度地提高量子计算的保真度。系统已在混沌宙元实验室量子研究场景中得到验证，为量子算法的实际应用提供了坚实基础。</p>
        </div>
      </div>

      <div class="info-card">
        <h3 class="info-title">系统概览</h3>
        <p class="info-content">系统状态：<span v-if="loading">检测中...</span><span v-else-if="systemHealthy" class="status-ok">正常运行</span><span v-else class="status-error">异常离线</span><span v-if="!systemHealthy" class="status-components"><span v-for="item in statusList" :key="item.name" class="comp-item">{{ item.name }}: <span :class="item.status === 'online' ? 'status-ok' : 'status-error'">{{ item.text }}</span></span></span></p>
        <p class="info-content">最大支持量子比特数目</p>
        <p class="info-content"><strong>100+</strong></p>
        <p class="info-content">支持多种量子硬件技术路线</p>
        <p class="check-item">超导量子比特</p>
        <p class="check-item">中性原子</p>
        <p class="check-item">离子阱</p>
        <p class="check-item">光量子</p>
        <p class="check-item">相干伊辛机</p>
        <p class="check-item">量子模拟器</p>
      </div>

      <div class="info-card">
        <h3 class="info-title">系统优势</h3>
        <p class="check-item">支持接入多路线量子真机</p>
        <p class="check-item">智能调度与多任务并行处理</p>
        <p class="check-item">高保真优化机制</p>
        <p class="check-item">插件式驱动架构支持灵活扩展</p>
        <p class="check-item">标准接口兼容多种量子设备</p>
        <p class="check-item">多租户隔离与RBAC权限控制</p>
        <p class="check-item">Prometheus监控告警与Grafana可视化</p>
      </div>
    </div>
  </div>
</template>

<script>
import logoImg from '@/assets/icons/wy_qcos_icon.png'
import { useUserStore } from '@/store/modules/user'
import { getSystemHealth } from '@/api/system'

export default {
  name: 'DashboardView',
  data() {
    return {
      logoImg,
      loading: true,
      systemHealthy: true,
      componentStatus: {}
    }
  },
  computed: {
    name() {
      const userStore = useUserStore()
      return userStore.name
    },
    statusList() {
      const statusMap = { online: '在线', offline: '离线' }
      const status = this.componentStatus
      const list = []
      const keys = ['fastapi', 'redis', 'prefect', 'worker']
      keys.forEach(key => {
        if (status[key]) {
          list.push({
            name: key,
            status: status[key],
            text: statusMap[status[key]] || status[key]
          })
        }
      })
      return list
    }
  },
  mounted() {
    this.fetchSystemHealth()
  },
  methods: {
    async fetchSystemHealth() {
      this.loading = true
      try {
        const response = await getSystemHealth()
        if (!response.error) {
          const result = response.result
          this.systemHealthy = result.system_healthy
          this.componentStatus = result.component_status || {}
        } else {
          this.systemHealthy = false
          this.componentStatus = {}
        }
      } catch (err) {
        this.systemHealthy = false
        this.componentStatus = {}
      } finally {
        this.loading = false
      }
    }
  }
}
</script>

<style lang="scss" scoped>
.dashboard-container {
  position: relative;
  overflow: hidden;
  min-height: calc(100vh - 50px);

  // bottom background layer
  &::after {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    z-index: -2;
    pointer-events: none;
    background: url('@/assets/background/6e04.png') no-repeat center/cover;
    opacity: 0.8;
  }

  // top background layer
  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 120vh;
    min-height: 300px;
    z-index: -1;
    pointer-events: none;
    background-image: url('@/assets/background/5b49.png');
    background-size: cover;
    background-position: center top;
    background-repeat: no-repeat;
  }
}

.content-wrapper {
  position: relative;
  z-index: 1;
  padding: 40px;
  margin-top: 40vh; // 从图片底部开始

  // 内容样式
  background: white;
  box-shadow: 0 0 30px rgba(0, 0, 0, 0.1);

  .dashboard-text {
    font-size: 2.5rem;
    color: #2c3e50;
  }
}

// 新增文字容器样式
.image-caption {
  position: absolute;
  top: 5%; // 垂直位置调整
  left: 8%; // 水平左对齐
  z-index: 2; // 确保在背景图上层
  color: #000; // 改为黑色
  text-shadow: 1px 1px 2px rgba(255, 255, 255, 0.5);
  max-width: 90%;

  .title-row {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .title {
    font-family: 'HarmonyOS Sans SC VF', sans-serif;
    font-size: 1.8rem;
    margin-bottom: 0.8rem;
    line-height: 1.2;
    // keep the long product name on a single line regardless of the
    // container width; otherwise "WUYUEQbit量子计算操作系统(QCOS)" wraps
    // into two lines once the container max-width is reached
    white-space: nowrap;
    // subtle two-layer shadow for a slight 3D lift: a tight darker offset
    // provides the "edge" while a larger soft blur adds depth
    text-shadow:
      0 1px 2px rgba(0, 0, 0, 0.25),
      0 4px 10px rgba(0, 0, 0, 0.18);
  }

  .title-logo {
    width: 36px;
    height: 36px;
    vertical-align: middle;
    margin-bottom: 0.8rem;
  }

  .subtitle {
    white-space: nowrap;
    font-family: SimSun, Songti SC, serif;
    font-size: 1.1rem;
    opacity: 0.9;
  }
}

.info-blocks {
  position: absolute;
  top: calc(15vh + 40px);
  left: 50%;
  transform: translateX(-50%);
  width: 95%;
  max-width: 1400px;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
  z-index: 2;

  .info-card {
    background: rgba(255, 255, 255, 0.95);
    border-radius: 12px;
    padding: 12px 16px;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
    transition: transform 0.3s ease;

    &:hover {
      transform: translateY(-5px);
    }
  }

  .info-title {
    color: #2c3e50;
    font-size: 1.5rem;
    margin-bottom: 8px;
    border-bottom: 2px solid #409eff;
    padding-bottom: 6px;
  }

  .info-content {
    /* 基础排版设置 */
    text-align: justify; // 两端对齐
    hyphens: auto; // 自动断词
    word-wrap: break-word; // 允许单词内断行
    word-break: break-word; // 中文换行处理

    /* 字符数控制 */
    max-width: 70ch; // 限制每行约70个字符（英文）
    margin: 0 auto; // 居中显示

    /* 中文排版优化 */
    line-height: 1.5; // 增加行高
    letter-spacing: 0.03em; // 微调字间距
    text-justify: inter-ideograph; // 汉字两端对齐

    /* 段落缩进处理 */
    p {
      text-indent: 2em;
    }

    /* 强调文本样式 */
    strong {
      color: #409eff;
      font-weight: 600;
      letter-spacing: 0.05em;
    }
  }
}

.info-card:nth-child(2) { // select the second card by position
  .info-content {
    font-size: 1.1em;

    // system status line
    .status-ok {
      color: #4CAF50;
      font-weight: 500;
    }

    .status-error {
      color: #F56C6C;
    }

    .status-components {
      display: block;
      margin-top: 0.3em;
      font-size: 0.9em;
      word-break: break-all;

      .comp-item {
        display: inline-block;
        margin-right: 0.8em;

        &:last-child {
          margin-right: 0;
        }
      }
    }

    &:nth-child(3) {
      margin-top: 0.6rem;
    }

    &:nth-child(5) {
      margin-top: 0.6rem;
    }

    /* quantum bit count emphasis */
    strong {
      font-size: 1.2em;
      vertical-align: middle;
    }
  }
}

.check-item {
  position: relative;
  padding-left: 1.5em;
  text-indent: 0;
  font-size: 1.3em;
  margin: 0.8em 0em;
  line-height: 1.6;

  &::before {
    content: "✓";
    position: absolute;
    left: 0;
    color: #4CAF50;
    font-weight: 700;
    font-size: 1.3em;
  }
}

/* 响应式调整 */
@media (min-width: 768px) {
  .image-caption {
    left: 10% !important;

    .title {
      font-size: 2.2rem;
    }

    .subtitle {
      font-size: 1.3rem;
    }
  }
}
</style>

<!-- Dark-mode adaptations. NOT scoped so the html.dark ancestor selector
     can reach the dashboard. All rules are wrapped in html.dark so the
     light (白天) theme keeps its original colors untouched. -->
<style lang="scss">
html.dark {
  .dashboard-container {
    // darken the two background image layers so white text remains readable
    &::after,
    &::before {
      filter: brightness(0.35) saturate(0.7);
    }
  }

  // headline + subtitle on top of the background image
  .dashboard-container .image-caption {
    color: #f5f7fa;
    text-shadow: 1px 1px 3px rgba(0, 0, 0, 0.7);
  }

  // info cards: switch from light frosted glass to a dark translucent panel
  .dashboard-container .info-blocks .info-card {
    background: rgba(20, 22, 28, 0.85);
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.6);
  }

  .dashboard-container .info-blocks .info-title {
    color: #e5e7eb;
    border-bottom-color: var(--el-color-primary);
  }

  .dashboard-container .info-blocks .info-content {
    color: #d4d7de;

    strong {
      color: var(--el-color-primary-light-3);
    }
  }

  .dashboard-container .check-item {
    color: #d4d7de;

    &::before {
      color: #67c23a;
    }
  }

  // status indicators: keep the semantic colors but bump brightness so
  // they remain legible on the dark card background
  .dashboard-container .info-card:nth-child(2) .info-content {
    .status-ok {
      color: #7dd88a;
    }

    .status-error {
      color: #f89898;
    }
  }
}
</style>
