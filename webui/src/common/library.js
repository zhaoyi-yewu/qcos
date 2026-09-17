/**
 * Copyright© 2024-2026 China Mobile (SuZhou) Software Technology Co.,Ltd.
 *
 * qcos is licensed under Mulan PSL v2.
 * You can use this software according to the terms and conditions
 * of the Mulan PSL v2.
 * You may obtain a copy of Mulan PSL v2 at:
 *         http://license.coscl.org.cn/MulanPSL2
 * THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS,
 *     WITHOUT WARRANTIES OF ANY KIND,
 * EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
 * MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
 * See the Mulan PSL v2 for more details.
 */

export function getJobStatus(job_status) {
  const jobMap = {
    'UNKNOWN': '未知',
    'QUEUED': '排队中',
    'RUNNING': '运行中',
    'FAILED': '失败',
    'COMPLETED': '已完成',
    'CANCELLING': '取消中',
    'CANCELLED': '已取消',
    'DELETED': '已删除'
  }
  return jobMap[job_status] || ''
}

export function getJobStatusTag(jobStatus) {
  const statusMap = {
    'UNKNOWN': 'grey',
    'QUEUED': 'orange',
    'RUNNING': 'green',
    'FAILED': 'red',
    'COMPLETED': 'blue',
    'CANCELLING': 'grey',
    'CANCELLED': 'grey',
    'DELETED': 'grey'
  }
  return statusMap[jobStatus] || ''
}

export function getStatus(deviceStatus) {
  const statusMap = {
    'online': '在线',
    'offline': '离线',
    'busy': '忙碌',
    'unknown': '未知'
  }
  return statusMap[deviceStatus] || ''
}

export function getEnable(enable) {
  return enable ? '开启' : '关闭'
}

export function getCircuitAggregation(circuitAggregation) {
  if (circuitAggregation === 'internal') {
    return '作业内并行'
  } else if (circuitAggregation === 'external') {
    return '多作业并行'
  }
  return '无(串行)'
}

export function getResultsFetchMode(resultsFetchMode) {
  const resultsFetchModeMap = {
    'sync': '同步',
    'async': '异步'
  }
  return resultsFetchModeMap[resultsFetchMode] || '-'
}

export function convertDate(dateStr) {
  if (!dateStr) {
    return dateStr
  }
  const date = new Date(dateStr)
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  }).format(date)
}

export function customColorMethod(percentage) {
  if (percentage < 30) {
    return '#909399'
  }
  if (percentage < 70) {
    return '#e6a23c'
  }
  return '#67c23a'
}

export function isEmptyStr(value) {
  if (value === null) {
    return true
  }
  if (typeof value === 'string') {
    if (value.trim() === '') {
      return true
    }
  }
  return false
}

export function isEmptyObj(value) {
  return Object.prototype.toString.call(value) === '[object Object]' &&
    Object.keys(value).length === 0
}

export function readMultiFiles(fileList) {
  const fileContents = []
  fileList.forEach(fileObj => {
    const promise = new Promise((resolve, reject) => {
      const reader = new FileReader()
      reader.onload = (e) => {
        resolve(
          {
            'fileName': fileObj.name,
            'content': e.target.result
          }
        )
      }
      reader.onerror = () => {
        reject(new Error(`读取文件: ${fileObj.name} 失败: ${reader.error.message}`))
      }
      reader.readAsText(fileObj.raw)
    })
    fileContents.push(promise)
  })
  return Promise.all(fileContents)
}

export function log(item) {
  console.log(item)
}

export function getFileExtension(fileName) {
  if (!fileName) return null
  const lastDotIndex = fileName.lastIndexOf('.')
  if (lastDotIndex <= 0) return null
  return fileName.slice(lastDotIndex + 1).toLowerCase()
}

export function readCsv(fileContent) {
  const lineList = []
  const lines = fileContent.split(/\r\n|\n/).filter(line => line.trim() !== '')
  for (let i = 0; i < lines.length; i++) {
    lineList.push(lines[i].split(/,/).map(item => {
      const trimmed = item.trim()
      return trimmed ? parseInt(trimmed, 10) : null
    }).filter(item => item !== null))
  }
  return JSON.stringify(lineList)
}

export function qasmParser(fileName, fileContent) {
  // 无需转换格式
  return fileContent
}

export function quboParser(fileName, fileContent) {
  const extName = getFileExtension(fileName)
  if (extName === 'csv') {
    fileContent = readCsv(fileContent)
  }
  return JSON.parse(fileContent)
}

