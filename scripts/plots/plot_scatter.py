#!/usr/bin/env python3
#
# Copyright (C) 2020 Freie Universität Berlin
#
# This file is subject to the terms and conditions of the GNU Lesser
# General Public License v2.1. See the file LICENSE in the top level
# directory for more details.

import argparse
import os

import numpy as np
import matplotlib.pyplot as plt                                 # noqa: E402

from parse_results import DATA_PATH                             # noqa: E402
from plot_stats import STAT_PLOTS, NODE_ROLES
from plot_cdf import HUMAN_READABLE_MODE, collect_dataframes    # noqa: E402


STYLE = {
    "reass": {None: {"marker": "x"}},
    "sfr": {None: {"marker": "o", "facecolor": "k"},
            "-vrep": {"marker": "o", "facecolor": "lightgray"}},
}
MARKS = {
    "F5": {"x": 380, "y": 0.5},
    "F6": {"x": 300, "y": 20},
}


def set_axes(axes, nodes, stat1, stat2):
    xlim = axes.get_xlim()
    ylim = axes.get_ylim()
    if xlim[1] < 1:
        xlim = (0, 1)
    if ylim[1] < 1:
        ylim = (0, 1)
    axes.set_xlim(0, xlim[1])
    if "yscale" in STAT_PLOTS[stat1]:
        axes.set_xscale(STAT_PLOTS[stat1]["yscale"])
    elif "ysteps" in STAT_PLOTS[stat1]:
        axes.set_xticks(np.arange(0, axes.get_xlim()[1] + 1,
                                  STAT_PLOTS[stat1]["ysteps"]))
    if "yscale" in STAT_PLOTS[stat2]:
        axes.set_yscale(STAT_PLOTS[stat2]["yscale"])
        if "ymax" in STAT_PLOTS[stat2]:
            axes.set_ylim((0, STAT_PLOTS[stat2]["ymax"]))
            axes.set_yticks([10**e for e in
                range(int(np.floor(np.log10(STAT_PLOTS[stat2]["ymax"]))) + 1)])
    else:
        if "ymax" in STAT_PLOTS[stat2]:
            axes.set_ylim((0, STAT_PLOTS[stat2]["ymax"]))
            if "ysteps" in STAT_PLOTS[stat2]:
                axes.set_yticks(np.arange(ymin, STAT_PLOTS[stat2]["ymax"] + 1,
                                          STAT_PLOTS[stat2]["ysteps"]))
        else:
            axes.set_ylim((0, axes.get_ylim()[1]))
            if "ysteps" in STAT_PLOTS[stat2]:
                axes.set_yticks(np.arange(0, axes.get_ylim()[1] + 1,
                                STAT_PLOTS[stat1]["ysteps"]))
    axes.set_xlabel(STAT_PLOTS[stat1]["ylabel"])
    axes.set_ylabel(STAT_PLOTS[stat2]["ylabel"])


def mark_cluster(axes, node_role, stats1, stats2):
    annotation_color = "#555555"
    prop = dict(arrowstyle="->,head_width=0.15,head_length=0.4",
                shrinkA=0, shrinkB=0, color=annotation_color)
    textx = MARKS[node_role]["x"]
    texty = MARKS[node_role]["y"]
    x = stats1.mean()
    y = stats2.mean()
    axes.annotate(node_role, xy=(x, y), xytext=(textx, texty),
                  arrowprops=prop, color=annotation_color)


