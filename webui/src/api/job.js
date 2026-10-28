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

import { jsonrpcRequest, httpRequest } from '@/api/jsonrpc'

export function queryVersion() {
  return jsonrpcRequest('/version', 'version', { 'details': true })
}

// --- Job operations ---

export function queryJobs(query = null) {
  return jsonrpcRequest('/v1/job', 'get_jobs', {}, query)
}

export function queryJobDetails(jobId) {
  return jsonrpcRequest(
    '/v1/job/get_job_results', 'get_job_results',
    { job_id: jobId }
  )
}

export function submitJob(reqData) {
  // backend submit_job is a fastapi-jsonrpc method on the /v1/job
  // entrypoint: send the JSON-RPC envelope with the job body in
  // params.body instead of a raw HTTP POST
  return jsonrpcRequest('/v1/job/submit_job', 'submit_job', reqData)
}

export function postSubmitSequence(reqData) {
  return httpRequest('/qc/v1/gui_task/sequence', 'post', reqData)
}

export function cancelTask(jobIds = null) {
  return jsonrpcRequest(
    '/v1/job/cancel_jobs', 'cancel_jobs',
    { job_ids: jobIds }
  )
}

export function deleteTask(jobIds = null) {
  return jsonrpcRequest(
    '/v1/job/delete_jobs', 'delete_jobs',
    { job_ids: jobIds }
  )
}

/**
 * Update a QUEUED job's mutable attributes.
 *
 * Only jobs in QUEUED state can be updated; the backend will return
 * an error otherwise. Each field is optional - pass only the fields
 * to be changed.
 *
 * @param {object} data - update payload
 * @param {string} data.job_id - job uuid (required)
 * @param {string} [data.job_name] - new job name
 * @param {string} [data.description] - new job description
 * @param {number} [data.job_priority] - new priority, integer 1-10
 *   (1 = highest, 10 = lowest, default = 5)
 * @returns {Promise} JSON-RPC response
 */
export function updateJob(data) {
  return jsonrpcRequest('/v1/job', 'update_job', data)
}

// --- Calibration operations ---

export function postCalibration(reqData) {
  return httpRequest('/qc/v1/auto_calibration', 'post', reqData)
}

export function getCalibration(calibType) {
  return httpRequest(
    `/qc/v1/auto_calibration?type=${encodeURIComponent(calibType)}`,
    'get'
  )
}

export function stopCalibration() {
  return httpRequest('/qc/v1/auto_calibration/abort', 'post')
}

export function submitCalibrationVal(reqData) {
  return httpRequest(
    '/qc/v1/auto_calibration/submit', 'post', reqData
  )
}

export function getCalibrationVal(calibType) {
  return httpRequest(
    `/qc/v1/auto_calibration/current_value?type=${encodeURIComponent(calibType)}`,
    'get'
  )
}

export function getEnvironmentInfo(type) {
  return httpRequest(
    `/qc/v1/environment_info?type=${encodeURIComponent(type)}`,
    'get'
  )
}
