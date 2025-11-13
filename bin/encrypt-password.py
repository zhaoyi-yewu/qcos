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

"""
encrypt-password.py -- encrypt/decrypt password

Prerequisite:
pip3 install cryptography
or
yum install -y python3-cryptography
"""

import sys

from argparse import ArgumentParser, RawDescriptionHelpFormatter

from qcos.common.constant import Constant
from qcos.common.library import Library


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
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument("-e", "--encrypt", dest="plain_text",
                           help="text needs to be encrypted")
        group.add_argument("-d", "--decrypt", dest="cipher_text",
                           help="text needs to be decrypted")
        parser.add_argument("-k", "--key", dest="fernet_key",
                            default=Constant.DEFAULT_FERNET_KEY,
                            help="Fernet key")

        # parse arguments
        args = parser.parse_args()
        plain_text = args.plain_text
        cipher_text = args.cipher_text

        # fernet cipher suite with provided key
        fernet_key = args.fernet_key

        # Handle text encryption
        if plain_text:
            success, err_msg, encrypted_text = Library.encrypt_text(
                plain_text,
                encryption_prefix=Constant.ENCRYPTION_PREFIX,
                fernet_key=fernet_key)
            if success:
                print(f"Original text : {plain_text}")
                print(f"Encrypted text: {encrypted_text}")
            else:
                print(f"Encryption failed. Reason: {err_msg}", file=sys.stderr)

        # Handle text decryption
        if cipher_text:
            success, err_msg, decrypted_text = Library.decrypt_text(
                cipher_text,
                encryption_prefix=Constant.ENCRYPTION_PREFIX,
                fernet_key=fernet_key)
            if success:
                print(f"Encrypted text: {cipher_text}")
                print(f"Decrypted text: {decrypted_text}")
            else:
                print(f"Decryption failed. Reason: {err_msg}", file=sys.stderr)

        return 0

    except KeyboardInterrupt:
        print("\nUser interrupt", file=sys.stderr)
        return 0
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