export function filterDevices(versionData, devicesDetails, filter) {
  const devices = {}
  const transpilers = versionData.capabilities['transpilers']
  const drivers = versionData.capabilities['drivers']
  const driverTranspilerMappings = versionData.capabilities['driver_transpiler_mappings']
  for (const deviceName in devicesDetails) {
    let addDevice = false
    const device = devicesDetails[deviceName]
    const aliasName = device['alias_name']
    const driverName = device['driver_name']
    const status = device['status']
    const enable = device['enable']
    if (filter && filter['enable'] && !enable) {
      continue
    }
    const driver = drivers[driverName]
    const enableTranspiler = driver['enable_transpiler']
    let filteredTranspilerNames = null
    if (enableTranspiler) {
      const transpilerNames = driverTranspilerMappings[driverName]
      filteredTranspilerNames = []
      for (let i = 0; i < transpilerNames.length; i++) {
        const transpilerName = transpilerNames[i]
        const transpiler = transpilers[transpilerName]
        const supportedCodeTypes = transpiler['supported_code_types']
        let found = true
        if (filter && filter['code_types']) {
          found = filter['code_types'].some(r => supportedCodeTypes.includes(r))
        }
        if (found) {
          const transpilerAliasName = transpiler['alias_name']
          filteredTranspilerNames.push({
            'name': transpilerName,
            'alias_name': transpilerAliasName
          })
          addDevice = true
        }
      }
    } else {
      let found = true
      if (filter && filter['code_types']) {
        const supportedCodeTypes = driver['supported_code_types']
        found = filter['code_types'].some(r => supportedCodeTypes.includes(r))
      }
      if (found) {
        addDevice = true
      }
    }
    if (addDevice) {
      devices[deviceName] = {
        'alias_name': aliasName,
        'status': status,
        'enable': enable,
        'transpilers': filteredTranspilerNames
      }
    }
  }
  return devices
}

export function getTaskCompletedTimeDisplay(job_status, end_date) {
  switch (job_status) {
    case 'FAILED':
      return '-'
    case 'CANCELLED':
      return '-'
    case 'COMPLETED':
      return convertDate(end_date)
    default:
      return '任务计算未完成，暂无数据'
  }
}

export function getResultsPrettyPrint(result, codeType) {
  const displayResults = {}
  if (codeType === 'qubo') {
    displayResults['result'] = getQuboResultsPrettyPrint(result['results'])
  } else {
    displayResults['result'] = JSON.stringify(result['results'], null, 2)
  }
  displayResults['num_qubits'] = result['num_qubits']
  if (result['profiling'] && !isEmptyObj(result['profiling'])) {
    displayResults['profiling'] = JSON.stringify(result['profiling'], null, 2)
  } else {
    displayResults['profiling'] = '未打开'
  }
  if ('error' in result) {
    displayResults['error'] = result['error']
  }
  return displayResults
}

export function getQuboPrettyPrint(code) {
  let displayCodes = []
  for (let i = 0; i < code.length; i++) {
    displayCodes.push(JSON.stringify(code[i]))
  }
  displayCodes = JSON.stringify(displayCodes, null, 2)
  displayCodes = displayCodes.replace(/"/g, '')
  return displayCodes
}

export function getQuboResultsPrettyPrint(result) {
  let displayCodes = []
  if (!result) {
    return displayCodes
  }
  for (let i = 0; i < result.length; i++) {
    const _result = result[i]
    const newResult = {}
    for (const key in _result) {
      const value = _result[key]
      if (key === 'solutionVector') {
        newResult[key] = JSON.stringify(value)
      } else {
        newResult[key] = value
      }
    }
    displayCodes.push(newResult)
  }
  displayCodes = JSON.stringify(displayCodes, null, 2)
  displayCodes = displayCodes.replace(/"\[/g, '[')
  displayCodes = displayCodes.replace(/\]"/g, ']')
  return displayCodes
}

export function getTaskSourceContent(sourceCode, codeType) {
  const codeList = []
  for (let i = 0; i < sourceCode.length; i++) {
    codeList.push(`<b>代码[${i}]:</b>`)
    codeList.push('<div class="scrollable-content"><pre>')
    if (codeType === 'qubo') {
      codeList.push(getQuboPrettyPrint(sourceCode[i]))
    } else {
      codeList.push(sourceCode[i])
    }
    codeList.push('</pre></div>')
  }
  return codeList.join('\n')
}

export function getTaskResultsContent(results, codeType) {
  const resultsList = []
  if (results == null) {
    return resultsList
  }
  for (let i = 0; i < results.length; i++) {
    resultsList.push(getResultsPrettyPrint(results[i], codeType))
  }
  return resultsList
}
