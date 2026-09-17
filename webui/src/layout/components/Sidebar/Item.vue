<script>
import { h } from 'vue'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'

export default {
  name: 'MenuItem',
  props: {
    icon: {
      type: String,
      default: ''
    },
    title: {
      type: String,
      default: ''
    }
  },
  render() {
    const vnodes = []

    if (this.icon) {
      if (this.icon.includes('el-icon')) {
        // Convert el-icon-xxx to PascalCase component name
        // e.g. el-icon-s-home -> SHome, el-icon-upload -> Upload
        const iconName = this.icon.replace(/^el-icon-/, '')
        const pascalName = iconName
          .split('-')
          .map(s => s.charAt(0).toUpperCase() + s.slice(1))
          .join('')
        const IconComp = ElementPlusIconsVue[pascalName]
        if (IconComp) {
          vnodes.push(h(IconComp, { class: 'sub-el-icon' }))
        } else {
          vnodes.push(h('i', { class: [this.icon, 'sub-el-icon'] }))
        }
      } else {
        vnodes.push(h('svg-icon', { 'icon-class': this.icon }))
      }
    }

    if (this.title) {
      vnodes.push(h('span', { class: 'menu-title' }, [this.title]))
    }
    return vnodes
  }
}
</script>

<style scoped>
.sub-el-icon {
  color: currentColor;
  width: 1em;
  height: 1em;
}
</style>
