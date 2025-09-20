# Installation

Install dependencies:

```bash
pip install -r host/requirements.txt
pip install -r host/requirements-dev.txt
```

Build executable:

```bash
pyinstaller -F --python-option u --distpath rpcooler/bin host/rpcooler.py
```
Create *deb* package:

```bash
dpkg-deb --build --root-owner-group rpcooler
```
Install *deb* package:

```bash
dpkg -i rpcooler.deb
```

Enable at startup:

```bash
systemctl enable rpcooler.service
```

# Configuration

Config file location is `/etc/rpcooler.conf`

Config template:

```
SERIAL_DEVICE_PATH=
CPU_TEMP_PATH=
COOLER_ON_TEMP=
COOLER_ON_FRAMES=
INTERVAL_MS=
RAID_DISKS=
STORAGES=
```
