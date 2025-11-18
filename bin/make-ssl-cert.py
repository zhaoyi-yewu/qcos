#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024-2025 China Mobile (SuZhou) Software Technology Co.,Ltd.
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

"""
make-ssl-cert.py -- Create SSL keys and certificates

Prerequisite:
yum install -y openssl
"""

import copy
import os
import subprocess
import sys
from pathlib import Path

from argparse import ArgumentParser, RawDescriptionHelpFormatter

TOP_DIR = Path(__file__).resolve().parent.parent
TEMP_DIR = "/tmp/qcos"
KEY_SIZE = 2048
CERT_C = "CN"
CERT_ST = "Suzhou"
CERT_L = "Suzhou"
CERT_O = "China Mobile (Suzhou) Software Technology Co., Ltd."
CERT_OU = "Institute of Future Technology (IOFT)"
CERT_CN = None
CERT_EM = "zhaoyi_yewu@cmss.chinamobile.com"
CERT_DAYS = 100 * 365


def mkdirs(dir):
    """Create dirs

    Args:
        dir: dir name
    """
    sub_path = os.path.dirname(dir)
    if not os.path.exists(sub_path):
        mkdirs(sub_path)
    if not os.path.exists(dir):
        os.mkdir(dir)


def read_file(file_path):
    """Read file content

    Args:
        file_path: file path

    Returns:
        file content
    """
    content = None
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    return content


def write_file(file_path, file_content):
    """Write file

    Args:
        file_path: file path
        file_content: file content

    Returns:

    """
    with open(file_path, 'wb') as output:
        bytes_data = file_content.encode("utf-8")
        output.write(bytes_data)


def make_ssl_cert(ip_list, dns_list, key_files, cert_days=CERT_DAYS):
    """Make SSL certificate

    Args:
        ip_list: IP list
        dns_list: DNS list
        key_files: key file list
        cert_days: certificate days

    Returns:
        return code (0: success, other: failed)
    """
    openssl_conf_temp_file = TEMP_DIR + "/openssl.conf"
    ssl_database_index_file = TEMP_DIR + "/index.txt"
    ssl_serial_file = TEMP_DIR + "/serial.txt"
    ssl_newcerts_dir = TEMP_DIR + "/"

    print("Generating SSL certificate: ")

    # check if key files exist
    key_file_list = []
    key_file_exist = True
    for key_file_name, key_file in key_files.items():
        if not os.path.exists(key_file):
            key_file_exist = False
    for key_file_name, key_file in key_files.items():
        key_file_list.append(key_file_name + ": " + key_file)
    key_files_str = ",".join(key_file_list)
    if key_file_exist:
        print(key_files_str + " are already existed, skip!")
        return 1

    # read ssl configs
    openssl_conf = f"{TOP_DIR}/etc/ssl/openssl.conf"
    file_content = read_file(openssl_conf)

    # prepare ssl configs
    ip_str_list = []
    dns_str_list = []
    common_name_list = []
    ip_set = set()
    dns_set = set()

    dns_index = 1
    for dns in dns_list:
        if dns not in dns_set:
            dns_set.add(dns)
            dns_str_list.append(f"DNS.{dns_index} = {dns}")
            dns_index += 1

    ip_index = 1
    for ip in ip_list:
        if ip not in ip_set:
            ip_set.add(ip)
            ip_str_list.append(f"IP.{ip_index} = {ip}")
            ip_index += 1

    ssl_info = copy.deepcopy(key_files)
    ssl_info["C"] = CERT_C
    ssl_info["ST"] = CERT_ST
    ssl_info["L"] = CERT_L
    ssl_info["O"] = CERT_O
    ssl_info["OU"] = CERT_OU
    ssl_info["CN"] = CERT_CN
    ssl_info["EM"] = CERT_EM
    ssl_info["DNS_LIST"] = "\n".join(dns_str_list)
    ssl_info["IP_LIST"] = "\n".join(ip_str_list)
    ssl_info["COMMON_NAME_LIST"] = "\n".join(common_name_list)

    ssl_info["openssl_conf_temp_file"] = openssl_conf_temp_file
    ssl_info["key_size"] = KEY_SIZE
    ssl_info["days"] = cert_days
    ssl_info["SSL_DATABASE"] = ssl_database_index_file
    ssl_info["SSL_SERIAL"] = ssl_serial_file
    ssl_info["SSL_NEWCERTS_DIR"] = ssl_newcerts_dir

    file_content = file_content.format(**ssl_info)
    write_file(openssl_conf_temp_file, file_content)

    cmds = []
    # create index, serial
    cmds.append("touch {SSL_DATABASE} {SSL_SERIAL}".format(**ssl_info))
    cmds.append("echo 01 > {SSL_SERIAL}".format(**ssl_info))

    # create server private-key
    cmds.append(
        "openssl genrsa -out {SSL_PRIVATE_KEY} {key_size}".format(**ssl_info))

    # create server CSR
    cmds.append(
        "openssl req -new -config {openssl_conf_temp_file} "
        "-key {SSL_PRIVATE_KEY} -out {SSL_CSR}".format(
            **ssl_info))

    # create CA cert private-key
    cmds.append(
        "openssl genrsa -out {CAKEY_PEM} {key_size}".format(**ssl_info))

    # create CA cert CSR
    cmds.append(
        "openssl req -new -x509 -config {openssl_conf_temp_file} -days {days} "
        "-key {CAKEY_PEM} -out {CACERT_PEM}".format(**ssl_info))

    # create CRT
    cmds.append(
        "openssl ca -in {SSL_CSR} -config {openssl_conf_temp_file} "
        "-days {days} -out {SSL_CRT} -batch".format(**ssl_info))

    # combine PEM
    cmds.append(
        "cat {SSL_CRT} {SSL_PRIVATE_KEY} > {COMBINED_PEM}".format(**ssl_info))

    # modify permissions for key files
    cmds.append(
        "chmod 400 {CAKEY_PEM} {CACERT_PEM} {SSL_CRT} {SSL_PRIVATE_KEY} "
        "{COMBINED_PEM}".format(**ssl_info))

    print("commands: ")
    print("\n".join(cmds))
    print("")
    ret = subprocess.call(";".join(cmds), shell=True)
    return ret


