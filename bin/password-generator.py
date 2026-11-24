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

"""Generate a secure password containing all supported character types."""

import argparse
import secrets
import string


DEFAULT_LENGTH = 8
SPECIAL_CHARACTERS = "@$%^*"
CHARACTER_SETS = (
    string.ascii_lowercase,
    string.ascii_uppercase,
    string.digits,
    SPECIAL_CHARACTERS,
)
MIN_LENGTH = len(CHARACTER_SETS)
ALL_CHARACTERS = "".join(CHARACTER_SETS)


def generate_password(length=DEFAULT_LENGTH):
    """Generate a password with at least one character from each set."""
    if length < MIN_LENGTH:
        raise ValueError(f"Password length must be at least {MIN_LENGTH}.")

    characters = [secrets.choice(chars) for chars in CHARACTER_SETS]
    characters.extend(
        secrets.choice(ALL_CHARACTERS) for _ in range(length - MIN_LENGTH)
    )
    secrets.SystemRandom().shuffle(characters)
    return "".join(characters)


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate a secure password with uppercase and lowercase "
        "letters, digits, and special characters (@$%^*)."
    )
    parser.add_argument(
        "-l",
        "--length",
        type=int,
        default=DEFAULT_LENGTH,
        help=f"password length (default: {DEFAULT_LENGTH}, "
        f"minimum: {MIN_LENGTH})",
    )
    args = parser.parse_args()
    if args.length < MIN_LENGTH:
        parser.error(f"--length must be at least {MIN_LENGTH}")
    return args


def main():
    """Generate and print a password."""
    args = parse_args()
    print(generate_password(args.length))


if __name__ == "__main__":
    main()
