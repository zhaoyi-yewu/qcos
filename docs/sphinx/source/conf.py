# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

import os
import sys

from pallets_sphinx_themes import ProjectLink


project = '五岳量子计算操作系统(QCOS)文档'
copyright = '2024-2025 中移（苏州）软件技术有限公司'
author = 'Zhao Yi'
release = '1.0.0'

exclude_patterns = ['_build']

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.extlinks",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",
    "myst_parser",
]

source_suffix = {
    '.rst': 'restructuredtext',
    '.md': 'markdown',
}

myst_enable_extensions = [
    "colon_fence",
    "linkify",
    "substitution",
]

autodoc_member_order = "bysource"
autodoc_typehints = "description"
autodoc_preserve_defaults = True

numfig = False
html_secnumber_depth = 0
toc_object_entries = False
html_use_smartypants = False
html_permalinks = False  # 禁用锚点编号
html_permalinks_icon = ""

language = 'zh_CN'

# latex config
latex_engine = "xelatex"
latex_use_xindy = False 
latex_domain_indices = False
latex_use_modindex = False
latex_elements = {
    'papersize': 'a4paper',
    'pointsize': '10pt',
    'fncychap': '',
    'fontpkg': '''
        \setmainfont{FreeSerif}[
        UprightFont    = *,
        ItalicFont     = *Italic,
        BoldFont       = *Bold,
        BoldItalicFont = *BoldItalic
        ]
        \setsansfont{FreeSans}[
        UprightFont    = *,
        ItalicFont     = *Oblique,
        BoldFont       = *Bold,
        BoldItalicFont = *BoldOblique,
        ]
        \setmonofont{FreeMono}[
        UprightFont    = *,
        ItalicFont     = *Oblique,
        BoldFont       = *Bold,
        BoldItalicFont = *BoldOblique,
        ]
    ''',
    'preamble': r'''
        % ========== Import header & footer dependency packages ==========
        \usepackage{fancyhdr}  % Core package: Customize header and footer
        \usepackage{fancyvrb}  % Load: fancyvrb
        \usepackage{lastpage}  % Optional: Display total pages (e.g., 1/5)
        \usepackage{color}     % Optional: Set color for header and footer
        \usepackage{longtable,array,listings}
        \usepackage{xeCJK}
        \usepackage[UTF8]{ctex}
        \usepackage{ctex}
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
        \fancyhead[R]{\textcolor{blue}{QCOS v1.0.0}}     % Right header: Version number (blue)

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
    ''',
 }

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'alabaster'
html_sidebars = {
    "**": [
        "about.html",
        "searchfield.html",
        "navigation.html",
        "relations.html",
        # "donate.html",
    ]
}
html_theme_options = {
    "description": "QCOS是一款开源的通用量子计算操作系统",
    "fixed_sidebar": True,
    'show_related': False,
    'show_relbars': True,
    # "github_user": "",
    # "github_repo": "",
    # "github_banner": True,
}
html_static_path = ['_static']
# TODO (zhaoyi): to be replaced
# html_favicon = "_static/qcos-icon.svg"
# html_logo = "_static/qcos-logo.png"
html_css_files = [
    'custom.css',
]
html_title = "QCOS Documentation"
html_show_sourcelink = False
gettext_uuid = True
gettext_compact = False
