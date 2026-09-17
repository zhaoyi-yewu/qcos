const Mock = require('mockjs')

//表格中的数据是data，是mock出来的，所以一旦重启vue项目，这个data的值就会变
//items|30中的这个30，是mock出30行数据的意思
//http://localhost:9528/#/example_k8s_cluster_path/table_k8s_cluster这个链接中的表格中的数据，
//是请求的http://localhost:9528/dev-api/vue-admin-template/table/list 这个接口，接口返回的数据就是下面mock出来的data
const data = Mock.mock({
  'items|2': [{
    id: '@id',
    title: 'table_k8s_cluster_@sentence(10, 20)',
    'status|1': ['published', 'draft', 'deleted'],
    author: 'name',
    display_time: '@datetime',
    pageviews: '@integer(300, 5000)'
  }]
})

//新接口所需的数据
const dataForSimulationTask = Mock.mock({
  'items|30': [{
    id: '@id',
    title: 'table_k8s_simulation_task_@sentence(10, 20)',
    'status|1': ['published', 'draft', 'deleted'],
    author: 'name',
    display_time: '@datetime',
    pageviews: '@integer(300, 5000)'
  }]
})

module.exports = [
  {
    url: '/vue-admin-template/table/list',
    type: 'get',
    response: config => {
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
    url: '/vue-admin-template/table_simulation_task/list',
    type: 'get',
    response: config => {
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


// module.exports只能赋值一次，赋值多次，则只有最后一次赋值会覆盖前面多次的赋值
// module.exports = [
//   {
//     url: '/vue-admin-template/table_simulation_task/list',
//     type: 'get',
//     response: config => {
//       const items = dataForSimulationTask.items
//       return {
//         code: 20000,
//         data: {
//           total: items.length,
//           items: items
//         }
//       }
//     }
//   }
// ]
