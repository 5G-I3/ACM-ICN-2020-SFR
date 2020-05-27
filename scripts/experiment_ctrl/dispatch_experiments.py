#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright (C) 2020 Freie Universität Berlin
#
# This file is subject to the terms and conditions of the GNU Lesser
# General Public License v2.1. See the file LICENSE in the top level
# directory for more details.

import argparse
import csv
import os
import logging
import multiprocessing
import pexpect
import re
import signal
import subprocess
import sys
import time
import yaml

from iotlabcli.profile import ProfileM3

from iotlab_controller.common import get_default_api, get_uri
from iotlab_controller.constants import IOTLAB_DOMAIN
from iotlab_controller.experiment.base import ExperimentError
from iotlab_controller.riot import RIOTFirmware
from iotlab_controller.experiment.tmux import TmuxExperiment
from iotlab_controller.nodes import BaseNodes


__author__ = "Martine S. Lenders"
__copyright__ = "Copyright 2020 Freie Universität Berlin"
__license__ = "LGPL v2.1"
__email__ = "m.lenders@fu-berlin.de"

SCRIPT_PATH = os.path.dirname(os.path.realpath(__file__))

APP_PATH = os.path.join(SCRIPT_PATH, "..", "..", "app")
DATA_PATH = os.environ.get("DATA_PATH",
                           os.path.join(SCRIPT_PATH, "..", "..", "results"))

FIRMWARE_NAME = "icn20-icnlowpan-sfr"

ARCHI_SHORT = "m3"
BOARD = "iotlab-m3"

MODES = set(("reass", "sfr"))

DEFAULT_IOTLAB_SITE = "grenoble"
DEFAULT_EXP_NAME_FORMAT = "icnlowpan_comp_cr_c{channel:02d}"
DEFAULT_MODE = "sfr"
DEFAULT_FIRMWARE_PATH = APP_PATH
DEFAULT_CHANNEL = 20
DEFAULT_DURATION = 6
DEFAULT_SFR_PARAMS = {
    "win": 1,       # window size
    "ifg": 100,     # inter-frame gap
    "arq": 150,     # ARQ timeout
    "frag": 4,      # fragment retries
    "dg": 0,        # datagram retries
}
DEFAULT_DELAY = 1000
DEFAULT_COUNT = 300
logger = logging.getLogger("dispatch")


def _cmake_version():
    try:
        output = subprocess.check_output(("cmake", "--version"))
    except subprocess.CalledProcessError:
        return 0, 0
    m = re.search(r"cmake version (\d+)\.(\d+)", output.decode())
    if m is None:
        return 0, 0
    return int(m.group(1)), int(m.group(2))


