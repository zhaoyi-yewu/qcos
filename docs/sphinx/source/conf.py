#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024-2026 China Mobile (SuZhou) Software Technology Co.,Ltd.
#
# qcos is licensed under Mulan PSL v2.
# You can use this software according to the terms and conditions
# of the Mulan PSL v2.
# You may obtain a copy of Mulan PSL v2 at:
#         http://license.coscl.org.cn/MulanPSL2
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS,
#     WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
# ----------------------------------------------------------------------
# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

import os
import shutil
import subprocess
import sys
import types

import pydantic.functional_serializers  # Note: Don't delete this import
from sphinx.errors import ExtensionError
from sphinx.ext import apidoc
from sphinx.ext import imgconverter

current_dir = os.path.split(os.path.realpath(__file__))[0]
top_dir = os.path.abspath(f"{current_dir}/../../..")
src_dir = os.path.abspath(f"{top_dir}/src")
sys.path.insert(0, src_dir)

from wy_qcos.common.constant import Constant
from wy_qcos.common.qcos_version import QcosVersion
on_rtd = os.environ.get("READTHEDOCS") == "True"

project = f"{Constant.PLATFORM_NAME}"
title = f"{Constant.PLATFORM_NAME}文档"
subject = "文档"
description_zh = "QCOS是一款开源的通用量子计算操作系统"
copyright = f"{Constant.COPYRIGHT}"
author = "Zhao Yi"
version = QcosVersion.VERSION
release = QcosVersion.VERSION
file_name = "qcos-full-docs"
sphinx_api_dir = f"{top_dir}/docs/sphinx/source/api"


extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.extlinks",
    "sphinx.ext.graphviz",
    "sphinx.ext.imgconverter",
    "sphinxcontrib.rsvgconverter",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",
    "sphinx_rtd_theme",
    "myst_parser",
    "docxbuilder",
    'sphinxcontrib.autodoc_pydantic',
    "sphinxcontrib.mermaid",
    "sphinxcontrib.plantuml",
]

exclude_patterns = [
    "_build",
    "_template",
]

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

##
# skip module
autodoc_mock_imports = [
    "aiohttp",
    "argparse",
    "cliff",
    "fastapi",
    "fastapi.applications",
    "fastapi_jsonrpc",
    "fastapi_jsonrpc.api",
    "fastapi_jsonrpc.base",
    "fastapi_jsonrpc.core",
    "loguru",
    "mqt",
    # "networkx",  # required for docstring-check.sh / sphinx-build -b html
    # "numpy",  # required for autodoc
    "numexpr",
    "openqasm3",
    "pydantic",
    "pydantic_core",
    "pydantic_settings",
    "pydantic.functional_serializers",
    "ply",
    "prefect",
    "prometheus_client",
    "psutil",
    "quark",
    "pulp",
    "pwdlib",
    "qiskit",
    "qiskit_aer",
    "qutip",
    "redis",
    # "rustworkx",  # required for autodoc
    "setproctitle",
    "stevedore",
    "sympy",
    "uvicorn",
    "yarl",
    "zerorpc",
    "zmp",
    "wy_qcos.api.fastapi_server",
    "wy_qcos.api_server",
    "wy_qcos_client.shell",
    "wy_qcos_client.tests",
    "wy_qcos.driver.casoldatom",
    "wy_qcos.driver.qboson",
    "wy_qcos.driver.qiskit",
    "wy_qcos.driver.qutip",
    "wy_qcos.driver.spinq",
    "wy_qcos.driver.uqc",
    "wy_qcos.server",
    "wy_qcos.tests",
    "wy_qcos.transpiler.cmss.compiler.openqasm3",
    "wy_qcos.transpiler.cmss.circuit.parameter",
    "wy_qcos.transpiler.cmss.circuit.parameterexpression",
    "wy_qcos.transpiler.cmss.circuit.parametervector",
    "wy_qcos.transpiler.cmss.transpiler_cmd_line",
    "wy_qcos.transpiler.cmss.transpiler_cmss",
    "wy_qcos.transpiler.cmss.transpiler_cmss_for_cpp",
    "wy_qcos.transpiler.common.pulse_ir",
    "wy_qcos.transpiler.dummy.transpiler_dummy",
    "wy_qcos.transpiler.high_performance",
]
suppress_warnings = [
    "autodoc",
    "autodoc.import_object",
    "config.misconfig",
    "ref.ref",
    "ref.python",
]


