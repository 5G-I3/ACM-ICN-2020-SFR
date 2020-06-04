#!/usr/bin/env python3
#
# Copyright (C) 2020 Freie Universität Berlin
#
# This file is subject to the terms and conditions of the GNU Lesser
# General Public License v2.1. See the file LICENSE in the top level
# directory for more details.

import argparse
import functools
import os
import sys

import numpy as np
import matplotlib.pyplot as plt                                 # noqa: E402

from parse_results import DATA_PATH                             # noqa: E402

from plot_cdf import HUMAN_READABLE_MODE, collect_dataframes    # noqa: E402

FIGSIZE_DEFAULT = (2.4587625, 1.73851894)
NODE_ROLES = {
    5: {
        "m3-273": "C",
        "m3-281": "F1",
        "m3-289": "F2",
        "m3-2": "P1",
        "m3-72": "P2",
    },
    8: {
        "m3-233": "C",
        "m3-241": "F1",
        "m3-249": "F2",
        "m3-257": "F3",
        "m3-265": "F4",
        "m3-273": "F5",
        "m3-281": "F6",
        "m3-289": "P",
    }
}
NODES_ORDER = {
    5: [
        "C",
        "F1",
        "F2",
        "P1",
        "P2"
    ],
    8: [
        "C",
        "F1",
        "F2",
        "F3",
        "F4",
        "F5",
        "F6",
        "P"
    ]
}
STYLE = {
    "reass": {None: "white"},
    "sfr": {None: "gray", "-vrep": "lightgray"},
}
BAR_WIDTH = {
    False: .90 / 3, # sfr_only == False
    True: .90 / 2,  # sfr_only == True
}
MODE_OFFSET = {
    False: {        # sfr_only == False
        "reass": {None: -BAR_WIDTH[False]},
        "sfr": {None: 0, "-vrep": BAR_WIDTH[False]},

    },
    True: {         # sfr_only == True
        "sfr": {None: -BAR_WIDTH[True] / 2,
                "-vrep": BAR_WIDTH[True] / 2},

    },
}


def cnt_trans_series(df, count, nodes):
    df["cnt_trans"] = df["cnt_trans"] / count
    return df.groupby("node")["cnt_trans"]


def frag_retrans_series(df, count, nodes):
    df["frag_retrans"] = (df["frags_re_nack"] + df["frags_re_tout"]) / count
    return df.groupby("node")["frag_retrans"]


def int_retrans_series(df, count, nodes):
    df["int_retrans"] = df["int_retrans"] / \
        (count * len([producer for producer in NODES_ORDER[nodes]
                      if producer[0] == "P"]))
    return df.groupby("node")["int_retrans"]


def pktbuf_series(df, count, nodes):
    df["pktbuf_usage"] = (df["pktbuf_used"] * 100) / df["pktbuf_size"]
    return df.groupby("node")["pktbuf_usage"]


def frags_fwd_series(df, count, nodes):
    df["frags_fwd"] = df["frags_fwd"] / \
        (count * len([producer for producer in NODES_ORDER[nodes]
                      if producer[0] == "P"]))
    return df.groupby("node")["frags_fwd"]


def hide_consumers(key, nodes):
    res = {
        5: {
            "xlim": (0.5, nodes - .5),
            "xticks": np.arange(1, nodes),
            "xticklabels": NODES_ORDER[nodes][1:],
        },
    }
    res[8] = res[5]
    return res[nodes][key]


def hide_producers(key, nodes):
    res = {
        5: {
            "xlim": (-0.5, nodes - 2.5),
            "xticks": np.arange(0, nodes - 2),
            "xticklabels": NODES_ORDER[nodes][:-2],
        },
        8: {
            "xlim": (-0.5, nodes - 1.5),
            "xticks": np.arange(0, nodes - 1),
            "xticklabels": NODES_ORDER[nodes][: -1],
        },
    }
    return res[nodes][key]


