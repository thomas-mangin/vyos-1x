#!/usr/bin/env python3
#
# numeric value validator
#
# Copyright (C) 2017 VyOS maintainers and contributors
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; If not, see <http://www.gnu.org/licenses/>.

import sys
import argparse

def main():
    'checks if a number matches some constraints'

    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--float", action="store_true", help="Accept floating point values")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-r", "--range", type=str, help="Check if the number is within range (inclusive), example: 1024-65535", action='append')
    group.add_argument("-n", "--non-negative", action="store_true", help="Check if the number is non-negative (>= 0)")
    group.add_argument("-p", "--positive", action="store_true", help="Check if the number is positive (> 0)")
    parser.add_argument("number", type=str, help="Number to validate")

    args = parser.parse_args()

    if args.float:
        converter = float
        name = 'floating point'
    else:
        converter = int
        name = 'integer'

    try:
        number = converter(args.number)
    except Exception:
        sys.exit(f'{args.number} is not a valid {name} number')

    if args.range:
        try:
            for r in args.range:
                _lower, _upper = r.split('-')
                lower = int(_lower)
                upper = int(_upper)
        except:
            sys.exit(f'{args.range} is not a valid number range')

        if number < lower or number > upper:
            span = args.range if len(args.range) > 1 else args.range[0]
            sys.exit('Number {number} is not in the range {span}')

    elif args.non_negative and number < 0:
        sys.exit('Number should be non-negative')

    elif args.positive and number <= 0:
        sys.exit('Number should be positive')

    sys.exit()


if __name__ == '__main__':
    main()