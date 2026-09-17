<template>
  <BaseCalibration :config="paramsConfig" />
</template>

<script>
import { ARRANGE_CH1_CONFIG } from '@/config/calibration-configs'
import BaseCalibration from '@/views/calibration/BaseCalibration.vue'

export default {
  components: { BaseCalibration },
  data() {
    return {
      paramsConfig: ARRANGE_CH1_CONFIG
    }
  }
}
</script>