def all_nodes(key, nodes):
    res = {
        5: {
            "xlim": (-0.5, nodes - .5),
            "xticks": np.arange(0, nodes),
            "xticklabels": NODES_ORDER[nodes],
        },
    }
    res[8] = res[5]
    return res[nodes][key]


def only_forwarders(key, nodes):
    res = {
        5: {
            "xlim": (0.5, nodes - 2.5),
            "xticks": np.arange(1, nodes - 2),
            "xticklabels": NODES_ORDER[nodes][1:-2],
        },
        8: {
            "xlim": (0.5, nodes - 1.5),
            "xticks": np.arange(1, nodes - 1),
            "xticklabels": NODES_ORDER[nodes][1:-1],
        },
    }
    return res[nodes][key]


STAT_PLOTS = {
    "cnt_trans": {
        "series": cnt_trans_series,
        "ylabel": r"Content trans. [avg. \# / content]",
        "xlim": functools.partial(hide_consumers, "xlim"),
        "xticks": functools.partial(hide_consumers, "xticks"),
        "xticklabels": functools.partial(hide_consumers, "xticklabels"),
        "ymax": 1.5,
        "ysteps": 0.5,
        "legend": {"loc": "upper left"},
    },
    "cs_hits": {
        "series": lambda df, *args: df.groupby("node")["cs_hits"],
        "column": lambda df, *args: df["cs_hits"],
        "ylabel": r"CS hit events [\#]",
        "xlim": functools.partial(hide_consumers, "xlim"),
        "xticks": functools.partial(hide_consumers, "xticks"),
        "xticklabels": functools.partial(hide_consumers, "xticklabels"),
        "ylabel_format": {"axis": "y", "style": "sci", "scilimits": (3, 3)},
        "ymax": 2000,
        # "ysteps": 200,
        "yscale": "symlog",
        "legend": {"loc": "upper left", "fontsize": 8},
    },
    "fbuf_full": {
        "series": lambda df, *args: df.groupby("node")["fbuf_full"],
        "ylabel": r"Fragment buffer events [\#]",
        "xlim": functools.partial(all_nodes, "xlim"),
        "xticks": functools.partial(all_nodes, "xticks"),
        "xticklabels": functools.partial(all_nodes, "xticklabels"),
        "ymax": 1,
        "legend": {"loc": "upper left"},
    },
    "frag_fwd": {
        "series": frags_fwd_series,
        "ylabel": r"Fragments fwd. [avg. \# / content]",
        "xlim": functools.partial(only_forwarders, "xlim"),
        "xticks": functools.partial(only_forwarders, "xticks"),
        "xticklabels": functools.partial(only_forwarders, "xticklabels"),
        "sfr_only": True,
        "legend": {"loc": "upper center", "ncol": 2,
                   "bbox_to_anchor": (0.5, 1.2)},
    },
    "frag_retrans": {
        "series": frag_retrans_series,
        "ylabel": r"Fragment retrans. [avg. \# / content]",
        "xlim": functools.partial(hide_consumers, "xlim"),
        "xticks": functools.partial(hide_consumers, "xticks"),
        "xticklabels": functools.partial(hide_consumers, "xticklabels"),
        "ymax": 12,
        "ysteps": 4,
        "sfr_only": True,
        "legend": {"loc": "upper left"},
    },
    "int_retrans": {
        "series": int_retrans_series,
        "ylabel": "Interest retrans.\n[avg. \\# / content]",
        "xlim": functools.partial(hide_producers, "xlim"),
        "xticks": functools.partial(hide_producers, "xticks"),
        "xticklabels": functools.partial(hide_producers, "xticklabels"),
        "ymax": 3.1,
        "ysteps": 1,
    },
    "pktbuf": {
        "series": pktbuf_series,
        "ylabel": r"Packet buffer usage [\%]",
        "xlim": functools.partial(all_nodes, "xlim"),
        "xticks": functools.partial(all_nodes, "xticks"),
        "xticklabels": functools.partial(all_nodes, "xticklabels"),
        "ymax": 40,
        "ysteps": 10,
        "legend": {"loc": "upper center", "ncol": 3},
        "figsize": (4.917525, 1.3021813),
    },
    "vrb_full": {
        "series": lambda df, *args: df.groupby("node")["vrb_full"],
        "column": lambda df, *args: df["vrb_full"],
        "ylabel": r"VRB full events [\#]",
        "xlim": functools.partial(only_forwarders, "xlim"),
        "xticks": functools.partial(only_forwarders, "xticks"),
        "xticklabels": functools.partial(only_forwarders, "xticklabels"),
        "ymax": 500,
        "ysteps": 100,
        "sfr_only": True,
        "legend": {"loc": "upper left"},
    },
    "rbuf_full": {
        "series": lambda df, *args: df.groupby("node")["rbuf_full"],
        "ylabel": r"RB full events [\#]",
        "xlim": functools.partial(hide_producers, "xlim"),
        "xticks": functools.partial(hide_producers, "xticks"),
        "xticklabels": functools.partial(hide_producers, "xticklabels"),
        "ylabel_format": {"axis": "y", "style": "sci", "scilimits": (3, 3)},
        "ymax": 10000,
        "ysteps": 2000,
        "legend": {"loc": "upper left", "fontsize": 8},
    },
}