def run_experiment(exp, mode, consumer, producers, forwarders,
                   sfr_params=None, sniff=False, runs=None, vrep=True,
                   prefix=None, data_len=None, descs=None, inject_yaml=None):
    if runs is None:
        runs = []
    if sfr_params is None:
        sfr_params = DEFAULT_SFR_PARAMS
    if descs is None:
        descs = ExperimentDescriptions()
    last_mode = mode
    last_vrep = vrep
    consumer = exp.nodes[get_uri(exp.nodes.site, consumer)]
    producers = [exp.nodes[get_uri(exp.nodes.site, p)] for p in producers]
    forwarders = [exp.nodes[get_uri(exp.nodes.site, f)] for f in forwarders]

    def update_runs():
        additional_runs = load_additional_runs(inject_yaml)
        if additional_runs:
            # update runs
            runs = additional_runs + runs
            # and also update experiment description
            descs[exp.exp_id] = additional_runs + descs[exp.exp_id]
            descs.update_file()
            return True
        return False

    update_runs()
    if not runs:
        logger.warning("No runs in experiment {}".format(exp.exp_id))
        return
    if ("SSH_AUTH_SOCK" in os.environ) and ("SSH_AGENT_PID" in os.environ):
        exp.cmd("export SSH_AUTH_SOCK='{}'"
                .format(os.environ["SSH_AUTH_SOCK"]))
        exp.cmd("export SSH_AGENT_PID='{}'"
                .format(os.environ["SSH_AGENT_PID"]))
    while len(runs):
        for run in list(runs):
            # TODO reschedule experiment when not enough time for run
            if update_runs():
                # restart loop with runs
                break
            run_mode = run.get("mode", mode)
            if run_mode == "sfr":
                run_mode += "-win{win:d}ifg{ifg:d}arq{arq}r{frag}dg{dg}{vrep}" \
                    .format(vrep="-vrep" if run.get("vrep", vrep) else "",
                            **run.get("sfr_params", sfr_params))
            delay = run.get("delay", DEFAULT_DELAY)
            count = run.get("count", DEFAULT_COUNT)
            prefix = run.get("prefix", prefix)
            data_len = run.get("data_len", data_len)
            assert(prefix is not None and data_len is not None)
            run_name = os.path.join(
                DATA_PATH,
                "{exp.name}_m{mode}-{count}x{delay}ms{data_len}B_{timestamp}"
                .format(exp=exp, timestamp=int(time.time()), count=count,
                        delay=delay, mode=run_mode, data_len=data_len)
            )
            if (last_vrep != run.get("vrep", vrep)) or \
               (last_mode != run.get("mode", mode)) or \
               (run.get("reflash")):
                # reflash nodes
                assert len(exp.firmwares) == 1
                for firmware in exp.firmwares:
                    firmware.env["MODE"] = run["mode"]
                    firmware.env["VREP"] = "1" if run.get("vrep", 1) else "0"
                    if _cmake_version() <= (3, 13):
                        threads = multiprocessing.cpu_count()
                    else:
                        # see https://github.com/RIOT-OS/RIOT/issues/14288
                        threads = 1
                    firmware.build(threads=threads)
                logger.info("Reflash {}".format(exp.firmwares[0]))
                exp.nodes.flash(exp.exp_id, exp.firmwares[0])
                last_mode = run["mode"]
                descs[exp.exp_id]["mode"] = last_mode
            else:
                exp.nodes.reset(exp.exp_id)
            default_run_duration = (((delay / 1000) * count) / 60) + 0.5
            run_duration = run.get("duration", default_run_duration) * 60
            if sniff:
                sniffer = _start_sniffer(exp, "{}.pcap".format(run_name))
            else:
                sniffer = None
            _load_l2addr_ifaces(exp)
            exp.start_serial_aggregator(exp.nodes.site,
                                        logname="{}.log".format(run_name))
            exp.cmd("version")
            for producer in producers:
                logger.info("Configuring producer {}".format(producer))
                exp.cmd("{};produce {}/{} {}".format(
                    producer.uri.split(".")[0], prefix, producer.l2addr[:5],
                    data_len
                ))
            logger.info("Constructing routes")
            exp.cmd("{};route {} {}".format(
                consumer.uri.split(".")[0], prefix, forwarders[0].l2addr
            ))
            for i, forwarder in enumerate(forwarders[:-1]):
                exp.cmd("{};route {} {}".format(
                    forwarder.uri.split(".")[0], prefix,
                    forwarders[i + 1].l2addr
                ))
            for producer in producers:
                exp.cmd("{};route {}/{} {}".format(
                    forwarders[-1].uri.split(".")[0], prefix,
                    producer.l2addr[:5], producer.l2addr
                ))
            logger.info("Starting experiment")
            exp.cmd("{};consume {} {} {}".format(
                consumer.uri.split(".")[0], delay, count,
                ' '.join([
                    "{}/{}".format(prefix, producer.l2addr[:5])
                    for producer in producers
                ])
            ))
            logger.info(
                "Waiting for {}s for experiment {} (until {}) to finish"
                .format(run_duration, run_name,
                        time.asctime(time.localtime(time.time() +
                                                    run_duration))))

            time.sleep(run_duration + 60)
            exp.hit_enter()
            exp.cmd("pktbuf")
            time.sleep(1)
            exp.cmd("6lo_frag")
            time.sleep(1)
            exp.cmd("ccnl_cs")
            time.sleep(1)
            exp.stop_serial_aggregator()
            _stop_sniffer(sniffer)
            descs[exp.exp_id].get("runs").remove(run)
            descs.update_file()