def skip_modules(app, what, name, obj, skip, options):
    # Skip modules
    skip_module_list = []
    if what == "module" and isinstance(obj, types.ModuleType):
        module_name = obj.__name__
        for skip_module in skip_module_list:
            if skip_module in module_name:
                return True
    return skip


def run_apidoc():
    """Run apidoc."""
    apidoc.main(["-H", "QCOS API文档", "-f", "-o", sphinx_api_dir, f"{src_dir}"])


def _patch_imgconverter():
    """Patch imgconverter to handle multi-page SVG files."""
    _original_convert = imgconverter.ImagemagickConverter.convert

    def _custom_convert(self, src, dst):
        if self.app.builder.config.image_converter == 'rsvg-convert':
            if not self.available:
                return False
            # Handle multi-page SVG (e.g., file.svg[0])
            page = None
            src_clean = src
            if '[' in src and src.endswith(']'):
                idx = src.rfind('[')
                page = src[idx + 1:-1]
                src_clean = src[:idx]
            args = ['rsvg-convert', '-f', 'png', '-o', dst]
            if page is not None:
                args.extend(['--page', page])
            args.append(src_clean)
            try:
                subprocess.run(args, capture_output=True, check=True)
                return True
            except subprocess.CalledProcessError as exc:
                raise ExtensionError(
                    'rsvg-convert exited with error:\n[stderr]\n%r\n'
                    '[stdout]\n%r' % (exc.stderr, exc.stdout)
                ) from exc
            except OSError as exc:
                raise ExtensionError(
                    'rsvg-convert command cannot be run: %s' % exc
                ) from exc
        else:
            return _original_convert(self, src, dst)

    imgconverter.ImagemagickConverter.convert = _custom_convert


def setup(app):
    """Setup app."""

    def check_builder(app):
        builder_name = app.builder.name
        print(f"[Builder name: {builder_name}]")
        shutil.rmtree(
            f"{top_dir}/docs/sphinx/source/api/",
            ignore_errors=True,
            onerror=None
        )
        extensions.append("sphinxcontrib.jquery")
        run_apidoc()
        # Patch imgconverter after all extensions are loaded
        _patch_imgconverter()

    app.connect("autodoc-skip-member", skip_modules)
    app.connect("builder-inited", check_builder)


source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

myst_enable_extensions = [
    "colon_fence",
    "linkify",
    "substitution",
]

nitpicky = False
nitpick_ignore = [
    ("py:class", "GenericException"),
]

autodoc_inherit_docstrings = False
autodoc_member_order = "bysource"
autodoc_typehints = "description"
autodoc_preserve_defaults = True
autodoc_pydantic_field_list_validators = True
autodoc_pydantic_model_member_order = 'bysource'
autodoc_pydantic_model_show_json = True
autodoc_pydantic_model_undoc_members = False

numfig = False
html_secnumber_depth = 0
toc_object_entries = False
html_use_smartypants = False
html_permalinks = False
html_permalinks_icon = ""

# mermaid configs
mermaid_cmd = "mmdc"
mermaid_output_format = "png"
mermaid_params = [
    "--puppeteerConfigFile", f"{current_dir}/puppeteer-config.json",
]
os.environ["PUPPETEER_PRODUCT"] = "firefox"
os.environ["PUPPETEER_EXECUTABLE_PATH"] = "/usr/bin/firefox"

# plantuml configs
if on_rtd:
    # Use system plantuml command installed via apt_packages
    plantuml = "plantuml"
else:
    plantuml_jar_path = "/usr/local/lib/node_modules/plantuml/vendor/plantuml.jar"
    plantuml = f"java -Dfile.encoding=UTF-8 -Djava.awt.headless=true -jar {plantuml_jar_path} -charset UTF-8"

plantuml_output_format = "svg"  # default: png
plantuml_latex_output_format = "pdf"

# image converter configs
image_converter = "rsvg-convert"

