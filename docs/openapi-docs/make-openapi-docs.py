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

# Script to export the ReDoc documentation page into a standalone HTML file.
# Created by https://github.com/pawamoy on https://github.com/Redocly/redoc/issues/726#issuecomment-645414239

import json
import os
import sys

current_dir = os.path.split(os.path.realpath(__file__))[0]
top_dir = os.path.abspath(f"{current_dir}/../../src")
sys.path.insert(0, top_dir)
from wy_qcos.api.fastapi_server import app
from wy_qcos.common.constant import Constant
from wy_qcos.common.qcos_version import QcosVersion

HTML_TEMPLATE = f"""<!DOCTYPE html>
<html>
<head>
    <meta http-equiv="content-type" content="text/html; charset=UTF-8">
    <title>QCOS API Doc - v{QcosVersion.VERSION}</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {{
            margin: 0;
            padding: 0;
        }}
    </style>
    <style data-styled="" data-styled-version="4.4.1"></style>
</head>
<body>
    <div id="redoc-container"></div>
    <script src="js/redoc.standalone.js"> </script>
    <script>
        var spec = %s;
        Redoc.init(spec, {{}}, document.getElementById("redoc-container"));
    </script>
</body>
</html>
"""

if __name__ == "__main__":
    output_dir = f"{current_dir}/dist"
    os.makedirs(output_dir, mode=0o755, exist_ok=True)
    file_path = f"{output_dir}/qcos-api-docs.html"
    with open(file_path, "w") as fd:
        openapi_dict = app.openapi()
        openapi_dict["info"]["title"] = f"{Constant.PLATFORM_NAME} API文档"
        openapi_dict["info"]["version"] = f"v{QcosVersion.VERSION}"
        openapi_str = json.dumps(openapi_dict)
        print(HTML_TEMPLATE % openapi_str, file=fd)
    print(f"Successfully created qcos api docs: {file_path}")
