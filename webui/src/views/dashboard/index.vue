<template>
  <div class="dashboard-container">
    <!-- 新增文字容器 -->
    <div class="image-caption">
      <h1 class="title">五岳量子计算操作系统</h1>
      <p class="subtitle">混沌宙元量子科学装置发布新一代量子计算基础设施</p>
    </div>

    <!-- 新增三栏信息容器 -->
    <div class="info-blocks">
      <div class="info-card">
        <h3 class="info-title">项目介绍</h3>
        <div class="info-content">
          <p>
            五岳量子计算操作系统是连接上层量子算法与下层量子硬件的桥梁，负责将量子算法转换为可在量子硬件上执行的指令，并管理和调度量子硬件资源。通过分层架构设计，有效解决了量子计算中的资源管理、任务调度、比特映射等挑战，提供稳定、可靠的量子计算服务。</p>
          <p>
            系统采用创新的多任务电路并行技术和智能调度算法，实现了量子资源的高效利用。同时，通过量子异构硬件管理引擎，支持包括中性原子、离子阱和光量子在内的多种量子硬件平台，并通过插件式架构实现灵活扩展。系统还集成了自动化校准机制和状态读取技术，确保量子操作的精确性和可靠性。</p>
          <p>
            五岳量子计算操作系统通过低阶编译器将高级量子算法描述转换为硬件可执行的脉冲序列，并应用高保真优化机制和误差缓解技术，最大限度地提高量子计算的保真度。该系统混沌宙元实验室量子研究场景中得到验证，为量子算法的实际应用提供了坚实基础。</p>
        </div>
      </div>

      <div class="info-card">
        <h3 class="info-title">系统概览</h3>
        <p class="info-content">系统状态 </p>
        <p class="info-content">正常运行中 </p>
        <p class="info-content">最大支持量子比特数目</p>
        <p class="info-content"><strong>100+</strong></p>
        <p class="info-content">支持多种量子硬件技术路线</p>
        <p class="check-item">中性原子</p>
        <p class="check-item">离子阱</p>
        <p class="check-item">超导量子比特</p>
        <p class="check-item">光量子</p>
      </div>

      <div class="info-card">
        <h3 class="info-title">系统优势</h3>
        <p class="check-item">支持接入多路线量子真机</p>
        <p class="check-item">智能调度与多任务并行处理</p>
        <p class="check-item">高保真优化机制</p>
        <p class="check-item">插件式驱动架构支持灵活扩展</p>
        <p class="check-item">标准接口兼容多种量子设备</p>
      </div>
    </div>
  </div>
</template>

<script>
import { useUserStore } from '@/store/modules/user'

export default {
  name: 'Dashboard',
  computed: {
    name() {
      const userStore = useUserStore()
      return userStore.name
    }
  }
}
</script>
</parameter>

<style lang="scss" scoped>
.dashboard-container {
  position: relative;
  min-height: 0vh;

  // 新增底层背景
  &::after {
    content: '';
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    z-index: -2; // 置于最底层
    background: url('~@/assets/background/6e04.png') no-repeat center/cover;
    opacity: 0.8; // 透明度调节
    filter: grayscale(30%); // 添加灰度滤镜
  }

  // 原有顶部背景
  &::before {
    z-index: -1; // 调整层级在底层背景之上
    content: '';
    position: absolute; // 使用绝对定位
    top: 0;
    left: 0;
    width: 100%;
    height: 120vh; // 图片占可视区域的40%
    min-height: 300px; // 最小高度限制

    background-image: url('~@/assets/background/5b49.png');
    background-size: cover;
    background-position: center top; // 图片顶部对齐
    background-repeat: no-repeat;
    background-color: white; // 图片区域的背景色
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
  max-width: 600px;

  .title {
    font-family: 'HarmonyOS Sans SC VF', sans-serif;
    font-size: 2.8rem;
    margin-bottom: 1rem;
    line-height: 1.2;
  }

  .subtitle {
    white-space: nowrap;
    font-family: SimSun, Songti SC, serif;
    font-size: 1.4rem;
    opacity: 0.9;
  }
}

.info-blocks {
  position: absolute;
  top: calc(20vh + 0px);
  left: 50%;
  transform: translateX(-50%);
  width: 95%;
  max-width: 1400px;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 30px;
  z-index: 2;

  .info-card {
    background: rgba(255, 255, 255, 0.95);
    border-radius: 12px;
    padding: 30px;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
    transition: transform 0.3s ease;

    &:hover {
      transform: translateY(-5px);
    }
  }

  .info-title {
    color: #2c3e50;
    font-size: 1.5rem;
    margin-bottom: 15px;
    border-bottom: 2px solid #409eff;
    padding-bottom: 10px;
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

.info-card:nth-child(2) { // 通过位置选择第二个卡片
  .info-content {
    font-size: 1.6em;

    &:nth-child(3) { // "正常运行中"
      font-size: 2.0em;
      color: #4CAF50;
      font-weight: 500;
    }

    &:nth-child(4) {
      margin-top: 1rem;
    }

    &:nth-child(6) {
      margin-top: 1rem;
    }

    /* 量子比特数强调 */
    strong {
      font-size: 1.8em;
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
      font-size: 3.5rem;
    }

    .subtitle {
      font-size: 1.8rem;
    }
  }
}
</style>
