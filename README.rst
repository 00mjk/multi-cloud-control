Unified CLI Utility for AWS, Azure and GCP Instance Control
===========================================================

MCC: Command-Line Instance Control for Top 3 Enterprise Cloud Providers
-----------------------------------------------------------------------

The Multi-Cloud-Control utility, mcc, is currently in alpha and allows
listing basic information from instances on AWS, Azure and GCP in one report
with one simple command: ``mcc``.

Planned future enhancements:
- start and stop instances
- connect to instances via ssh
- image / snapshot instances
- change instance configuration (disk, network, HW)

Installation
------------

This utility can be installed with **pip**:

.. code:: shell

  pip install mcc

Configuration
-------------

The first time the utility is run, it creates its configuration directory, {HOME}/.cloud, and copies a sample config.ini file into it.
The sample config.ini lists the credential information you need to populate for each platform.
When editing the file, be careful not to change the section titles or item names.

Supported Platforms & Python Versions
-------------------------------------

Python 2.7, 3.3, 3.4, 3.5, 3.6

Platforms:

- Linux
- macOS (OS X)

Windows support is planned at the beta stage
