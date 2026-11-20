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

/*
 * Diagram rendering bootstrap for the AI agent chat.
 *
 * This module MUST be imported before `@tdesign-vue-next/chat` in
 * main.js. The chat markdown renderer
 * (@tdesign/web-components-chat/.../markdown-content.js) checks
 * `window.mermaid` at module-evaluation time and only then registers
 * its mermaid code-block plugin on CherryStream. Assigning
 * window.mermaid as a top-level statement of main.js would run AFTER
 * all imported modules have been evaluated, which is why the mermaid
 * plugin previously never activated. Importing this module first
 * guarantees the global exists before the chat bundle is evaluated.
 */

import mermaid from 'mermaid'

// Mermaid: picked up by the chat markdown renderer (see above), which
// then renders ```mermaid fenced blocks as SVG diagrams.
window.mermaid = mermaid
mermaid.initialize({
  startOnLoad: false,
  theme: 'default',
  // Conservative security level: chat content is model-generated,
  // so we keep htmlLabels off to avoid arbitrary HTML injection.
  securityLevel: 'strict'
})
