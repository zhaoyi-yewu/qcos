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

import logging
import urllib
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

logger = logging.getLogger(__name__)


class DataParseHandler(BaseHTTPRequestHandler):
    def _parse_url_params(self):
        """Parse query parameters in URL."""
        parsed_url = urlparse(self.path)
        query_params = parse_qs(parsed_url.query)
        return query_params

    def _parse_multipart_data(self):
        """Parse multipart/form-data type requests."""
        boundary = (
            self.headers.get("Content-Type")
            .split("boundary=")[-1]
            .encode("utf-8")
        )
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        parts = body.split(b"--" + boundary)
        data = {"fields": {}, "files": {}}

        for part in parts[1:-1]:
            part = part.strip()
            if not part:
                continue

            header_part, content_part = part.split(b"\r\n\r\n", 1)
            headers = {}
            for line in header_part.decode("utf-8").split("\r\n"):
                if ":" in line:
                    key, value = line.split(":", 1)
                    headers[key.strip()] = value.strip()

            content_disposition = headers.get("Content-Disposition", "")
            if "name=" in content_disposition:
                name = content_disposition.split('name="')[1].split('"')[0]

                if "filename=" in content_disposition:
                    filename = content_disposition.split('filename="')[
                        1
                    ].split('"')[0]

                    file_content = content_part.rstrip(b"\r\n")
                    data["files"][name] = {
                        "filename": filename,
                        "content": file_content,
                    }
                else:
                    data["fields"][name] = content_part.decode("utf-8").rstrip(
                        "\r\n"
                    )
        return data

    def _parse_json_data(self):
        """Parse requests of type application/json."""
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8")
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return {"error": "Invalid JSON"}

    def _parse_form_data(self):
        """Parsing requests of type application/x-www-form-urlencoded."""
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8")
        params = urllib.parse.parse_qs(body)
        return {k: v[0] for k, v in params.items()}

    def do_GET(self):
        url_params = self._parse_url_params()

        self.send_response(200)
        self.send_header("Content-type", "application/json; charset=utf-8")
        self.end_headers()
        if "machine_id" in url_params:
            response = {
                "code": "0",
                "msg": "",
                "data": {"token": {"access": "qaz1"}, "status": 1},
            }
        elif "task_name" in url_params:
            response = {
                "code": "0",
                "msg": "",
                "data": {"data": [{"id": "123", "status": 5}]},
            }
        else:
            response = {
                "code": "0",
                "msg": "",
                "data": {
                    "out_data": [
                        {
                            "result": 1,
                            "quboValue": -235.0,
                            "maxcutValue": 60.5,
                            "solutionVector": [
                                1,
                                1,
                                1,
                                1,
                                0,
                                1,
                                1,
                                1,
                                0,
                                0,
                                0,
                                0,
                                0,
                                1,
                                0,
                                0,
                                0,
                                1,
                                1,
                                0,
                                1,
                                0,
                                1,
                                1,
                                1,
                                1,
                                0,
                                1,
                                1,
                                1,
                                0,
                                1,
                                1,
                                0,
                                1,
                                0,
                                1,
                                1,
                                0,
                                1,
                                1,
                                0,
                                1,
                                1,
                                0,
                                1,
                                0,
                                0,
                                1,
                                1,
                                1,
                                0,
                                0,
                                1,
                                1,
                                0,
                                1,
                                1,
                                0,
                                1,
                                1,
                                1,
                                1,
                                0,
                                0,
                                0,
                                1,
                                0,
                                1,
                                1,
                                1,
                                0,
                                0,
                                1,
                                1,
                                1,
                                1,
                                0,
                                1,
                                0,
                                1,
                                0,
                                0,
                                1,
                                1,
                                1,
                                0,
                                0,
                                1,
                                1,
                                1,
                                1,
                                0,
                                1,
                                1,
                                1,
                                0,
                                1,
                                0,
                            ],
                        }
                    ],
                    "visual_data": [
                        4.0,
                        -43.0,
                        -43.0,
                        -43.0,
                        -147.0,
                        -147.0,
                        -155.0,
                        -177.0,
                        -177.0,
                        -190.0,
                        -197.0,
                        -209.0,
                        -212.0,
                        -220.0,
                        -220.0,
                        -220.0,
                    ],
                },
            }

        self.wfile.write(
            json.dumps(response, ensure_ascii=False).encode("utf-8")
        )

    def do_POST(self):
        content_type = self.headers.get("Content-Type", "")

        if "application/json" in content_type:
            request_data = self._parse_json_data()
        elif "application/x-www-form-urlencoded" in content_type:
            request_data = self._parse_form_data()
        elif "multipart/form-data" in content_type:
            request_data = self._parse_multipart_data()
        else:
            request_data = {
                "raw": self.rfile.read(
                    int(self.headers.get("Content-Length", 0))
                ).decode("utf-8")
            }

        self.send_response(200)
        self.send_header("Content-type", "application/json; charset=utf-8")
        self.end_headers()

        if "username" in request_data:
            response = {
                "code": "0",
                "msg": "",
                "data": {"token": {"access": "ok"}, "status": 1},
            }
        elif "files" in request_data:
            response = {
                "code": "0",
                "msg": "",
                "data": {"creator": "creator1", "id": "123", "name": "name1"},
            }
        elif "data" in request_data:
            response = {
                "code": "0",
                "msg": "",
            }
        else:
            response = {}
        self.wfile.write(
            json.dumps(response, ensure_ascii=False).encode("utf-8")
        )


def main():
    server_address = ("", 18601)
    httpd = HTTPServer(server_address, DataParseHandler)
    logger.info("server start")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.server_close()
        logger.info("server stop")


if __name__ == "__main__":
    main()
