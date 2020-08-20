Scripts to conduct experiment
=============================
Overview
--------
The scripts in this directory serve the experiment conduction.

[`dispatch_experiments.py`](./dispatch_experiments.py) runs all experiments as
described in `descs.yaml`.

[`setup_exp.sh`](./setup_exp.sh) ensures the environment for
`dispatch_experiments.py` is run in the background in one TMUX session (called
`icnlowpan-sfr`) with insurance that an SSH authentication agent was started and
configured to communicate with the IoT-LAB frontend server.

Requirements
------------
The scripts assume they are run with Python 3.

The following python packages are required (version numbers indicate tested versions):

- `libtmux` v0.8.0
- `pexpect` v4.8.0
- `iotlabcli` v2.6.0
- [`iotlab_controller`](https://github.com/miri64/iotlab_controller) v0.3.0
- `pyyaml` v5.3

The required packages are listed in [`requirements.txt`](./requirements.txt) and
can be installed using

```sh
pip3 install -r requirements.txt
```

You will also require a version of the `ssh` command (e.g. `openssh-client`) to
interact with the IoT-LAB nodes.

`tmux` is required to multiplex the terminal in the background.

You must also configure your IoT-LAB credentials using `iotlab-auth` which is
provided by the `iotlabcli` python package (which is automatically installed
with `iotlab_controller`). See

```
iotlab-auth -h
```

for further instructions.

Usage
-----
### `dispatch_experiments.py`
This script conducts all experiments described in `descs.yaml`.

```
./dispatch_experiments.py
```

For each run, `mode`, `vrep`, `prefix`, `data_len`, `count`, and `delay` can be
set to configure the [application](../../app). `reflash` enforces the rebuild
and reflashing of the application to all nodes. Have a look at
`descs.example.yaml` to see how a set of experiments can be described.

Experiments can also be described for an already running IoT-LAB experiment by
assigning an object to the ID of that IoT-LAB experiment

```yaml
226556:
  channel: 20
  iotlab_site: grenoble
  consumer: m3-273
  forwarders:
  - m3-281
  - m3-289
  producers:
  - m3-2
  - m3-72
  # ...
```

Just make sure, the nodes listed are actually booked for the provided IoT-LAB
experiment at the given site.

The resulting logs of a run will be stored in `DATA_PATH` under the name
`icnlowpan_comp_cr_c<channel>_m<mode-incl-SFR-params>-<count>x<delay>ms<data_len>B_<timestamp>.log`

If you want to sniff the IEEE 802.15.4 traffic during the experiment, add
`sniffer: true` to the experiment's description. The resulting PCAP file will be
stored in `DATA_PATH` under the name
`icnlowpan_comp_cr_c<channel>_m<mode-incl-SFR-params>-<count>x<delay>ms<data_len>B_<timestamp>.pcap`

#### Environment variables
- `DATA_PATH`: (default: `./../../results`) Path to store the resulting logs and
  PCAPs in

### `setup_exp.sh`
Helper script to automatically put `dispatch_experiments.py` (and its generated
TMUX windows) in a TMUX session with proper SSH authentication agent
configuration.

As such, when starting the script, it might ask you for your SSH key passphrase.
It is used to store your key in the SSH authentication agent, so the called
scripts can communicate with the IoT-LAB SSH frontend.
