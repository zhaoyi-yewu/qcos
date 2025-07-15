#!/bin/python3
"""
Script to export the ReDoc documentation page into a standalone HTML file.
Created by https://github.com/pawamoy on https://github.com/Redocly/redoc/issues/726#issuecomment-645414239
"""

import json
import os
import sys

top_path = os.path.abspath(
    os.path.split(os.path.realpath(__file__))[0] + "/..")
sys.path.insert(0, top_path)
from qcos.api.fastapi_server import app

HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
    <meta http-equiv="content-type" content="text/html; charset=UTF-8">
    <title>QCOS API Doc</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {
            margin: 0;
            padding: 0;
        }
    </style>
    <style data-styled="" data-styled-version="4.4.1"></style>
</head>
<body>
    <div id="redoc-container"></div>
    <script src="js/redoc.standalone.js"> </script>
    <script>
        var spec = %s;
        Redoc.init(spec, {}, document.getElementById("redoc-container"));
    </script>
</body>
</html>
"""

if __name__ == "__main__":
    file_path = "api-docs/qcos-api-docs.html"
    with open(file_path, "w") as fd:
        print(HTML_TEMPLATE % json.dumps(app.openapi()), file=fd)
    print(f"Successfully created qcos api docs: {file_path}")

