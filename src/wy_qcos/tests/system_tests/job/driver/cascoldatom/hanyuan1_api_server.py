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

import base64
import json
import logging

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend
from http.server import BaseHTTPRequestHandler, HTTPServer
from wy_qcos.common.library import _s

logger = logging.getLogger(__name__)


# Same RSA key pair used in unit tests
PASSWORD_PRI_KEY = _s(
    "MIICeAIBADANBgkqhkiG9w0BAQEFAASCAmIwggJeAgEAAoGBAL+S1b9o7RbU0zhBdvV"
    "NijpIdCNMy3hx+G+H1rflVnhB0rE/4eNkTS5v3iDNMhhqBZKjAslyBcq6FQS55EgShH"
    "UeK4rXUPI8k0yfonxnemT/t7wI9nCgI9lb5HUffzj4B9RRlhmeqTuW8w9GEBoNQZxMD"
    "6sCn1zghWskrZrNhsjbAgMBAAECgYEAuWle0Mu3s8I1z5uki5QJdZFMPiIER8VeomtB"
    "SGiBgRCL35spgBBClvAUd4DBvFlYnWyBtQBTVLs2voU/yPWLFbZgKhRMBY1KbD8lgV6"
    "vVfMnZvLxsvt6HGAFNauOZ7JwnwaaLSNFSR+kApjSIh5rzrPufjQ5U+1TlQiebdXAFm"
    "kCQQDiWHedCvlrIAC7txgApzodRu6TjpnCk3+r+21FD75/uQDV3OcI6D8A+UkkP22Dm"
    "6ZR5FsHZgriN9s144H+omcHAkEA2KwhPBjh3C6mW/OPGhPLJwf7pCoJRT6Y+KME76kY"
    "bpBO99aEJqH8B3e7mEHGeZGyD3E0FODwbJvshqy4k68mjQJBAKlBfFiL700jBklYtfM"
    "vGa7w7tCajvJId+00O1asWkiKIEzMPluTyCFDSGV5pLwIdYvBViynKrZVDHA0q22tJZ"
    "sCQE98RezwC9tkWa8d2H9uh3ZYHV6J9UCryB5eX280DzxwQCf3UB+ECRsMN4uRhagPZ"
    "Mz5cGvAYTLWuJxnPIchF/kCQQDYtMa3+Yys8GjTe6gvkd6rQ7b6X3pTW2em8KfirlWe"
    "VAZtYs/MxYJZcuFy26lFA+DtO7Rg2GzhIKkUrzvqvgkQ"
)

PASSWORD_PUB_KEY = _s(
    "MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQC/ktW/aO0W1NM4QXb1TYo6SHQjTMt"
    "4cfhvh9a35VZ4QdKxP+HjZE0ub94gzTIYagWSowLJcgXKuhUEueRIEoR1HiuK11DyPJ"
    "NMn6J8Z3pk/7e8CPZwoCPZW+R1H384+AfUUZYZnqk7lvMPRhAaDUGcTA+rAp9c4IVrJ"
    "K2azYbI2wIDAQAB"
)

PASSWORD_SECRET = _s("test_password_secret")


def decrypt_by_private_key(raw_data):
    """Decrypt by private key.

    Args:
        raw_data: raw encrypted data

    Returns:
        decrypted data
    """
    private_key_der = base64.b64decode(PASSWORD_PRI_KEY)
    private_key = serialization.load_der_private_key(
        private_key_der, password=None, backend=default_backend()
    )
    ciphertext = base64.b64decode(raw_data)
    decrypted_parts = []
    max_length = private_key.key_size // 8
    for i in range(0, len(ciphertext), max_length):
        part = ciphertext[i : i + max_length]
        decrypted_part = private_key.decrypt(part, padding.PKCS1v15())
        decrypted_parts.append(decrypted_part)
    plaintext = b"".join(decrypted_parts)
    return json.loads(plaintext.decode("utf-8"))


