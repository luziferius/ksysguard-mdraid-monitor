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

import collections
import time

from ksysguard_mdraid_monitor import constants
from ksysguard_mdraid_monitor.argument_parser import Namespace
from ksysguard_mdraid_monitor import command
from ksysguard_mdraid_monitor.model import RaidStatus


class KSysGuardDaemon:
    """
    Implements the application main loop. Information about general commands were sourced from
    https://github.com/KDE/ksysguard/blob/master/ksysguardd/Command.c

    """

    def __init__(self, args: Namespace):
        self.args = args
        self.command_table = self._build_command_table()
        self.prompt = "ksysguardd> "
        self.run_main_loop = True
        self.raid_status: RaidStatus = RaidStatus()
        self.raid_status_age = time.monotonic_ns()

    def _build_command_table(self) -> collections.defaultdict:

        # defaultdict calls the given function when instantiating the default value on unknown entries.
        # So use lambda to wrap the error handler, so that all lookups in the table return function objects.
        command_table = collections.defaultdict(lambda: self.command_not_found_error)
        command_table.update({
            "monitors": self.command_monitors,
            "quit": self.command_quit,
            "": lambda: (),  # Print nothing on empty input
        })
        for class_ in (
                command.TotalDeviceCount, command.ActiveDeviceCount, command.FailedDeviceCount, command.TotalComponentCount,
                ):
            self.register_monitor(command_table, class_)

        return command_table

    @staticmethod
    def _print_header():
        header = f"ksysguardd 4\n" \
                 f"{constants.COPYRIGHT} <{constants.AUTHOR_EMAIL}>\n" \
                 f"{constants.GPL_NOTICE}"
        print(header)

    def register_monitor(self, command_table: collections.defaultdict, command_class: command.AbstractMonitor):
        cmd = command_class(self)
        command_table[cmd.command] = cmd
        command_table[f"{cmd.command}?"] = cmd.command_info

    def _read_raid_status(self):
        now = time.monotonic_ns()
        if self.raid_status_age + self.args.min_interval_ms*1_000_000 <= now:
            self.raid_status = RaidStatus()

    def main_loop(self):
        self._print_header()
        while self.run_main_loop:
            try:
                buffer = input(self.prompt)
            except EOFError:
                self.command_quit()
                continue
            self._read_raid_status()
            self.command_table[buffer]()

    @staticmethod
    def command_not_found_error():
        """Default action on unknown input"""
        print("UNKNOWN COMMAND")

    def command_monitors(self):
        for cmd in self.command_table.values():
            if isinstance(cmd, command.AbstractMonitor):
                print(cmd.command_monitor_output)

    def command_quit(self):
        """Break the main loop"""
        self.run_main_loop = False
