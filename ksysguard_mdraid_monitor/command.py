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

from abc import abstractmethod
import collections
import time
import typing

from .argument_parser import Namespace
from . import constants
from .model import RaidStatus


class AbstractMonitor:

    def __init__(self, parent):
        self.parent: KSysGuardDaemon = parent

    @property
    def command_monitor_output(self) -> str:
        return f"{self.command}\t{self.output_type}"

    def command_info(self):
        """Implements the info command "sensor_name?" that returns the value range and unit of this command."""
        if self.unit is None:
            result = f"{self.description}\t{self.min}\t{self.max}"
        else:
            result = f"{self.description}\t{self.min}\t{self.max}\t{self.unit}"
        print(result)

    def __call__(self, *args, **kwargs):
        print(self.command_value)

    @property
    @abstractmethod
    def command(self) -> str:
        """
        Returns the command string that can be used to query this monitor.
        """
        pass

    @property
    @abstractmethod
    def command_value(self):
        """
        Returns the monitor value.
        """
        pass

    @property
    @abstractmethod
    def output_type(self) -> str:
        """
        Used by the "monitors" command.
        Returns a string representation of the output type
        """
        pass

    @property
    @abstractmethod
    def description(self):
        """
        Used by the info command (f"{self.command}?").
        Returns a short descriptive name displayed by KSysGuard
        """
        pass

    @property
    @abstractmethod
    def min(self):
        """
        Used by the info command (f"{self.command}?").
        Returns the minimum value the sensor may have.
        """
        pass

    @property
    @abstractmethod
    def max(self):
        """
        Used by the info command (f"{self.command}?").
        Returns the maximum value the sensor may have.
        """
        pass

    @property
    @abstractmethod
    def unit(self) -> typing.Optional[str]:
        """
        Used by the info command (f"{self.command}?").
        Returns the sensor unit.
        """
        pass


class TotalDeviceCount(AbstractMonitor):
    """Reports the total number of /dev/mdX RAID devices."""
    @property
    def command(self) -> str:
        return "SoftRaid/TotalDevices"

    @property
    def command_value(self):
        return self.parent.raid_status.total_device_count

    @property
    def output_type(self) -> str:
        return "integer"

    @property
    def description(self):
        return "Total device count"

    @property
    def min(self):
        return 0

    @property
    def max(self):
        return 0

    @property
    def unit(self) -> typing.Optional[str]:
        return None


class ActiveDeviceCount(AbstractMonitor):
    """Reports the total number of active and working RAID devices. Upper bound is the total device count."""
    @property
    def command(self) -> str:
        return "SoftRaid/ActiveDevices"

    @property
    def command_value(self):
        return self.parent.raid_status.active_device_count

    @property
    def output_type(self) -> str:
        return "integer"

    @property
    def description(self):
        return "Active device count"

    @property
    def min(self):
        return 0

    @property
    def max(self):
        return self.parent.raid_status.total_device_count

    @property
    def unit(self) -> typing.Optional[str]:
        return None


class FailedDeviceCount(AbstractMonitor):
    """Reports the total number of inactive and failed RAID devices. Upper bound is the total device count."""
    @property
    def command(self) -> str:
        return "SoftRaid/FailedDevices"

    @property
    def command_value(self):
        return self.parent.raid_status.inactive_device_count

    @property
    def output_type(self) -> str:
        return "integer"

    @property
    def description(self):
        return "Failed device count"

    @property
    def min(self):
        return 0

    @property
    def max(self):
        return self.parent.raid_status.total_device_count

    @property
    def unit(self) -> typing.Optional[str]:
        return None


class DegradedDeviceCount(AbstractMonitor):
    """
    Reports the total number of degraded RAID devices (that have missing components).
    Upper bound is the total device count.
    """
    @property
    def command(self) -> str:
        return "SoftRaid/DegradedDevices"

    @property
    def command_value(self):
        return self.parent.raid_status.degraded_device_count

    @property
    def output_type(self) -> str:
        return "integer"

    @property
    def description(self):
        return "Degraded device count"

    @property
    def min(self):
        return 0

    @property
    def max(self):
        return self.parent.raid_status.total_device_count

    @property
    def unit(self) -> typing.Optional[str]:
        return None


class TotalComponentCount(AbstractMonitor):
    """Reports the total number of RAID components. This is the sum of all component devices of all RAID devices"""
    @property
    def command(self) -> str:
        return "SoftRaid/TotalComponents"

    @property
    def command_value(self):
        return self.parent.raid_status.total_component_count

    @property
    def output_type(self) -> str:
        return "integer"

    @property
    def description(self):
        return "Total component count"

    @property
    def min(self):
        return 0

    @property
    def max(self):
        return 0

    @property
    def unit(self) -> typing.Optional[str]:
        return None


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
                TotalDeviceCount, ActiveDeviceCount, FailedDeviceCount, TotalComponentCount,
                ):
            self.register_monitor(command_table, class_)

        return command_table

    @staticmethod
    def _print_header():
        header = f"ksysguardd 4\n" \
                 f"{constants.COPYRIGHT} <{constants.AUTHOR_EMAIL}>\n" \
                 f"{constants.GPL_NOTICE}"
        print(header)

    def register_monitor(self, command_table: collections.defaultdict, command_class: AbstractMonitor):
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
            if isinstance(cmd, AbstractMonitor):
                print(cmd.command_monitor_output)

    def command_quit(self):
        """Break the main loop"""
        self.run_main_loop = False