def plot(node_names, stat1, stat2, filenames, mark_nodes=False):
    assert stat1 in STAT_PLOTS
    assert stat2 in STAT_PLOTS
    plt.rcParams.update({
        "figure.max_open_warning": 30,
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
    dfs = collect_dataframes(filenames)
    figs = {}
    sfr_only = STAT_PLOTS[stat1].get("sfr_only") or \
        STAT_PLOTS[stat2].get("sfr_only")
    for key in dfs:
        df = dfs[key]["df"]
        mode = dfs[key]["mode"]
        nodes = key[2]
        delay = key[3]
        count = key[4]
        if any(node not in NODE_ROLES[nodes] for node in node_names):
            print("{} not in NODE_ROLES for {} nodes".format(node_names, nodes))
            continue
        if sfr_only and mode["mode"] != "sfr":
            continue
        fig_key = (nodes, delay, count)
        if fig_key not in figs:
            figs[fig_key] = {}
            figs[fig_key]["mode"] = [mode]
            figs[fig_key]["fig"] = plt.figure(
                figsize=(2.4587625, 1.73851894)
            )
            figs[fig_key]["ax"] = figs[fig_key]["fig"].add_subplot(111)
        else:
            figs[fig_key]["mode"].append(mode)
        stats1 = STAT_PLOTS[stat1]["column"](df, count, nodes)
        stats2 = STAT_PLOTS[stat2]["column"](df, count, nodes)
        roles_index = []
        for idx in stats1.index:
            # NODE_ROLES for `nodes` contains `nodes` entries
            assert(nodes == len(NODE_ROLES[nodes]))
            roles_index.append(df["node"][idx])
        stats1.index = roles_index
        roles_index = []
        for idx in stats2.index:
            # NODE_ROLES for `nodes` contains `nodes` entries
            assert(nodes == len(NODE_ROLES[nodes]))
            roles_index.append(df["node"][idx])
        stats2.index = roles_index
        label = "{}{}".format(
            HUMAN_READABLE_MODE[mode["mode"]],
            "" if mode["mode"] == "reass" else
            " w/ VREP" if mode["vrep"] else " w/o VREP"
        )
        figs[fig_key]["ax"].scatter(
            stats1[:][node_names],
            stats2[:][node_names],
            color="k",
            label=label,
            **STYLE[mode["mode"]][mode["vrep"]],
        )
        figs[fig_key]["ax"].legend(loc="lower left", fontsize=8)
        if mark_nodes:
            if nodes == 8 and delay == 1000 and \
               mode["mode"] == "sfr" and not mode["vrep"]:
                for node in node_names:
                    node_role = NODE_ROLES[nodes][node]
                    # skip empty data sets or if there is no arrow parameters
                    if not any(np.isfinite(stats2[:][node])) or \
                       node_role not in MARKS:
                        continue
                    mark_cluster(figs[fig_key]["ax"], node_role,
                                 stats1[:][node], stats2[:][node])
        plt.gcf()
    for fig_key in figs:
        nodes = fig_key[0]
        delay = fig_key[1]
        count = fig_key[2]
        set_axes(figs[fig_key]["ax"], nodes, stat1, stat2)
        plot_name = os.path.join(
            DATA_PATH,
            "{stat1}-v-{stat2}-{nodes}-{node_names}-{count}x{delay}ms"
            .format(stat1=stat1.replace("_", "-"),
                    stat2=stat2.replace("_", "-"),
                    nodes=nodes, node_names="+".join(node_names),
                    count=count, delay=delay)
        )
        figs[fig_key]["fig"].savefig(
            "{}.pdf".format(plot_name),
            bbox_inches="tight"
        )
        figs[fig_key]["fig"].savefig(
            "{}.pgf".format(plot_name),
            bbox_inches="tight"
        )


def csl(values):
    res = []
    for value in values.split(","):
        value = value.strip()
        res.append(value)
    return res


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mark-nodes", "-m", action="store_true",
                        help="Mark node clusters in plot for daisy chain and "
                             "1000ms delay and SFR w/o VREP")
    parser.add_argument("nodes", type=csl,
                        help="Nodes to plot scatter plot for")
    parser.add_argument("stat1", help="Stat for x-axis")
    parser.add_argument("stat2", help="Stat for y-axis")
    parser.add_argument("filenames", help="Filenames", nargs="+")
    args = parser.parse_args()
    plot(args.nodes, args.stat1, args.stat2, args.filenames, args.mark_nodes)