def encrypt_by_public_key(raw_data):
    """Encrypt by public key.

    Args:
        raw_data: raw_data

    Returns:
        encrypted data
    """
    public_key_der = base64.b64decode(PASSWORD_PUB_KEY)
    public_key = serialization.load_der_public_key(
        public_key_der, backend=default_backend()
    )

    plaintext = json.dumps(raw_data, ensure_ascii=False).encode("utf-8")

    key_size_bytes = public_key.key_size // 8
    max_length = key_size_bytes - 11
    encrypted_parts = []

    for i in range(0, len(plaintext), max_length):
        part = plaintext[i : i + max_length]
        encrypted_part = public_key.encrypt(part, padding.PKCS1v15())
        encrypted_parts.append(encrypted_part)

    ciphertext = b"".join(encrypted_parts)
    return base64.b64encode(ciphertext).decode("utf-8")


class Hanyuan1DataHandler(BaseHTTPRequestHandler):
    """HTTP request handler for Hanyuan1 mock API server."""

    def _send_json_response(self, response_data):
        """Send JSON response.

        Args:
            response_data: response data dict
        """
        encrypted_response = encrypt_by_public_key(response_data)
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(encrypted_response.encode("utf-8"))

    def do_POST(self):
        """Handle POST requests."""
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8")

        logger.info(f"Received POST request to path: {self.path}")

        if self.path.endswith("/task/WuYue/submit"):
            self._handle_submit(body)
        elif self.path.endswith("/task/WuYue/query"):
            self._handle_query(body)
        elif self.path.endswith("/task/WuYue/queryParam"):
            self._handle_query_param(body)
        else:
            self.send_response(404)
            self.end_headers()

    def _handle_submit(self, body):
        """Handle task submit request.

        Args:
            body: request body
        """
        # Decrypt the request data
        try:
            request_data = decrypt_by_private_key(body)
            logger.info(f"Submit request data: {request_data}")
        except Exception:
            logger.info("Submit request received")

        response_data = {
            "code": 1,
            "msg": "Success",
            "data": None,
        }
        logger.info("Submit task response: code=1, msg=Success")
        self._send_json_response(response_data)

    def _handle_query(self, body):
        """Handle task query request.

        Args:
            body: request body
        """
        # Decrypt the request data
        try:
            request_data = decrypt_by_private_key(body)
            logger.info(f"Query request data: {request_data}")
        except Exception as e:
            logger.warning(f"Handle_query occurs exception: {e}")

        # Simulate completed status
        response_data = {
            "code": 1,
            "msg": "Success",
            "data": [
                {
                    "taskStatus": 5,  # task_status_completed
                    "outData": {
                        "lineResult": {
                            "0000": 25,
                            "0001": 25,
                            "0010": 25,
                            "0011": 25,
                        },
                        "optimization": "OPTIMIZED_CIRCUIT",
                        "grid": "GRID_INFO",
                    },
                    "execStartTime": 1700000000,
                    "execEndTime": 1700001000,
                    "timeConsume": "10.00",
                }
            ],
        }
        logger.info("Query task response: task_status=completed")
        self._send_json_response(response_data)

    def _handle_query_param(self, body):
        """Handle device info query request.

        Args:
            body: request body
        """
        response_data = {
            "code": 1,
            "msg": "Success",
            "data": {
                "singleFidelity": 0.99,
                "doubleFidelity": 0.95,
                "SPAMError": 0.01,
                "horizontalRelaxationTime": 132,
                "uniformityDephasingTime": 120,
                "nonUniformityDephasingTime": 110,
                "verticalRelaxationTime": 100,
                "tweezersNum": 100,
                "vaccum": 1.2,
                "rydbergExcitation": 0.85,
                "transportFidelity": 0.98,
                "elementAtom": "Rb",
                "time": "2024-01-01 00:00:00",
            },
        }
        logger.info("Query param response: success")
        self._send_json_response(response_data)

    def log_message(self, fmt, *args):
        """Override to use logging instead of stderr."""
        logger.info(f"{fmt % args}")


def main(port=18609):
    """Start the mock Hanyuan1 API server."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(module)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    server_address = ("", port)
    httpd = HTTPServer(server_address, Hanyuan1DataHandler)
    logger.info(f"Mock Hanyuan1 API server started on port {port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.server_close()
        logger.info("Mock Hanyuan1 API server stopped")


if __name__ == "__main__":
    main()
