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

<!--
  SizedChart: wrapper around vue-echarts that defers mounting until the
  host element has a non-zero size. ECharts aborts with "Can't get DOM
  width or height" when initialised against a 0x0 container — common
  inside grid layouts / lazy tabs / fullscreen dialogs that animate
  open from 0 size. We observe the wrapper with ResizeObserver and only
  render <v-chart> once real dimensions are available.
-->
<template>
  <div ref="hostRef" class="sized-chart-host">
    <v-chart
      v-if="ready"
      class="sized-chart"
      :option="option"
      :autoresize="true"
    />
  </div>
</template>

<script>
import VChart from 'vue-echarts'

export default {
  name: 'SizedChart',
  components: { VChart },
  props: {
    option: {
      type: Object,
      required: true
    }
  },
  data() {
    return {
      ready: false
    }
  },
  mounted() {
    // Fast path: the element already has a size (common when the parent
    // was laid out before this component mounted). Skip the observer.
    const el = this.$refs.hostRef
    if (!el) return
    if (el.clientWidth > 0 && el.clientHeight > 0) {
      this.ready = true
      return
    }
    // Second-chance fast path: when this component is mounted in the
    // same tick that its parent finished a CSS transition (e.g. the
    // monitor-center fullscreen dialog mounts <sized-chart> from
    // @opened), the browser may not have flushed layout yet, so
    // clientWidth/Height still read as 0 even though the final size
    // is non-zero. A double-rAF lets the browser paint one frame and
    // we re-check. Without this, the ResizeObserver below can end up
    // as the only signal and, on some browsers, misses the initial
    // 0 -> final transition, leaving the chart blank forever.
    this._rafId = requestAnimationFrame(() => {
      this._rafId = requestAnimationFrame(() => {
        this._rafId = null
        if (this.ready || !this.$refs.hostRef) return
        const { clientWidth, clientHeight } = this.$refs.hostRef
        if (clientWidth > 0 && clientHeight > 0) {
          this.ready = true
          this._disconnectObserver()
        }
      })
    })
    // Slow path: wait for the first non-zero layout. ResizeObserver
    // fires whenever the host's content rect changes, including the
    // transition from 0x0 to its final size.
    this._ro = new ResizeObserver(entries => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect
        if (width > 0 && height > 0) {
          this.ready = true
          this._disconnectObserver()
          return
        }
      }
    })
    this._ro.observe(el)
    // Window-resize fallback: dialogs / drawers that finish their
    // open animation *without* changing the host's contentRect
    // (e.g. transform-only transitions, or hosts whose size is
    // determined by an ancestor the observer cannot see) would
    // otherwise leave `ready` stuck at false. A cheap window-resize
    // listener gives the component one more chance to flip ready.
    this._onWindowResize = () => {
      if (this.ready || !this.$refs.hostRef) return
      const { clientWidth, clientHeight } = this.$refs.hostRef
      if (clientWidth > 0 && clientHeight > 0) {
        this.ready = true
        this._teardownWatchers()
      }
    }
    window.addEventListener('resize', this._onWindowResize)
  },
  beforeUnmount() {
    this._teardownWatchers()
    if (this._rafId) {
      cancelAnimationFrame(this._rafId)
      this._rafId = null
    }
  },
  methods: {
    _disconnectObserver() {
      if (this._ro) {
        this._ro.disconnect()
        this._ro = null
      }
    },
    _teardownWatchers() {
      this._disconnectObserver()
      if (this._onWindowResize) {
        window.removeEventListener('resize', this._onWindowResize)
        this._onWindowResize = null
      }
    }
  }
}
</script>

<style scoped>
.sized-chart-host {
  width: 100%;
  height: 100%;
  min-height: 0;
  min-width: 0;
  /* When placed inside a flex container (e.g. the fullscreen dialog's
     .fullscreen-chart-container uses display:flex + align/justify
     center), an empty host would be collapsed to 0x0 and the
     ResizeObserver would never fire — deadlock. align-self:stretch
     lets the host fill the cross axis even before the chart mounts,
     and align/justify-self behave consistently across browsers. */
  align-self: stretch;
  flex: 1 1 auto;
}

.sized-chart {
  width: 100%;
  height: 100%;
}
</style>