# latex config
language = "zh_CN"
latex_engine = "xelatex"
latex_use_xindy = False
latex_domain_indices = False
latex_use_modindex = False
latex_documents = [
    ("index", "qcos-full-docs.tex", f"{project}\\\\全量文档", f"{author}", "manual"),
]
if not on_rtd:
    latex_documents += [
    ("user-guide/index", "qcos-chapter1-user-guide.tex", f"{project}\\\\用户指南", f"{author}", "manual"),
    ("design/index", "qcos-chapter2-design-guide.tex", f"{project}\\\\设计文档", f"{author}", "manual"),
    ("developer-guide/index", "qcos-chapter3-developer-guide.tex", f"{project}\\\\开发指南", f"{author}", "manual"),
    ("other-docs/index", "qcos-chapter4-other-docs.tex", f"{project}\\\\其他文档", f"{author}", "manual"),
]
latex_elements = {
    "papersize": "a4paper",
    "pointsize": "10pt",
    "figure_align": "H",
    "fncychap": "",
    "fontpkg": """
        \\setmainfont{FreeSerif}[
        UprightFont    = *,
        ItalicFont     = *Italic,
        BoldFont       = *Bold,
        BoldItalicFont = *BoldItalic
        ]
        \\setsansfont{FreeSans}[
        UprightFont    = *,
        ItalicFont     = *Oblique,
        BoldFont       = *Bold,
        BoldItalicFont = *BoldOblique,
        ]
        \\setmonofont{FreeMono}[
        UprightFont    = *,
        ItalicFont     = *Oblique,
        BoldFont       = *Bold,
        BoldItalicFont = *BoldOblique,
        ]
    """,
    "preamble": r"""
        % ========== Import header & footer dependency packages ==========
        \usepackage{fancyhdr}  % Core package: Customize header and footer
        \usepackage{fancyvrb}  % Load: fancyvrb
        \usepackage{lastpage}  % Optional: Display total pages (e.g., 1/5)
        \usepackage{color}     % Optional: Set color for header and footer
        \usepackage{longtable,array,listings}
        \usepackage{tocloft}
        \usepackage{eso-pic}

       % ========== Set TOC ==========
        \setcounter{tocdepth}{3}
        \setcounter{secnumdepth}{3}

        % ========== Convert contensname/indexname/listfigurename/listtablename to Chinese ==========
        % === 关键修改：在文档开始时重定义 ===
        % 使用 \AtBeginDocument 确保命令在所有宏包加载完毕后执行
        \AtBeginDocument{\renewcommand{\contentsname}{目录}}

        % 如果文档同时包含索引（Index），也可以一起修改
        \AtBeginDocument{\renewcommand{\indexname}{索引}}

        % 如果文档同时包含图表清单（List of Figures/Tables），也可以一起修改
        \AtBeginDocument{\renewcommand{\listfigurename}{图目录}}
        \AtBeginDocument{\renewcommand{\listtablename}{表目录}}

        % ========== Keep your previous Chinese font configuration ==========
        \let\oldusepackage\usepackage
        \renewcommand{\usepackage}[2][]{%
            \ifx#2cmap\else
                \oldusepackage[#1]{#2}
            \fi
        }

        % ========== paragraph indent ==========
        % \setlength{\parindent}{2em}：设置段落缩进的长度。
        %   - 1em ≈ 当前字体的一个中文字符宽度。
        %   - 2em ≈ 两个中文字符的宽度（即您需要的 2 字符缩进）。
        \AtBeginDocument{
            \setlength{\parindent}{2em}
            % \parskip：设置段落之间的垂直距离。
            % 默认的 LaTeX 排版（英式）是：段落之间有距离，但没有首行缩进。
            % 中文排版通常是：有首行缩进，但段落之间无额外距离。
            \setlength{\parskip}{0pt}
        }

        % ========== set small fontsize of code-block in table ==========
        \makeatletter
        
        % === 定义名为 'smallcode' 的容器环境 ===
        % 当你在 reST 中使用 .. container:: smallcode 时，Sphinx 会调用这个环境
        \newenvironment{sphinxclasstable-code-small-font}{
            \begingroup % 开始一个组，限制样式的作用范围
            % 关键：使用 \fvset 设置 fancyvrb 的字体大小
            % 您可以使用 \footnotesize, \scriptsize, \tiny 或者 \fontsize{8pt}{10pt}\selectfont
            \fvset{fontsize=\tiny} 
        }{
            \endgroup % 结束组，恢复原来的字体大小
        }
        \makeatother

        % ========== Customize header & footer styles ==========
        \pagestyle{fancy}  % Enable fancy page style (replace default plain style)

        % Clear default header and footer (avoid conflicts)
        \fancyhf{}

        % ========== Header Configuration ========== 
        \fancyhead[L]{\textbf{量子计算操作系统(QCOS)文档}}  % Left header: Document name (bold)
        \fancyhead[C]{\textit{\thesection\ 节标题}}       % Center header: Current section (italic)

        % ========== Footer Configuration ========== 
        \fancyfoot[L]{\textcolor{gray}{文档生成时间：\today}} % Left footer: Generation date (gray)
        \fancyfoot[C]{\textbf{第 \thepage 页 / 共 \pageref{LastPage} 页}}  % Center footer: Page number + total pages
        \fancyfoot[R]{\textit{内部文档}}                                   % Right footer: Document type (italic)
        \renewcommand{\chaptermark}[1]{\markboth{第\ \thechapter\ 章\ #1}{}}

        % ========== Adjust margins (avoid overlap with content) ==========
        \setlength{\headheight}{15pt}  % Header height (adapted for Chinese characters)
        \setlength{\topmargin}{-0.5cm} % Top margin
        \setlength{\textheight}{22cm}  % Main content height
        \setlength{\footskip}{15pt}    % Footer margin

        % ========== Apply header & footer to section pages (e.g., cover, TOC) ==========
        \fancypagestyle{plain}{
            \fancyhf{}  % Clear default style for section pages
            \fancyfoot[C]{\textbf{第 \thepage 页 / 共 \pageref{LastPage} 页}}  % Only keep page number on section pages
            \renewcommand{\headrulewidth}{0pt}  % Hide header rule on section pages
        }

        % ========== Add horizontal line below header (optional) ==========
        \renewcommand{\headrulewidth}{0.5pt}  % Header rule width (0pt to hide)
        \renewcommand{\footrulewidth}{0.3pt}  % Footer rule width (optional)

        % ========== Replace Chinese chapter head ==========
        \renewcommand{\contentsname}{目录}
        % % 2. 终极方案：强制重定义目录生成逻辑（完全绕过所有默认配置）
        \makeatletter
        \renewcommand{\tableofcontents}{
            % 第一步：生成“目录”标题（无编号，字体/间距与原Contents一致）
            \chapter*{\Huge\bfseries 目录}
            % 第二步：生成目录内容（保留原有章节/页码结构）
            \@starttoc{toc}
            % 第三步：添加目录页码（可选，与原样式一致）
            \addcontentsline{toc}{chapter}{目录}
        }
        \makeatother

        % 3. 章节标题配置（保留你的核心需求）
        \makeatletter
        \renewcommand{\@makechapterhead}[1]{
            \vspace*{50\p@}%
            {\parindent \z@ \raggedright \normalfont
                \Huge\bfseries 
                第\arabic{chapter}章\ #1\par\nobreak
                \vskip 40\p@
            }
        }
        \makeatother
        \renewcommand{\chaptername}{}

        % 4. 索引清理（仅保留必要的tocloft配置，删除目录相关）
        \renewcommand{\printindex}{}
        \cftpagenumbersoff{section}

        % ========== Apply watermark ==========
        % 定义水印内容
        \newcommand{\watermarktext}{
            \put(0,0){
                \parbox{\linewidth}{
                    \centering
                    \textbf{\fontsize{50}{50}\selectfont\color[gray]{0.9}\rotatebox{60}{量子计算操作系统（QCOS）}}
                }
            }
        }
        
        % 调用水印命令，应用到每一页背景
        % \AddToShipoutPicture*{\watermarktext}  % 是否打开水印
    """,
}

docx_documents = [
    ("index", f"{file_name}.docx", {
        "title": project,
        "creator": author,
        "subject": subject,
    }, True),
]
docx_style = "_template/docx/docxbuilder-style.docx"
docx_coverpage = True
docx_pagebreak_before_section = 1


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_rtd_theme"  # alternative: "alabaster"
html_sidebars = {
    "**": [
        "about.html",
        "searchfield.html",
        "navigation.html",
        "relations.html",
        # "donate.html",
    ]
}
html_theme_options_rtd = {
    "navigation_depth": 4,
    "collapse_navigation": True,
    "sticky_navigation": True,
    "titles_only": False,
}
html_theme_options_alabaster = {
    "description": description_zh,
    "fixed_sidebar": True,
    "show_related": False,
    "show_relbars": True,
}
html_theme_options = html_theme_options_rtd
html_static_path = ["_static"]
# TODO (zhaoyi): to be replaced
# html_favicon = "_static/qcos-icon.svg"
# html_logo = "_static/qcos-logo.png"
html_css_files = [
    "custom.css",
]
html_title = title
html_show_sourcelink = False
gettext_uuid = True
gettext_compact = False
