ksysguard_mdraid_monitor
========================

This program implements a ``KSysGuardd``-compatible monitor for the KDE system monitor KSysGuard.
It can be used to monitor MDRaid software RAID on Linux using the KDE system monitor. KSysGuard supports monitoring
of MDRaid by itself, but only offers highly local and specific sensors. This program supplements the available sensors
by offering aggregate sensors that provide a broader overview of the RAID health.

Current development state
-------------------------

The program works on the developer’s machine, but there are no unit tests that verify the parsing
of ``/proc/mdstat`` for all possible situations.
Consider it to be in an early alpha state. It currently offers only very basic sensors:

- Total number of RAID arrays in the system (``/dev/mdX``)
- Number of active/healthy RAID arrays
- Number of inactive/failed RAID arrays
- Number of degraded RAID arrays
- Number of arrays enqueued for any kind of maintenance task
- Number of arrays enqueued for a specific maintenance task (check, re-sync, recovery)
- Number of arrays with bitmaps
- Bitmap page usage across all arrays with bitmaps
- Aggregate total number of RAID component devices across all arrays


Requirements
------------

- Python >= 3.7 (3.6 may work, but is untested. <=3.5 is definitely unsupported)
- Linux with mounted ``/proc`` file system. ``/proc/mdstat`` present in ``/proc``.

Install
-------

Install latest version from the source checkout: :code:`pip3 install .`.

As an alternative, you can run the program directly from the repository checkout without installation.
The repository contains a simple runner script (named ``ksysguard_mdraid_monitor-runner.py``)
that can be used for this purpose.

Usage
-----

Usage within KSysGuard
++++++++++++++++++++++

This is the recommended usage of this program. Instructions for integration into KSysGuard:

- Open KSysGuard GUI
- Click on ``File`` → ``Monitor Remote Machine…``
- This opens a configuration dialogue window. Set these values:
   - ``Host``: Enter a name under which the sensors become available in the sensor browser
   - ``Connection Type``: Select ``Custom command``
   - ``Command``: Enter either ``ksysguard_mdraid_monitor`` or the full path to ``ksysguard_mdraid_monitor-runner.py``
   - Click OK
- The sensors will be available in the ``Sensor Browser`` when editing a Tab.
- Drag at least one sensor into a tab. Otherwise the connection will be removed when closing KSysGuard, as KSysGuard discards unused, external monitors on exit.


Direct usage
++++++++++++

This mode is not that useful, as the command line interface is designed for automatic usage by other programs. It does
not provide a nice, interactive interface. Nonetheless, it can be used directly:

Execute :code:`ksysguard_mdraid_monitor` after installation or run
:code:`./ksysguard_mdraid_monitor-runner.py` from the source tree,
if you have cloned the development repository.

When started, the program outputs a prompt for command input: ``ksysguardd>``. You can use these commands:


+-------------------+---------------------------------------------------------------------------------------------+------------------------------------------------------+
| Command           | Description                                                                                 | Output format                                        |
+===================+=============================================================================================+======================================================+
| quit              | Exit ``ksysguard_mdraid_monitor``. Use ``[Ctrl]+D`` as an alternative.                      |                                                      |
+-------------------+---------------------------------------------------------------------------------------------+------------------------------------------------------+
| monitors          | List all available sensors, one per line                                                    | ``<sensor_name>\t<sensor_unit>``                     |
+-------------------+---------------------------------------------------------------------------------------------+------------------------------------------------------+
|``<sensor_name>``  | One of the sensor names from ``monitors`` output. Prints the raw sensor value without unit  | ``<raw_output_value>``                               |
+-------------------+---------------------------------------------------------------------------------------------+------------------------------------------------------+
|``<sensor_name?>`` | Information about the sensor: short name/description, minimum value, maximum value and unit | ``<text>\t<min_value>\t<max_value>\t<sensor_unit>``  |
+-------------------+---------------------------------------------------------------------------------------------+------------------------------------------------------+

About
-----

Copyright (C) 2020, Thomas Hess

This program is licensed under the GNU GENERAL PUBLIC LICENSE Version 3.
See the LICENSE file for details.