def _start_sniffer(exp, pcap_file):
    sniffer = exp.tmux_session.session.find_where({"window_name": "sniffer"})
    if sniffer is None:
        sniffer = exp.tmux_session.session.new_window("sniffer", DATA_PATH,
                                                      attach=False)
    sniffer = sniffer.select_pane(0)
    if ("SSH_AUTH_SOCK" in os.environ) and ("SSH_AGENT_PID" in os.environ):
        sniffer.send_keys("export SSH_AUTH_SOCK='{}'"
                          .format(os.environ["SSH_AUTH_SOCK"]))
        sniffer.send_keys("export SSH_AGENT_PID='{}'"
                          .format(os.environ["SSH_AGENT_PID"]))
    # kill currently running sniffer
    sniffer.send_keys("C-c", suppress_history=False)
    sniffer.send_keys("ssh {}@{}.{} sniffer_aggregator -o - -i {} > {}"
                      .format(exp.username, exp.nodes.site,
                              IOTLAB_DOMAIN, exp.exp_id, pcap_file),
                      enter=True, suppress_history=False)
    return sniffer


def _stop_sniffer(sniffer=None):
    if sniffer is not None:
        sniffer.cmd("send-keys", "C-c")


def _node_l2addr_file(exp):
    nodes = [node.uri.split(".")[0].split("-")[1] for node in exp.nodes]
    nodes.sort(key=int)
    return os.path.join(DATA_PATH, "l2addrs_{}.csv".format("+".join(nodes)))


def _load_l2addr_ifaces_file(exp, l2addr_filename):
    loaded = 0
    if os.path.exists(l2addr_filename):
        with open(l2addr_filename) as l2addr_file:
            l2addr_csv = csv.DictReader(l2addr_file)
            for row in l2addr_csv:
                node = None
                try:
                    node = exp.nodes[
                        "{name}.{site}.{domain}"
                        .format(domain=IOTLAB_DOMAIN, site=exp.nodes.site,
                                **row)
                    ]
                    node.iface = int(row["iface"])
                    # trigger AttributeError intentionally
                    node.l2addr = row["l2addr"].upper()
                    loaded += 1
                except (KeyError, ValueError, AttributeError):
                    break
    return loaded


def _load_l2addr_ifaces(exp):
    logger.info("Loading interfaces and L2 addresses of nodes")
    l2addr_filename = _node_l2addr_file(exp)
    if _load_l2addr_ifaces_file(exp, l2addr_filename) == len(exp.nodes):
        return
    child = pexpect.spawnu(
            "ssh {}@{}.{} serial_aggregator -i {}".format(
                    exp.username, exp.nodes.site, IOTLAB_DOMAIN, exp.exp_id
                ),
            timeout=3
        )
    child.expect("Aggregator started", timeout=10)
    child.logfile = sys.stdout
    with open(l2addr_filename, "w") as l2addr_file:
        l2addr_csv = csv.DictWriter(l2addr_file,
                                    ["name", "iface", "l2addr"])
        l2addr_csv.writeheader()
        for node in exp.nodes:
            nodename = node.uri.split(".")[0]
            child.sendline("{};ifconfig".format(nodename))
            res = child.expect([r"{};Iface\s+(\d+)".format(nodename),
                                r"Node not managed: m3-(\d+)"])
            if res > 0:
                raise ExperimentError("Network contains node not within "
                                      "the experiment: m3-{}"
                                      .format(child.match.group(1)))
            node.iface = int(child.match.group(1))
            child.expect(r"{};\s+Long HWaddr: ([0-9A-F:]+)\s"
                         .format(nodename))
            node.l2addr = child.match.group(1)
            l2addr_csv.writerow({
                "name": nodename,
                "iface": node.iface,
                "l2addr": node.l2addr,
            })
    while not child.terminated:
        try:
            os.killpg(os.getpgid(child.pid), signal.SIGKILL)
        except ProcessLookupError:
            break
        else:
            child.close()
            time.sleep(5)


def load_additional_runs(inject_yaml=None):
    runs = []
    if inject_yaml is not None and os.path.exists(inject_yaml):
        with open(inject_yaml) as yamlf:
            runs.extend(yaml.load(yamlf, Loader=yaml.FullLoader))
        os.remove(inject_yaml)
    return runs


