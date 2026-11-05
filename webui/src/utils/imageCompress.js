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

/**
 * Compress an image file to reduce base64 size and token consumption.
 *
 * Targets long edge <= maxEdge (Claude / GPT-4o recommended resolution)
 * and JPEG quality 0.85.
 *
 * @param {File} file - Image file from paste / drop / file input
 * @param {number} [maxEdge=1568] - Max long edge in pixels
 * @param {number} [quality=0.85] - JPEG quality 0-1
 * @returns {Promise<{data: string, media_type: string, size_bytes: number, width: number, height: number}>}
 */
export async function compressImage(file, maxEdge = 1568, quality = 0.85) {
  const img = await createImageBitmap(file)
  const { width, height } = img
  const scale = Math.min(1, maxEdge / Math.max(width, height))
  const w = Math.round(width * scale)
  const h = Math.round(height * scale)

  const canvas = document.createElement('canvas')
  canvas.width = w
  canvas.height = h
  const ctx = canvas.getContext('2d')
  ctx.drawImage(img, 0, 0, w, h)

  const blob = await new Promise((resolve, reject) => {
    canvas.toBlob(
      b => (b ? resolve(b) : reject(new Error('Image compression failed'))),
      'image/jpeg',
      quality
    )
  })

  const buf = await blob.arrayBuffer()
  const bytes = new Uint8Array(buf)
  let binary = ''
  const chunkSize = 8192
  for (let i = 0; i < bytes.length; i += chunkSize) {
    binary += String.fromCharCode(...bytes.subarray(i, i + chunkSize))
  }

  return {
    data: btoa(binary),
    media_type: 'image/jpeg',
    size_bytes: buf.byteLength,
    width: w,
    height: h
  }
}
