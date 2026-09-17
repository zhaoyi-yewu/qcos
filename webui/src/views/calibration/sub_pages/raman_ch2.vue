<template>
  <BaseCalibration :config="paramsConfig" />
</template>

<script>
import { RAMAN_CH2_CONFIG } from '@/config/calibration-configs'
import BaseCalibration from '@/views/calibration/BaseCalibration.vue'
export default {
  components: { BaseCalibration },
  data() {
    return {
      paramsConfig: RAMAN_CH2_CONFIG
    }
  }
}
</script>
