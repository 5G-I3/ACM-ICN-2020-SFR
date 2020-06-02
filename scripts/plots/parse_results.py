#!/usr/bin/env python3
#
# Copyright (C) 2020 Freie Universität Berlin
#
# This file is subject to the terms and conditions of the GNU Lesser
# General Public License v2.1. See the file LICENSE in the top level
# directory for more details.

import csv
import re
import os
import sys

__author__ = "Martine S. Lenders"
__copyright__ = "Copyright 2020 Freie Universität Berlin"
__license__ = "LGPL v2.1"
__email__ = "m.lenders@fu-berlin.de"

SCRIPT_PATH = os.path.dirname(os.path.realpath(__file__))
DATA_PATH = os.environ.get("DATA_PATH",
                           os.path.join(SCRIPT_PATH, "..", "..", "results"))
NAME_PATTERN = r"icnlowpan_comp_cr_c\d+_" \
               r"m{mode}-{count}x{delay}ms{data_len}B_(?P<timestamp>\d+)"
LOG_NAME_PATTERN = r"{}\.log$".format(NAME_PATTERN.format(
    mode=r"(?P<mode>(reass|sfr-.*))",
    count=r"(?P<count>\d+)",
    delay=r"(?P<delay>\d+)",
    data_len=r"(?P<data_len>\d+)",
))
STATS_LISTINGS = {
    "ch": "cs_hits",
    "pt": "cnt_trans",
    "rt": "int_retrans",
}
ROLES_COMPILES = {
    "consumer": re.compile(r"consume \d+ \d+( \S+)+"),
    "forwarder": re.compile("route \S+ [:0-9A-fa-f]+"),
    "producer": re.compile("produce \S+ \d+"),
}
STATS_COMPILES = {
    "pktbuf_size": re.compile(
        r"packet buffer: first byte: .*, last byte: .* "
        r"\(size: (?P<pktbuf_size>\d+)\)"
    ),
    "pktbuf_used": re.compile(r"  position of last byte used: "
                              r"(?P<pktbuf_used>\d+)$"),
    "fbuf_full": re.compile(r"frag full: (?P<fbuf_full>\d+)$"),
    "rbuf_full": re.compile(r"rbuf full: (?P<rbuf_full>\d+)$"),
    "vrb_full": re.compile(r"VRB full: (?P<vrb_full>\d+)$"),
    "frags_complete": re.compile(r"frags complete: (?P<frags_complete>\d+)$"),
    "dgs_complete": re.compile(r"dgs complete: (?P<dgs_complete>\d+)$"),
    "dgs_retrans": re.compile(r"DG resends: (?P<dgs_retrans>\d+)$"),
    "frags_sent": re.compile(r"frags sent: usual: (?P<frags_orig>\d+), "
                             r"aborts: (?P<frags_abort>\d+), "
                             r"forwarded: (?P<frags_fwd>\d+)$"),
    "frags_resent": re.compile(r"frag resends: NACK: (?P<frags_re_nack>\d+), "
                               r"timeout: (?P<frags_re_tout>\d+)$"),
    "sfr_ack": re.compile(r"ACKs: full: (?P<acks_full>\d+), "
                          r"partly: (?P<acks_part>\d+), "
                          r"aborts: (?P<acks_abort>\d+), "
                          r"forwarded: (?P<acks_fwd>\d+)$"),
}
STATS_CASTS = {
    "pktbuf_size": int,
    "pktbuf_used": int,
    "fbuf_full": int,
    "rbuf_full": int,
    "vrb_full": int,
    "frags_complete": int,
    "dgs_complete": int,
    "dgs_retrans": int,
    "frags_orig": int,
    "frags_abort": int,
    "frags_fwd": int,
    "frags_re_nack": int,
    "frags_re_tout": int,
    "acks_full": int,
    "acks_part": int,
    "acks_abort": int,
    "acks_fwd": int,
}
LOG_BLACKLIST = {
}

LOG_FIELDS = [
    "timestamp", "node", "msg", "xtimer", "name"
]
RESULT_FIELDS = {
    "times": ["exp_time", "nodes", "mode", "count", "delay", "data_len",
              "name", "send_time", "recv_time"],
    "stats": ["exp_time", "nodes", "mode", "count", "delay", "data_len",
              "node", "role", "pktbuf_used", "pktbuf_size",
              "cs_hits", "cnt_trans", "int_retrans", "dgs_retrans",
              "frags_orig", "frags_abort", "frags_fwd",
              "frags_re_nack", "frags_re_tout",
              "fbuf_full", "rbuf_full", "vrb_full",
              "frags_complete", "dgs_complete",
              "acks_full", "acks_part", "acks_abort", "acks_fwd"],
}


