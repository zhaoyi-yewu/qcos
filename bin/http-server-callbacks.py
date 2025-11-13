#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2025-2025 China Mobile (SuZhou) Software Technology Co.,Ltd.
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

import json

from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs


class CustomRequestHandler(BaseHTTPRequestHandler):
    """
    Custom Request handler
    """

    server_version = "CustomServer/1.0"
    sys_version = ""

    def _send_response(self, content, status=200, content_type="text/plain"):
        """
        Send response
        """
        self.send_response(status)
        self.send_header("Content-type", content_type)
        self.end_headers()
        self.wfile.write(content.encode("utf-8"))

    def do_GET(self):
        """
        Handle GET request
        """
        parsed_path = urlparse(self.path)
        query_params = parse_qs(parsed_path.query)

        if parsed_path.path == "/":
            self._send_response("Welcome to HTTP Server!")
        elif parsed_path.path == "/api/data":
            data = {"message": "API data", "params": query_params}
            self._send_response(json.dumps(data),
                                content_type="application/json")
        else:
            self._send_response("404 Not Found", status=404)

    def do_POST(self):
        """
        Handle POST request
        """
        content_length = int(self.headers["Content-Length"])
        post_data = self.rfile.read(content_length).decode("utf-8")

        if self.path == "/v1/job/set_job_results":
            try:
                print("OK")
                print(self.headers)
                print(post_data)
                json_data = json.loads(post_data)
                response = {"status": "success", "received": json_data}
                self._send_response(json.dumps(response),
                                    content_type="application/json")
            except json.JSONDecodeError:
                self._send_response("Invalid JSON", status=400)
        else:
            self._send_response("Unsupported endpoint", status=404)


if __name__ == "__main__":
    PORT = 8088
    server_address = ("", PORT)

    # create ThreadingHTTPServer
    httpd = ThreadingHTTPServer(server_address, CustomRequestHandler)

    print(f"Server is listening on port: {PORT}")
    httpd.serve_forever()