def set_axes(axes, nodes, stat):
    axes.set_xlim(STAT_PLOTS[stat]["xlim"](nodes))
    axes.set_xticks(STAT_PLOTS[stat]["xticks"](nodes))
    axes.set_xticklabels(STAT_PLOTS[stat]["xticklabels"](nodes))
    if "ylabel_format" in STAT_PLOTS[stat]:
        axes.ticklabel_format(**STAT_PLOTS[stat]["ylabel_format"])
    if "yscale" in STAT_PLOTS[stat]:
        axes.set_yscale(STAT_PLOTS[stat]["yscale"])
        if "ymax" in STAT_PLOTS[stat]:
            axes.set_ylim((0, STAT_PLOTS[stat]["ymax"]))
            axes.set_yticks([10**e for e in
                range(int(np.floor(np.log10(STAT_PLOTS[stat]["ymax"]))) + 1)])
    else:
        if "ymax" in STAT_PLOTS[stat]:
            axes.set_ylim((0, STAT_PLOTS[stat]["ymax"]))
            if "ysteps" in STAT_PLOTS[stat]:
                axes.set_yticks(np.arange(0, STAT_PLOTS[stat]["ymax"] + 1,
                                          STAT_PLOTS[stat]["ysteps"]))
        else:
            axes.set_ylim((0, axes.get_ylim()[1]))
            if "ysteps" in STAT_PLOTS[stat]:
                axes.set_yticks(np.arange(0, axes.get_ylim()[1] + 1,
                                STAT_PLOTS[stat1]["ysteps"]))
    axes.set_xlabel("Node")
    axes.set_ylabel(STAT_PLOTS[stat]["ylabel"])