def update_stats(res, timestamp, nodes, mode, count, delay, data_len, node,
                 stats, node_roles, casts=None):
    if casts:
        for stat, cast in casts.items():
            if stat in stats:
                stats[stat] = cast(stats[stat])
    if (timestamp, node) not in res:
        res[timestamp, node] = {
            "exp_time": timestamp,
            "nodes": nodes,
            "mode": mode,
            "count": count,
            "delay": delay,
            "data_len": data_len,
            "node": node,
            "role": node_roles.get(node),
        }
    res[timestamp, node].update(stats)


def inc_stat(stats, timestamp, nodes, mode, count, delay, data_len, node,
             node_roles, stat):
    if (timestamp, node) in stats and stat in stats[timestamp, node]:
        stats[timestamp, node][stat] += 1
    elif (timestamp, node) in stats:
        stats[timestamp, node][stat] = 1
    else:
        stats[timestamp, node] = {
            "exp_time": timestamp,
            "nodes": nodes,
            "mode": mode,
            "count": count,
            "delay": delay,
            "data_len": data_len,
            "node": node,
            "role": node_roles.get(node),
            stat: 1,
        }


def log_to_csvs(logname, nodes, mode, count, delay, data_len, timestamp, csvs,
                data_path=DATA_PATH):
    times = {}
    stats = {}
    with open(logname, "r") as logfile:
        logcsv = csv.DictReader(logfile, fieldnames=LOG_FIELDS, delimiter=";")
        node_roles = {}
        role_commands = set()
        for row in logcsv:
            msg = row["msg"]
            node = row["node"]
            if msg in STATS_LISTINGS:
                inc_stat(stats, timestamp, nodes, mode, count, delay, data_len,
                         node, node_roles, STATS_LISTINGS[msg])
            elif msg in {"qt", "pr"}:
                if msg == "qt":
                    key = "send_time"
                else:
                    key = "recv_time"
                name = row["name"]
                msg_timestamp = row["xtimer"]
                if name in times:
                    # only log first occurrence
                    if key not in times[name]:
                        times[name][key] = msg_timestamp
                else:
                    times[name] = {
                        "exp_time": timestamp,
                        "nodes": nodes,
                        "mode": mode,
                        "count": count,
                        "delay": delay,
                        "data_len": data_len,
                        "name": name,
                        key: msg_timestamp
                    }
            else:
                match = None
                for role in ROLES_COMPILES:
                    match = ROLES_COMPILES[role].match(msg)
                    if match and \
                       match.group(0) not in role_commands:     # deduplicate
                        node_roles[node] = role
                        role_commands.add(match.group(0))
                        break
                if match:
                    continue
                for stat in STATS_COMPILES:
                    match = STATS_COMPILES[stat].match(msg)
                    if match:
                        update_stats(stats, timestamp, nodes, mode, count,
                                     delay, data_len, node, match.groupdict(),
                                     node_roles, casts=STATS_CASTS)
                        break
                if match:
                    continue
    csvs[mode, count, delay, nodes]["times"]["csv"].writerows(times.values())
    csvs[mode, count, delay, nodes]["stats"]["csv"].writerows(stats.values())


def match_to_dict(match):
    res = match.groupdict()
    res["data_len"] = int(res["data_len"])
    res["count"] = int(res["count"])
    res["delay"] = int(res["delay"])
    return res


def count_nodes(logname):
    with open(logname, "r") as logfile:
        nodes = set()
        logcsv = csv.DictReader(logfile, fieldnames=LOG_FIELDS, delimiter=";")
        for row in logcsv:
            nodes.add(row["node"])
        return len(nodes)


def logs_to_csvs(data_path=DATA_PATH, blacklisted=None):
    if blacklisted is None:
        blacklisted = set(LOG_BLACKLIST)
    else:
        blacklisted = set(blacklisted) | set(LOG_BLACKLIST)
    comp = re.compile(LOG_NAME_PATTERN)
    csvs = {}
    try:
        for logname in os.listdir(data_path):
            match = comp.search(logname)
            if match is not None and logname not in blacklisted:
                logname = os.path.join(data_path, logname)
                params = match_to_dict(match)
                params["nodes"] = count_nodes(logname)
                key = tuple(params[p] for p in ["mode", "count", "delay",
                                                "nodes"])
                if key not in csvs:
                    csvs[key] = {}
                    for log in ["times", "stats"]:
                        csvs[key][log] = {
                            "file": open(os.path.join(
                                data_path,
                                "{mode}-{count}x{delay}ms{data_len}B-"
                                "{nodes}-{log}.csv"
                                .format(log=log, **params)
                            ), "w"),
                        }
                        csvs[key][log]["csv"] = csv.DictWriter(
                            csvs[key][log]["file"],
                            fieldnames=RESULT_FIELDS[log],
                            delimiter=","
                        )
                        csvs[key][log]["csv"].writeheader()
                log_to_csvs(logname, data_path=data_path, csvs=csvs, **params)
    finally:
        for key in csvs:
            for log in csvs[key]:
                csvs[key][log]["file"].close()


if __name__ == "__main__":
    logs_to_csvs(blacklisted=set(sys.argv))
