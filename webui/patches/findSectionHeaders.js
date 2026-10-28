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

// Patched: removed RegExp 'd' (hasIndices) flag for older MS Edge compatibility.
// The capture-group start/end columns are computed via String.prototype.indexOf,
// which yields exactly the same values as match.indices[1][0] / match.indices[1][1]
// for the '\\bMARK:\\s*(.*)$' pattern (single capturing group, no nested groups).
const markRegex = new RegExp('\\bMARK:\\s*(.*)$');
const trimDashesRegex = /^-+|-+$/g;
/**
 * Find section headers in the model.
 *
 * @param model the text model to search in
 * @param options options to search with
 * @returns an array of section headers
 */
export function findSectionHeaders(model, options) {
    let headers = [];
    if (options.findRegionSectionHeaders && options.foldingRules?.markers) {
        const regionHeaders = collectRegionHeaders(model, options);
        headers = headers.concat(regionHeaders);
    }
    if (options.findMarkSectionHeaders) {
        const markHeaders = collectMarkHeaders(model);
        headers = headers.concat(markHeaders);
    }
    return headers;
}
function collectRegionHeaders(model, options) {
    const regionHeaders = [];
    const endLineNumber = model.getLineCount();
    for (let lineNumber = 1; lineNumber <= endLineNumber; lineNumber++) {
        const lineContent = model.getLineContent(lineNumber);
        const match = lineContent.match(options.foldingRules.markers.start);
        if (match) {
            const range = { startLineNumber: lineNumber, startColumn: match[0].length + 1, endLineNumber: lineNumber, endColumn: lineContent.length + 1 };
            if (range.endColumn > range.startColumn) {
                const sectionHeader = {
                    range,
                    ...getHeaderText(lineContent.substring(match[0].length)),
                    shouldBeInComments: false
                };
                if (sectionHeader.text || sectionHeader.hasSeparatorLine) {
                    regionHeaders.push(sectionHeader);
                }
            }
        }
    }
    return regionHeaders;
}
function collectMarkHeaders(model) {
    const markHeaders = [];
    const endLineNumber = model.getLineCount();
    for (let lineNumber = 1; lineNumber <= endLineNumber; lineNumber++) {
        const lineContent = model.getLineContent(lineNumber);
        addMarkHeaderIfFound(lineContent, lineNumber, markHeaders);
    }
    return markHeaders;
}
function addMarkHeaderIfFound(lineContent, lineNumber, sectionHeaders) {
    markRegex.lastIndex = 0;
    const match = markRegex.exec(lineContent);
    if (match) {
        // Equivalent of match.indices[1][0] / match.indices[1][1] without 'd' flag.
        // match[1] is the captured text after 'MARK:' and optional whitespace.
        // Its position in lineContent is match.index + offset of match[1] inside match[0].
        const groupOffsetInMatch = match[0].indexOf(match[1]);
        const groupStartInLine = match.index + (groupOffsetInMatch === -1 ? match[0].length - match[1].length : groupOffsetInMatch);
        const column = groupStartInLine + 1;
        const endColumn = groupStartInLine + match[1].length + 1;
        const range = { startLineNumber: lineNumber, startColumn: column, endLineNumber: lineNumber, endColumn: endColumn };
        if (range.endColumn > range.startColumn) {
            const sectionHeader = {
                range,
                ...getHeaderText(match[1]),
                shouldBeInComments: true
            };
            if (sectionHeader.text || sectionHeader.hasSeparatorLine) {
                sectionHeaders.push(sectionHeader);
            }
        }
    }
}
function getHeaderText(text) {
    text = text.trim();
    const hasSeparatorLine = text.startsWith('-');
    text = text.replace(trimDashesRegex, '');
    return { text, hasSeparatorLine };
}