def plot(filenames, stats_to_plot=None):
    plt.rcParams.update({
        "figure.max_open_warning": 40,
        "lines.linewidth": .8,
        "font.family": "serif",  # use serif/main font for text elements
        "text.usetex": True,     # use inline math for ticks
        "pgf.rcfonts": False,    # don't setup fonts from rc parameters
        "pgf.preamble": "\n".join([
             "\\usepackage{units}",          # load additional packages
             "\\usepackage{metalogo}",
             r"\setmainfont{DejaVu Serif}",  # serif font via preamble
         ])
    })
    if stats_to_plot is None:
        stats_to_plot = STAT_PLOTS.keys()
    dfs = collect_dataframes(filenames)
    figs = {}
    for key in dfs:
        df = dfs[key]["df"]
        mode = dfs[key]["mode"]
        nodes = key[2]
        delay = key[3]
        count = key[4]
        for stat in stats_to_plot:
            sfr_only = STAT_PLOTS[stat].get("sfr_only", False)
            if sfr_only and mode["mode"] != "sfr":
                continue
            fig_key = (nodes, delay, count, stat)
            if fig_key not in figs:
                figs[fig_key] = {}
                figs[fig_key]["mode"] = [mode]
                figs[fig_key]["fig"] = plt.figure(
                    figsize=STAT_PLOTS[stat].get("figsize", FIGSIZE_DEFAULT)
                )
                figs[fig_key]["ax"] = figs[fig_key]["fig"].add_subplot(111)
            else:
                figs[fig_key]["mode"].append(mode)
            stats = STAT_PLOTS[stat]["series"](df, count, nodes)
            mean = stats.mean()
            std = stats.std()
            roles_index = []
            for idx in mean.index:
                # NODE_ROLES for `nodes` contains `nodes` entries
                assert(nodes == len(NODE_ROLES[nodes]))
                roles_index.append(NODE_ROLES[nodes][idx])
            mean.index = roles_index
            std.index = roles_index
            # NODES_ORDER for `nodes` contains `nodes` entries
            assert(nodes == len(NODES_ORDER[nodes]))
            nodes_order = [n for n in NODES_ORDER[nodes] if n in mean.index]
            x = np.array([i for i, n in enumerate(NODES_ORDER[nodes])
                          if n in mean.index])
            label = "{}{}".format(
                HUMAN_READABLE_MODE[mode["mode"]],
                "" if mode["mode"] == "reass" else
                " w/ VREP" if mode["vrep"] else " w/o VREP"
            )
            figs[fig_key]["ax"].bar(
                x + MODE_OFFSET[sfr_only][mode["mode"]][mode["vrep"]],
                mean[:][nodes_order],
                BAR_WIDTH[sfr_only],
                color=STYLE[mode["mode"]][mode["vrep"]],
                linewidth=.5,
                edgecolor="k",
                yerr=std[:][nodes_order],
                label=label
            )
            if "legend" in STAT_PLOTS[stat]:
                if "fontsize" not in STAT_PLOTS[stat]["legend"]:
                    STAT_PLOTS[stat]["legend"]["fontsize"] = 9
                figs[fig_key]["ax"].legend(
                    **STAT_PLOTS[stat]["legend"]
                )
            plt.gcf()
    for fig_key in figs:
        nodes = fig_key[0]
        delay = fig_key[1]
        count = fig_key[2]
        stat = fig_key[3]
        set_axes(figs[fig_key]["ax"], nodes, stat)
        plot_name = os.path.join(
            DATA_PATH,
            "{stat}-{nodes}-{count}x{delay}ms"
            .format(stat=stat.replace("_", "-"),
                    nodes=nodes, count=count, delay=delay)
        )
        figs[fig_key]["fig"].savefig(
            "{}.pdf".format(plot_name),
            bbox_inches="tight"
        )
        figs[fig_key]["fig"].savefig(
            "{}.pgf".format(plot_name),
            bbox_inches="tight"
        )


def csl_stat(values):
    res = []
    for value in values.split(","):
        value = value.strip()
        if value not in STAT_PLOTS:
            raise ValueError("Unknown stat {}".format(value))
        res.append(value)
    return res


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--stat", nargs="?", default=STAT_PLOTS.keys(),
                        dest="stats_to_plot", type=csl_stat,
                        help="Comma separated list of stat to plot. "
                             "Possible values: {}. Default: all"
                             .format(", ".join(STAT_PLOTS.keys())))
    parser.add_argument("filenames", nargs="+",
                        help="CSV files as generated by ./parse_results.py to "
                             "takes stats from")
    args = parser.parse_args()
    plot(**vars(args))