def main(argv=None):
    '''main'''

    if argv is None:
        argv = sys.argv
    else:
        sys.argv.extend(argv)

    program_shortdesc = __doc__.strip()
    program_license = f'''{program_shortdesc}

USAGE
'''

    try:
        # config parser
        parser = ArgumentParser(
            description=program_license,
            formatter_class=RawDescriptionHelpFormatter
        )
        parser.add_argument(
            "-i",
            "--ip-list",
            dest="ip_list",
            nargs="+",
            type=str,
            default=[],
            required=False,
            help="IP list, IPs can be specified multiple times",
        )
        parser.add_argument(
            "-n",
            "--dns-list",
            dest="dns_list",
            nargs="+",
            type=str,
            default=[],
            required=False,
            help="DNS list, DNSs can be specified multiple times",
        )
        parser.add_argument("-d", "--cert-days", dest="cert_days",
                            type=int,
                            default=CERT_DAYS,
                            help="Days to certify the cert")

        # parse arguments
        args = parser.parse_args()
        cert_days = args.cert_days
        ip_list = args.ip_list
        dns_list = args.dns_list

        if not any([ip_list, dns_list]):
            print("Please specify at least one argument: "
                  "either -i(--ip-list) or -n(--dns-list)\n")
            parser.print_help()
            return 1

        # prepare and generate ssl cert
        mkdirs(TEMP_DIR)
        key_files = {
            "SSL_PRIVATE_KEY": f"{TEMP_DIR}/ssl.key",
            "SSL_CSR": f"{TEMP_DIR}/ssl.csr",
            "SSL_CRT": f"{TEMP_DIR}/ssl.crt",
            "CAKEY_PEM": f"{TEMP_DIR}/cakey.pem",
            "CACERT_PEM": f"{TEMP_DIR}/cacert.pem",
            "COMBINED_PEM": f"{TEMP_DIR}/qcos-combined.pem"
        }
        ret = make_ssl_cert(ip_list=ip_list,
                            dns_list=dns_list,
                            key_files=key_files,
                            cert_days=cert_days)
        if ret != 0:
            print(f"Failed to generate ssl cert, error_code: {ret}")
            return ret

        # check key files
        err_msgs = []
        for key_file_name, key_file in key_files.items():
            if not os.path.exists(key_file):
                err_msgs.append(f"Can't find key/certificate file: {key_file}")
        if err_msgs:
            print("\n".join(err_msgs))
            ret = 1

        return ret

    except KeyboardInterrupt:
        print("\nUser interrupt", file=sys.stderr)
        return 0
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
