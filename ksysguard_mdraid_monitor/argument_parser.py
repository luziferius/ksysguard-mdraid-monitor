# Copyright (C) 2020 Thomas Hess <thomas.hess@udo.edu>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import argparse
import typing

import ksysguard_mdraid_monitor.constants


class NonNegativeInt(int):
    def __new__(cls, *args, **kwargs):
        new: NonNegativeInt = super(NonNegativeInt, cls).__new__(cls, *args, **kwargs)
        if new < 0:
            raise ValueError(f"Invalid number. Expected a non-negative integer. Got {new}.")
        return new


class Namespace(typing.NamedTuple):
    """
    Mocks the Namespace object returned by the argument parser as the result of parsing the arguments.
    Used in type hints to provide better type inference and static analysis.
    This is never instantiated in the code, except for maybe in unit tests.
    """
    min_interval_ms: NonNegativeInt


def generate_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-i", "--min-interval", dest="min_interval_ms", metavar="MILLISECONDS",
        type=NonNegativeInt, default=NonNegativeInt(10),
        help="Minimal delay between querying /proc/mdstat in milliseconds. This delay avoids unnecessary re-parsing "
             "of /proc/mdstat if multiple values are requested by KSysGuard in quick succession. Defaults to "
             "%(default)i ms. Requires a non-negative integer."
    )
    parser.add_argument(
        '-V', '--version',
        action='version',
        version=f'%(prog)s {ksysguard_mdraid_monitor.constants.__version__}'
    )
    return parser


def parse_arguments() -> Namespace:
    parser = generate_argument_parser()
    args = parser.parse_args()
    return args
