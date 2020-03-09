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
        self.md_device, self.is_active, self.raid_level, self.component_devices = self._parse_header_line(line_1)
        self.block_count, self.superblock_format, self.chunk_size, self.expected_device_count, \
            self.current_device_count = self._parse_block_count_line(line_2)

        # Set defaults for optional parts
        self.current_activity = "idle"
        self.progress_percent = 0.0
        self.currently_processed_block = 0
        self.activity_eta_minutes = 0.0
        self.speed_kbytes_per_sec = 0

        self.has_bitmap = False
        self.bitmap_used_pages = 0
        self.bitmap_total_pages = 0
        self.bitmap_used_size_kb = 0
        self.bitmap_chunk_size_kb = 0

        if line_3:
            if line_3.startswith("bitmap"):
                # Device has a bitmap and is currently idle
                self.has_bitmap = True
                self.bitmap_used_pages, self.bitmap_total_pages, self.bitmap_used_size_kb, self.bitmap_chunk_size_kb = \
                    self._parse_bitmap_line(line_3)
            else:
                # Device has no bitmap and a recovery, resync or check in progress
                self.current_activity, self.progress_percent, self.currently_processed_block, \
                    self.activity_eta_minutes, self.speed_kbytes_per_sec = self._parse_activity_line(line_3)
        
        if line_4:
            # Device has a bitmap and a recovery, resync or check in progress
            self.has_bitmap = True
            self.bitmap_used_pages, self.bitmap_total_pages, self.bitmap_used_size_kb, self.bitmap_chunk_size_kb = \
                self._parse_bitmap_line(line_4)
    
    @staticmethod
    def _parse_header_line(header_line: str):
        header_result = header_parser.match(header_line)
        md_device = header_result.group("md_device")
        is_active = header_result.group("is_active") == "active"
        raid_level = header_result.group("level")
        component_devices = header_result.group("components").strip().split(" ")
        return md_device, is_active, raid_level, component_devices
    
    @staticmethod
    def _parse_block_count_line(block_count_line: str):
        block_count_result = block_parser.match(block_count_line)
        block_count = int(block_count_result.group("block_count"))
        superblock_format = block_count_result.group("superblock_format")
        chunk_size = block_count_result.group("chunk_size")
        expected_device_count = int(block_count_result.group("expected_device_count"))
        current_device_count = int(block_count_result.group("current_device_count"))
        return block_count, superblock_format, chunk_size, expected_device_count, current_device_count

    @staticmethod
    def _parse_activity_line(activity_line: str):
        activity_result = activity_parser.match(activity_line)
        current_activity = activity_result.group("activity_mode")
        progress_percent = float(activity_result.group("progress"))
        currently_processed_block = int(activity_result.group("current_block"))
        activity_eta_minutes = float(activity_result.group("eta_min"))
        speed_kbytes_per_sec = int(activity_result.group("speed"))
        return current_activity, progress_percent, currently_processed_block, activity_eta_minutes, speed_kbytes_per_sec

    @staticmethod
    def _parse_bitmap_line(bitmap_line: str):
        bitmap_result = bitmap_parser.match(bitmap_line)
        bitmap_used_pages = int(bitmap_result.group("used_pages_count"))
        bitmap_total_pages = int(bitmap_result.group("total_pages_count"))
        bitmap_used_size_kb = int(bitmap_result.group("size_used_kb"))
        bitmap_chunk_size_kb = int(bitmap_result.group("bitmap_chunk_size_kb"))
        return bitmap_used_pages, bitmap_total_pages, bitmap_used_size_kb, bitmap_chunk_size_kb

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
    def degraded_device_count(self) -> int:
        return sum(1 for device in self.device_info if device.current_device_count < device.expected_device_count)

    @property
    def total_component_count(self) -> int:
        return sum(device.component_count for device in self.device_info)

    @property
    def bitmap_device_count(self) -> int:
        return sum(1 for device in self.device_info if device.has_bitmap)
