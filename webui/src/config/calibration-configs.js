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

// calibration-configs.js
export const RABI_CONFIG = {
  title: 'Rabi振荡扫描',
  apiType: 'rabi',
  formFields: {
    // 基础参数配置
    base: [
      { key: 'atom_row', label: '待测原子行号', initialValue: 4 },
      { key: 'atom_col', label: '待测原子列号', initialValue: 4 },
      { key: 'step_num', label: '扫描次数', initialValue: 1 },
      { key: 'shots', label: '扫描采样次数', initialValue: 10 }
    ],
    // 科学计数法参数
    sciParams: [
      { key: 'init_val', label: '扫描起始值', initialCoeff: 12 },
      { key: 'step', label: '扫描步长', initialCoeff: 1 }
    ],
    // 参数映射规则（将表单参数转换为API参数）
    mapping: (params) => ({
      atom_row: params.atom_row,
      atom_col: params.atom_col,
      step_num: params.step_num,
      shots: params.shots,
      init_val: params.init_val.coefficient * 10 ** params.init_val.exponent,
      step: params.step.coefficient * 10 ** params.step.exponent
    })
  }
}

export const RAMAN_CH1_CONFIG = {
  title: '单比特对准阱扫描CH1通道',
  apiType: 'raman_ch1',
  formFields: {
    // 基础参数配置
    base: [
      { key: 'atom_row', label: '待测原子行号', initialValue: 4 },
      { key: 'atom_col', label: '待测原子列号', initialValue: 4 },
      { key: 'step_num', label: '扫描次数', initialValue: 4 },
      { key: 'shots', label: '扫描采样次数', initialValue: 4 }
    ],
    // 科学计数法参数
    sciParams: [
      { key: 'init_val', label: '扫描起始值', initialCoeff: 12 },
      { key: 'step', label: '扫描步长', initialCoeff: 1 }
    ],
    // 参数映射规则（将表单参数转换为API参数）
    mapping: (params) => ({
      atom_row: params.atom_row,
      atom_col: params.atom_col,
      step_num: params.step_num,
      shots: params.shots,
      init_val: params.init_val.coefficient * 10 ** params.init_val.exponent,
      step: params.step.coefficient * 10 ** params.step.exponent
    })
  }
}

export const RAMAN_CH2_CONFIG = {
  title: '单比特对准阱扫描CH2通道',
  apiType: 'raman_ch2',
  formFields: {
    // 基础参数配置
    base: [
      { key: 'atom_row', label: '待测原子行号', initialValue: 4 },
      { key: 'atom_col', label: '待测原子列号', initialValue: 4 },
      { key: 'step_num', label: '扫描次数', initialValue: 4 },
      { key: 'shots', label: '扫描采样次数', initialValue: 4 }
    ],
    // 科学计数法参数
    sciParams: [
      { key: 'init_val', label: '扫描起始值', initialCoeff: 12 },
      { key: 'step', label: '扫描步长', initialCoeff: 1 }
    ],
    // 参数映射规则（将表单参数转换为API参数）
    mapping: (params) => ({
      atom_row: params.atom_row,
      atom_col: params.atom_col,
      step_num: params.step_num,
      shots: params.shots,
      init_val: params.init_val.coefficient * 10 ** params.init_val.exponent,
      step: params.step.coefficient * 10 ** params.step.exponent
    })
  }
}

export const ARRANGE_CH1_CONFIG = {
  title: '重排CH1频率扫描',
  apiType: 'arrange_ch1',
  formFields: {
    base: [
      { key: 'row_up', label: '重排区上沿行号', initialValue: 3 },
      { key: 'row_down', label: '重排区下沿行号', initialValue: 5 },
      { key: 'col_left', label: '重排区左侧列号', initialValue: 3 },
      { key: 'col_right', label: '重排区右侧列号', initialValue: 5 },
      { key: 'step_num', label: '扫描次数', initialValue: 4 },
      { key: 'shots', label: '扫描采样次数', initialValue: 4 }
    ],
    sciParams: [
      { key: 'init_val', label: '扫描起始值', initialCoeff: 12 },
      { key: 'step', label: '扫描步长', initialCoeff: 1 }
    ],
    mapping: (params) => ({
      row_up: params.row_up,
      row_down: params.row_down,
      col_left: params.col_left,
      col_right: params.col_right,
      step_num: params.step_num,
      shots: params.shots,
      init_val: params.init_val.coefficient * 10 ** params.init_val.exponent,
      step: params.step.coefficient * 10 ** params.step.exponent
    })
  }
}

export const ARRANGE_CH2_CONFIG = {
  title: '重排CH2频率扫描',
  apiType: 'arrange_ch2',
  formFields: {
    base: [
      { key: 'row_up', label: '重排区上沿行号', initialValue: 3 },
      { key: 'row_down', label: '重排区下沿行号', initialValue: 5 },
      { key: 'col_left', label: '重排区左侧列号', initialValue: 3 },
      { key: 'col_right', label: '重排区右侧列号', initialValue: 5 },
      { key: 'step_num', label: '扫描次数', initialValue: 4 },
      { key: 'shots', label: '扫描采样次数', initialValue: 4 }
    ],
    sciParams: [
      { key: 'init_val', label: '扫描起始值', initialCoeff: 12 },
      { key: 'step', label: '扫描步长', initialCoeff: 1 }
    ],
    mapping: (params) => ({
      row_up: params.row_up,
      row_down: params.row_down,
      col_left: params.col_left,
      col_right: params.col_right,
      step_num: params.step_num,
      shots: params.shots,
      init_val: params.init_val.coefficient * 10 ** params.init_val.exponent,
      step: params.step.coefficient * 10 ** params.step.exponent
    })
  }
}
