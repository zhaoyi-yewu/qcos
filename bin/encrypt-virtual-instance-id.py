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
encrypt-virtual-instance-id.py -- encrypt/decrypt virtual instance id

Encryption example:
./encrypt-virtual-instance-id.py -e -s 1234 -dn dummy -i 1234567890

Decryption example:
./encrypt-virtual-instance-id.py -d -s 1234 -vi ZHVtbXl8MTIzNDU2Nzg5MHwzNGNk
"""

import sys

from argparse import ArgumentParser, RawDescriptionHelpFormatter

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
        mode_group = parser.add_mutually_exclusive_group(required=True)
        mode_group.add_argument("-e", "--encrypt", action="store_true",
                                dest="encryption_mode",
                                help="encryption mode")
        mode_group.add_argument("-d", "--decrypt", action="store_true",
                                dest="decryption_mode",
                                help="decryption mode")

        encryption_mode = parser.add_argument_group("Encryption mode")
        encryption_mode.add_argument("-dn", "--device-names",
                                     dest="device_names",
                                     nargs="+",
                                     help="device names")
        encryption_mode.add_argument("-i", "--instance-id",
                                     dest="instance_id",
                                     help="instance id")

        decryption_mode = parser.add_argument_group("Decryption mode")
        decryption_mode.add_argument("-vi", "--virtual-instance-id",
                                     dest="virtual_instance_id",
                                     help="virtual instance id")
        parser.add_argument("-s", "--salt", dest="salt",
                            required=True,
                            help="Salt")

        # parse arguments
        args = parser.parse_args()
        device_names = args.device_names
        instance_id = args.instance_id
        virtual_instance_id = args.virtual_instance_id
        salt = args.salt
        if args.encryption_mode:
            if not device_names or not instance_id:
                print("Error: device_name and instance_id are required "
                      "in encryption mode")
                exit(1)
            if virtual_instance_id:
                print("Error: virtual_instance_id should not be set "
                      "in encryption mode")
                exit(1)
        elif args.decryption_mode:
            if not virtual_instance_id:
                print("Error: virtual_instance_id is required "
                      "in decryption mode")
                exit(1)
            if device_names or instance_id:
                print("Error: device_name and instance_id should not be set "
                      "in decryption mode")
                exit(1)

        # Handle encryption
        if args.encryption_mode:
            success, err_msg, virtual_instance_id = \
                Library.encrypt_virtual_instance_id(
                    device_names,
                    instance_id,
                    salt=salt,
                    encode=True)
            if success:
                print("[Input]")
                print(f"device_name: {', '.join(device_names)}")
                print(f"instance_id: {instance_id}, salt: {salt}")
                print("")
                print("[Output]")
                print(f"virtual_instance_id: {virtual_instance_id}")
                print(f"export QCOS_VIRTUAL_INSTANCE_ID={virtual_instance_id}")
                print("")
            else:
                print(f"{err_msg}", file=sys.stderr)

        # Handle decryption
        if args.decryption_mode:
            success, err_msg, device_names, instance_id = \
                Library.decrypt_virtual_instance_id(
                    virtual_instance_id,
                    salt=salt, encode=True)
            if success:
                print("Decryption is successful")
                print("[Input]")
                print(f"virtual_instance_id: {virtual_instance_id}")
                print(f"salt: {salt}")
                print("")
                print("[Output]")
                print(f"device_names: {', '.join(device_names)}")
                print(f"instance_id: {instance_id}")
                print("")
            else:
                print(f"{err_msg}", file=sys.stderr)

        return 0

    except KeyboardInterrupt:
        print("\nUser interrupt", file=sys.stderr)
        return 0
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
