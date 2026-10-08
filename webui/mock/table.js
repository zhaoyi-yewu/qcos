// Mock data generation without mockjs dependency.
// The random data here is generated at module load time, so
// restarting the dev server will produce new values.

function randomId() {
  return Math.floor(Math.random() * 100000 + 1024).toString()
}

function randomSentence(min, max) {
  const words = 'abcdefghijklmnopqrstuvwxyz'
  const len = Math.floor(Math.random() * (max - min) + min)
  let str = ''
  for (let i = 0; i < len; i++) {
    str += words.charAt(Math.floor(Math.random() * words.length))
  }
  return str
}

function randomItem(arr) {
  return arr[Math.floor(Math.random() * arr.length)]
}

function randomInt(min, max) {
  return Math.floor(Math.random() * (max - min + 1) + min)
}

function randomDatetime() {
  const d = new Date(Date.now() - randomInt(0, 30) * 24 * 3600 * 1000)
  return d.toISOString().replace('T', ' ').substring(0, 19)
}

function buildItems(count, titlePrefix) {
  const items = []
  for (let i = 0; i < count; i++) {
    items.push({
      id: randomId(),
      title: `${titlePrefix}_${randomSentence(10, 20)}`,
      status: randomItem(['published', 'draft', 'deleted']),
      author: 'name',
      display_time: randomDatetime(),
      pageviews: randomInt(300, 5000)
    })
  }
  return items
}

const data = {
  items: buildItems(2, 'table_k8s_cluster')
}

const dataForSimulationTask = {
  items: buildItems(30, 'table_k8s_simulation_task')
}

export default [
  {
    url: '/dev-api/vue-admin-template/table/list',
    method: 'get',
    response: () => {
      const items = data.items
      return {
        code: 20000,
        data: {
          total: items.length,
          items: items
        }
      }
    }
  },
  {
    url: '/dev-api/vue-admin-template/table_simulation_task/list',
    method: 'get',
    response: () => {
      const items = dataForSimulationTask.items
      return {
        code: 20000,
        data: {
          total: items.length,
          items: items
        }
      }
    }
  }
]
