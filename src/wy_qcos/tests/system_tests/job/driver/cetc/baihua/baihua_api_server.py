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

import json
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

logger = logging.getLogger(__name__)

# A stable instance ID returned by the mock /executetask endpoint
INSTANCE_ID = "mock-cetc-instance-0001"


class CetcApiHandler(BaseHTTPRequestHandler):
    """HTTP handler that simulates the CETC TianGong API."""

    def log_message(self, format, *args):
        logger.info(format, *args)

    def _send_json(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _parse_query(self):
        parsed = urlparse(self.path)
        return parse_qs(parsed.query), parsed.path

    def _read_json_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}

    # -- GET -------------------------------------------------------------

    def do_GET(self):
        params, path = self._parse_query()

        if path == "/taskdetail":
            self._handle_task_detail(params)
        elif path == "/qdevicedetail":
            self._handle_device_detail(params)
        elif path == "/tasklist":
            self._handle_task_list(params)
        else:
            self._send_json({"code": 404, "msg": "not found"}, status=404)

    def _handle_task_detail(self, params):
        self._send_json({
            "code": 200,
            "msg": "",
            "data": {
                "state": 2,
                "frequencyResult": [
                    {"qState": "00", "freq": 512},
                    {"qState": "11", "freq": 512},
                ],
            },
        })

    def _handle_device_detail(self, params):
        self._send_json({
            "code": 200,
            "msg": "",
            "data": {
                "state": 1,
                "maxQubits": 25,
                "jobNumber": 100,
                "time": "2026-08-14T15:05:35",
                "name": "Baihua",
                "nameEn": "Baihua",
                "singleBitInfo": [
                    {
                        "quantumBit": "Q0",
                        "T1": 100,
                        "T2": 80,
                        "singleFidelity": 0.99,
                        "fidelity0": 0.98,
                        "fidelity1": 0.97,
                    },
                    {
                        "quantumBit": "Q1",
                        "T1": 95,
                        "T2": 75,
                        "singleFidelity": 0.98,
                        "fidelity0": 0.97,
                        "fidelity1": 0.96,
                    },
                ],
                "doubleBitInfo": [
                    {"couplingQubits": "Q0-Q1", "czFidelity": 0.95},
                ],
            },
        })

    def _handle_task_list(self, params):
        self._send_json({
            "code": 200,
            "msg": "",
            "data": {"list": [], "total": 0},
        })

    # -- POST ------------------------------------------------------------

    def do_POST(self):
        _, path = self._parse_query()
        body = self._read_json_body()

        if path == "/executetask":
            self._handle_execute_task(body)
        else:
            self._send_json({"code": 404, "msg": "not found"}, status=404)

    def _handle_execute_task(self, body):
        self._send_json({
            "code": 200,
            "msg": "",
            "data": {"instanceId": INSTANCE_ID},
        })


def main(port=18611):
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(module)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    server_address = ("", port)
    httpd = HTTPServer(server_address, CetcApiHandler)
    logger.info(f"CETC mock API server starting on port {port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.server_close()
        logger.info("CETC mock API server stopped")


if __name__ == "__main__":
    main()
