# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

import os
import sys

from pallets_sphinx_themes import ProjectLink

top_dir = os.path.abspath(
    os.path.split(os.path.realpath(__file__))[0] + "/../..")
sys.path.insert(0, top_dir)
from qcos.api.fastapi_server import app

project = 'QCOS'
copyright = '2024-2025 China Mobile (SuZhou) Software Technology Co.,Ltd.'
author = 'Zhao Yi'
release = '1.0.0'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.extlinks",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",
    "sphinx.ext.intersphinx"
]
autodoc_member_order = "bysource"
autodoc_typehints = "description"
autodoc_preserve_defaults = True

templates_path = ['_templates']
exclude_patterns = []

language = 'zh_CN'

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'alabaster'
html_theme_options = {"index_sidebar_logo": False}
html_context = {
    "project_links": [
        # TODO (zhaoyi): to be replaced https://pypi.org/project/wy_qcos/
        ProjectLink("PyPI Releases", ""),
        ProjectLink("Source Code", "https://gitee.com/OpenWuYue/qcos")
    ]
}
html_sidebars = {
    "index": ["project.html"],
    "**": ["localtoc.html"]
}
singlehtml_sidebars = {"index": ["project.html"]}
html_static_path = ['_static']
# TODO (zhaoyi): to be replaced
# html_favicon = "_static/qcos-icon.svg"
# html_logo = "_static/qcos-logo.png"
html_title = "QCOS Documentation"
html_show_sourcelink = False
gettext_uuid = True
gettext_compact = False