class ExperimentDescriptions(dict):
    class Error(Exception):
        pass

    def __init__(self, filename=None, iotlab_api=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.filename = filename
        if iotlab_api is None:
            self.iotlab_api = get_default_api()
        else:
            self.iotlab_api = iotlab_api

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        self.update_file()
        return value

    def __delitem__(self, key):
        super().__delitem__(key)
        self.update_file()

    def update_file(self):
        if len(self) and self.filename:
            with open(self.filename, "w") as yamlf:
                yamlf.write(yaml.dump(dict(self.items())))
        elif self.filename:
            os.rename(self.filename,
                      self.filename + "." + str(int(time.time())) + ".bkp")

    def _schedule_unscheduled(self, unscheduled):
        exps = []
        if not isinstance(unscheduled, list):
            raise self.Error(
                "'unscheduled' value in {} must be list of "
                "experiment description objects".format(self.filename)
            )
        # make unscheduled mutable during iteration
        for desc in list(unscheduled):
            exp = sched_experiment(descs=self, iotlab_api=self.iotlab_api,
                                   **desc)
            self["unscheduled"].remove(desc)
            self.update_file()
            exps.append(exp)
        del self["unscheduled"]
        return exps

    def schedule(self):
        exps = []
        # make self mutable during iteration
        for exp_id, desc in list(self.items()):
            if exp_id == "unscheduled":
                exps.extend(self._schedule_unscheduled(desc))
                continue
            # else requeue existing experiments
            try:
                if not isinstance(exp_id, int):
                    logger.info("Skipping unrecognized entry '{}', should be "
                                "IoTLAB experiment id".format(exp_id))
                logger.info("Trying to requeue experiment {name} ({exp_id})"
                            .format(name=desc.get("name"), exp_id=exp_id))
                exp = TmuxExperiment(exp_id=exp_id, **desc_to_exp_params(
                    desc, self.iotlab_api, self
                ))
                exps.append(exp)
            except ExperimentError as e:
                logger.error("Unable to requeue {}: {}".format(exp_id, e))
                del self[exp_id]
        return exps


def desc_to_exp_params(desc, iotlab_api=None, descs=None):
    if desc.get("name") is None:
        desc["name"] = DEFAULT_EXP_NAME_FORMAT.format(**desc)
    params = {
        "name": desc["name"],
        "target": run_experiment,
        "consumer": desc["consumer"],
        "producers": desc["producers"],
        "forwarders": desc["forwarders"],
        "sfr_params": desc["sfr_params"],
        "mode": desc["mode"],
        "vrep": desc.get("vrep", True),
        "runs": desc["runs"],
        "sniff": desc["sniff"],
        "prefix": desc["prefix"],
        "data_len": desc["data_len"],
    }
    assert(isinstance(desc["forwarders"], list))
    if iotlab_api is None:
        params["api"] = get_default_api()
    else:
        params["api"] = iotlab_api

    if descs is not None:
        params["descs"] = descs

    env = {"MODE": desc["mode"], "VREP": "1" if desc.get("vrep", 1) else "0",
           "DEFAULT_CHANNEL": str(desc["channel"])}
    if desc["mode"] == "sfr":
        env_mapping = {
            "WIN_SIZE": "win",
            "INTER_FRAME_GAP": "ifg",
            "RETRY_TIMEOUT": "arq",
            "RETRIES": "frag",
            "DATAGRAM_RETRIES": "dg",
        }

        for key, value in env_mapping.items():
            env[key] = str(int(
                desc.get("sfr_params", DEFAULT_SFR_PARAMS).get(
                    value, DEFAULT_SFR_PARAMS[value]
                )
            ))
    params["firmwares"] = [RIOTFirmware(desc["firmware_path"],
                                        desc.get("board", BOARD),
                                        FIRMWARE_NAME, env=env)]
    if desc["sniff"]:
        params["profiles"] = [_get_sniffer_profile(iotlab_api,
                                                   desc["channel"])]
        logger.info("Select sniffing profile {}".format(
            params["profiles"][0]
        ))
    params["nodes"] = BaseNodes([
        get_uri(desc["iotlab_site"], node) for node in
        [desc["consumer"]] + desc["producers"] + desc["forwarders"]
    ])
    params["nodes"].site = desc["iotlab_site"]
    return params


def sched_experiment(consumer, forwarders, producers,
                     iotlab_site=DEFAULT_IOTLAB_SITE,
                     name=None, duration=DEFAULT_DURATION,
                     firmware_path=DEFAULT_FIRMWARE_PATH, vrep=True,
                     mode=DEFAULT_MODE, sfr_params=DEFAULT_SFR_PARAMS,
                     channel=DEFAULT_CHANNEL, prefix=None, data_len=None,
                     sniff=False, runs=None, descs=None, iotlab_api=None):
    desc = locals()
    del desc["iotlab_api"]
    del desc["descs"]
    params = desc_to_exp_params(desc, iotlab_api, descs)
    logger.info("Building firmwares")
    for firmware in params["firmwares"]:
        if _cmake_version() <= (3, 13):
            threads = multiprocessing.cpu_count()
        else:
            # see https://github.com/RIOT-OS/RIOT/issues/14288
            threads = 1
        firmware.build(threads=threads)
    # create and prepare IoT-LAB experiment
    exp = TmuxExperiment(**params)
    logger.info("Scheduling experiment {exp.name} with duration {duration}"
                .format(duration=duration, exp=exp))
    exp.schedule(duration)
    logger.info("Scheduled {exp.exp_id}".format(exp=exp))
    descs[exp.exp_id] = desc
    return exp


def load_descs(args, iotlab_api=None):
    try:
        with open(args.descs_yaml) as yamlf:
            descs = ExperimentDescriptions(
                args.descs_yaml, iotlab_api,
                yaml.load(yamlf, Loader=yaml.FullLoader)
            )
    except FileNotFoundError:
        descs = ExperimentDescriptions(args.descs_yaml, iotlab_api)
    exps = descs.schedule()
    exps.sort(key=lambda exp: exp.exp_id)
    return descs, exps


def _get_sniffer_profile(api, channel=DEFAULT_CHANNEL):
    for profile in api.get_profiles(ARCHI_SHORT):
        if (profile.get("radio") is not None) and \
           (profile["radio"].get("mode") == "sniffer") and \
           (channel in profile["radio"].get("channels")):
            return profile["profilename"]
    profile = ProfileM3(profilename="sniffer{}".format(channel), power="dc")
    profile.set_radio(channels=[channel], mode="sniffer")
    api.add_profile(profile.profilename, profile)
    return profile.profilename


def _parse_tmux_target(tmux_target, name):
    res = {}
    if tmux_target is not None:
        session_window = tmux_target.split(":")
        res["session_name"] = session_window[0]
        if len(session_window) > 1:
            window_pane = (":".join(session_window[1:])).split(".")
            res["window_name"] = window_pane[0]
            if len(window_pane) > 1:
                res["pane_id"] = ".".join(window_pane[1:])
    else:
        res["session_name"] = name
    return res


def start_experiments(exps, descs, args):
    if not exps:
        logger.warning("No experiments to run")
        descs.clear()
    for exp in exps:
        logger.info("Waiting for experiment {} to start".format(exp.exp_id))
        try:
            exp.wait()
        except (ExperimentError, RuntimeError) as e:
            logger.error("Could not wait for experiment: {}".format(e))
            del descs[exp.exp_id]
            return
        tmux_target = _parse_tmux_target(args.tmux_target, exp.name)
        logger.info("Starting TMUX session in {}".format(tmux_target))
        tmux_session = exp.initialize_tmux_session(**tmux_target)
        assert tmux_session
        exp.hit_ctrl_c()    # Kill potentially still running experiment
        exp.hit_ctrl_c()    # Kill potentially still running experiment
        time.sleep(.1)
        exp.run()
        del descs[exp.exp_id]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-t", "--tmux-target", default=None,
                        help="TMUX target for experiment control "
                             "(default: the IoT-LAB experiment name)")
    parser.add_argument("descs_yaml", nargs="?",
                        default=os.path.join(SCRIPT_PATH, "descs.yaml"))
    parser.add_argument("inject_yaml", nargs="?",
                        default=os.path.join(SCRIPT_PATH, "inject.yaml"))
    args = parser.parse_args()
    logger.setLevel(logging.INFO)
    api = get_default_api()
    descs, exps = load_descs(args, api)
    while (len(descs)):     # check if there are still experiments to run
        start_experiments(exps, descs, args)


if __name__ == "__main__":
    main()
