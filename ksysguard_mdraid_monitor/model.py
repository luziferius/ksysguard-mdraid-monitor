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

from pathlib import Path
import re


proc_mdstat_path = Path("/", "proc", "mdstat")

header_parser = re.compile(  # Parses the first line of each block, beginning with the md device name
    r"^md(?P<md_device>[1-9][0-9]+|[0-9]) : (?P<is_active>(in)?active) (?P<level>[a-z0-9]*)(?P<components> .*)"
)
block_parser = re.compile(
    r"^(?P<block_count>\d+) blocks "  # total block count
    r"(super (?P<superblock_format>\d+.\d+) )?"  # Optional superblock format
    r"(?P<level>linear|faulty|multipath|level \d+)?"  # Optional raid level. Not used for raid 1
    r"(, (?P<chunk_size>\S+) chunk, algorithm (?P<algorithm>\d+) )?"  # Chunk and algorithm. raid 4/5/6 only (?)
    r"\[(?P<expected_device_count>\d+)/(?P<current_device_count>\d+)\] "  # Current and expected device count
    r"\[[U_]+\]$"  # Missing/present devices graphic
)

activity_parser = re.compile(  # Parses a currently running activity: recovery, resync and check
    r"^\[=.*>\.*]\s+"  # Graphical progress indicator
    r"(?P<activity_mode>\S+) = (?P<progress>([1-9]\d{1,2}|\d)\.\d)% "  # Activity and progress in percent
    r"\((?P<current_block>\d+)/(?P<total_blocks>\d+)\) "  # Currently processed block and total block count
    r"finish=(?P<eta_min>\d+\.\d)min"  # Fractional ETA in minutes
    r"( speed=(?P<speed>\d+)K/sec)?"  # Current speed in kbytes/second . Optional?
)
bitmap_parser = re.compile(  # Parses the bitmap usage, for arrays that have it enabled.
    r"^bitmap: (?P<used_pages_count>\d+)/(?P<total_pages_count>\d+) pages "
    r"\[(?P<size_used_kb>\d)KB\], (?P<bitmap_chunk_size_kb>\d+)KB chunk"
)


class RaidDeviceInfo:
    """Groups information for a single MD device. Parses a single block from mdstat output."""
    def __init__(self, line_1: str, line_2: str, line_3: str = None, line_4: str = None):
        line_1_result = header_parser.match(line_1)
        self.md_device = line_1_result.group("md_device")
        self.is_active = line_1_result.group("is_active") == "active"
        self.raid_level = line_1_result.group("level")
        self.component_devices = line_1_result.group("components").split(" ")

        if line_3:
            if not line_3.startswith("bitmap"):
                # Recovery, resync or check in progress
                pass

    @property
    def component_count(self) -> int:
        return len(self.component_devices)


class RaidStatus:
    """Parses the current RAID status by parsing /proc/mdstat output"""
    def __init__(self, mdstat: str = None):
        if mdstat is None:
            mdstat = self._read_status_from_proc()
        self.device_info = list(self._parse_device_info(mdstat))

    @staticmethod
    def _read_status_from_proc() -> str:
        if not proc_mdstat_path.exists():
            raise RuntimeError(f"Can’t access {proc_mdstat_path}. File does not exist.")
        return proc_mdstat_path.read_text(encoding="ascii")

    @staticmethod
    def _parse_device_info(mdstat: str):
        block_lines = []
        for line in mdstat.splitlines(keepends=False):
            line = line.strip()  # Some empty lines actually contain whitespace characters.
            if RaidStatus._should_skip_line(line):
                continue
            if line:
                block_lines.append(line)
            else:
                yield RaidDeviceInfo(*block_lines)
                block_lines.clear()

    @staticmethod
    def _should_skip_line(line: str) -> bool:
        ignored_lines = [
            "Personalities",
            "read_ahead",  # Some platforms seem to output the global read-ahead as the second line
            "unused devices:",

        ]
        return any(line.startswith(ignored) for ignored in ignored_lines)

    @property
    def total_device_count(self) -> int:
        return len(self.device_info)

    @property
    def active_device_count(self) -> int:
        return sum(1 for device in self.device_info if device.is_active)

    @property
    def inactive_device_count(self) -> int:
        return sum(1 for device in self.device_info if not device.is_active)

    @property
    def total_component_count(self) -> int:
        return sum(device.component_count for device in self.device_info)
