<!-- rabi.vue -->
<template>
  <BaseCalibration :config="paramsConfig" />
</template>

<script>
import { RABI_CONFIG } from '@/config/calibration-configs'
import BaseCalibration from '@/views/calibration/BaseCalibration.vue'
export default {
  components: { BaseCalibration },
  data() {
    return {
      paramsConfig: RABI_CONFIG
    }
  }
}
</script>
