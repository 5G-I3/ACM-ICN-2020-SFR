#!/usr/bin/env python3
#
# Copyright (C) 2020 Freie Universität Berlin
#
# This file is subject to the terms and conditions of the GNU Lesser
# General Public License v2.1. See the file LICENSE in the top level
# directory for more details.

import re
import os
import sys

import pandas as pd
import numpy as np
import matplotlib as mpl
mpl.use("pgf")
import matplotlib.pyplot as plt                     # noqa: E402

from matplotlib.patches import Polygon              # noqa: E402

from parse_results import DATA_PATH                 # noqa: E402


MODE_PATTERN = r"(?P<mode>(sfr|reass))" \
               r"(-win(?P<win>\d+)ifg(?P<ifg>\d+)arq(?P<arq>\d+)" \
               r"r(?P<frag_rt>\d+)dg(?P<dg_rt>\d+))?(?P<vrep>-vrep)?$"
HUMAN_READABLE_MODE = {
    "reass": "HWR",
    "sfr": "SFR",
}
STYLE = {
    "reass": {None: ":"},
    "sfr": {None: "--", "-vrep": "-"}
}

SUBPLOT_Y_THRESH = 0.05
SUBPLOT_X = 0.3
SUBPLOT_Y = 0.2
SUBPLOT_WIDTH = 0.6
SUBPLOT_HEIGHT = 0.6

US_PER_SEC = 1000000


def add_subplot_axes(ax, rect, axisbg='w'):
    # https://stackoverflow.com/a/17479417
    fig = plt.gcf()
    box = ax.get_position()
    width = box.width
    height = box.height
    inax_position = ax.transAxes.transform(rect[0:2])
    transFigure = fig.transFigure.inverted()
    infig_position = transFigure.transform(inax_position)
    x = infig_position[0]
    y = infig_position[1]
    width *= rect[2]
    height *= rect[3]  # <= Typo was here
    subax = fig.add_axes([x, y, width, height], facecolor=axisbg)
    x_labelsize = subax.get_xticklabels()[0].get_size()
    y_labelsize = subax.get_yticklabels()[0].get_size()
    x_labelsize *= rect[2]**0.1
    y_labelsize *= rect[3]**0.1
    subax.xaxis.set_tick_params(labelsize=x_labelsize)
    subax.yaxis.set_tick_params(labelsize=y_labelsize)
    return subax


def _plot(ax, bins, cdf, mode):
    label = "{}{}".format(
        HUMAN_READABLE_MODE[mode["mode"]],
        "" if mode["mode"] == "reass" else
        " w/ VREP" if mode["vrep"] else " w/o VREP"
    )
    ax.plot(bins[1:] / US_PER_SEC, cdf, STYLE[mode["mode"]][mode["vrep"]],
            color="k", label=label)


def collect_dataframes(filenames):
    res = {}
    c = re.compile(MODE_PATTERN)
    for filename in filenames:
        print(filename)
        df = pd.read_csv(filename)
        if df.size == 0:
            continue
        mode = df["mode"]
        delay = df["delay"]
        count = df["count"]
        nodes = df["nodes"]
        # mode, delay, count, and columns are all the same
        assert(all(mode[0] == m for m in mode))
        assert(all(delay[0] == d for d in delay))
        assert(all(count[0] == c for c in count))
        assert(all(nodes[0] == n for n in nodes))
        match = c.match(mode[0])
        if match is None:
            continue
        mode = match.groupdict()
        key = mode["mode"], bool(mode["vrep"]), nodes[0], delay[0], count[0]
        if key in res:
            res[key]["df"] = pd.concat([res[key]["df"], df])
        else:
            res[key] = {
                "df": df,
                "mode": mode,
            }
    return res


def plot(filenames):
    plt.rcParams.update({
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
    x_max = 0
    for key in dfs:
        df = dfs[key]["df"]
        mode = dfs[key]["mode"]
        nodes = key[2]
        delay = key[3]
        count = key[4]
        fig_key = (nodes, delay, count)
        if fig_key not in figs:
            figs[fig_key] = {}
            figs[fig_key]["mode"] = [mode]
            figs[fig_key]["fig"] = plt.figure(
                figsize=(2.4587625, 1.73851894)
            )
            figs[fig_key]["ax"] = figs[fig_key]["fig"].add_subplot(111)
            figs[fig_key]["ax"].set_ylim(0, 1)
            figs[fig_key]["ax1"] = {}
            figs[fig_key]["ax1"]["mag"] = float("-inf")
            figs[fig_key]["ax1"]["ax"] = None
            figs[fig_key]["ax1"]["min"] = float("inf")
            figs[fig_key]["ax1"]["max"] = 0
        else:
            figs[fig_key]["mode"].append(mode)
        ttcs = (df["recv_time"].astype('float') -
                df["send_time"].astype('float')).values
        ttcs = ttcs[np.isfinite(ttcs)]
        maxrel = ttcs.shape[0] / df["send_time"].values.shape[0]
        hist, bins = np.histogram(ttcs, bins=100, density=1)
        dx = bins[1] - bins[0]
        cdf = np.cumsum(hist) * dx * maxrel
        if not all(np.isnan(cdf)) and (max(cdf) < SUBPLOT_Y_THRESH):
            if figs[fig_key]["ax1"]["ax"] is None:
                figs[fig_key]["ax1"]["ax"] = add_subplot_axes(
                    figs[fig_key]["ax"],
                    [SUBPLOT_X, SUBPLOT_Y, SUBPLOT_WIDTH, SUBPLOT_HEIGHT]
                )
            magnitude = int(np.log10(max(bins)))
            if figs[fig_key]["ax1"]["mag"] < magnitude:
                figs[fig_key]["ax1"]["mag"] = magnitude
                scale = 10**magnitude
                if figs[fig_key]["ax1"]["max"] > 0:
                    mx = figs[fig_key]["ax1"]["max"]
                    # round up to nearest multiple of scale
                    figs[fig_key]["ax1"]["max"] = \
                        (np.ceil(mx / scale)) * scale
                if figs[fig_key]["ax1"]["min"] < float("inf"):
                    mn = figs[fig_key]["ax1"]["min"]
                    # round up to nearest multiple of scale
                    figs[fig_key]["ax1"]["min"] = (mn // scale) * scale
            else:
                scale = 10**figs[fig_key]["ax1"]["mag"]
            if figs[fig_key]["ax1"]["max"] < max(bins):
                # round up to nearest multiple of scale
                figs[fig_key]["ax1"]["max"] = \
                    int(np.ceil(max(bins) / scale)) * scale
            if figs[fig_key]["ax1"]["min"] > min(bins):
                figs[fig_key]["ax1"]["min"] = \
                    (min(bins) // scale) * scale
            _plot(figs[fig_key]["ax1"]["ax"], bins, cdf, mode)
        _plot(figs[fig_key]["ax"], bins, cdf, mode)
        xlim = figs[fig_key]["ax"].get_xlim()
        if xlim[1] > x_max:
            x_max = xlim[1]
    for fig_key in figs:
        nodes = fig_key[0]
        delay = fig_key[1]
        count = fig_key[2]
        xlim = figs[fig_key]["ax"].get_xlim()
        xlim = -0.1, 10.1
        figs[fig_key]["ax"].set_xticks(np.arange(0, 11, 2))
        figs[fig_key]["ax"].set_xlim(xlim)
        if figs[fig_key]["ax1"]["ax"]:
            ylim = figs[fig_key]["ax"].get_ylim()
            orig_left = (figs[fig_key]["ax1"]["min"] / US_PER_SEC,
                         ylim[0])
            orig_right = (figs[fig_key]["ax1"]["max"] / US_PER_SEC,
                          ylim[0])
            proj_y = ((ylim[1] - ylim[0]) * SUBPLOT_Y) + ylim[0]
            proj_left = (((xlim[1] - xlim[0]) * SUBPLOT_X) + xlim[0], proj_y)
            proj_right = (((xlim[1] - xlim[0]) * (SUBPLOT_X + SUBPLOT_WIDTH)) +
                          xlim[0], proj_y)
            mark = Polygon(np.array([orig_left, orig_right, proj_right,
                                     proj_left]),
                           facecolor="lightgray", edgecolor=None, alpha=.5,
                           zorder=-1)
            figs[fig_key]["ax"].add_patch(mark)
            ylim = figs[fig_key]["ax1"]["ax"].get_ylim()
            figs[fig_key]["ax1"]["ax"].set_ylim((0, ylim[1]))
            figs[fig_key]["ax1"]["ax"].set_xticks(
                figs[fig_key]["ax"].get_xticks()
            )
            figs[fig_key]["ax1"]["ax"].set_xlim((0, orig_right[0]))
        figs[fig_key]["ax"].set_xlabel("TTC [sec]")
        figs[fig_key]["ax"].set_ylabel("CDF")
        figs[fig_key]["ax"].margins(0)
        if delay == 1000 and nodes == 5:
            figs[fig_key]["ax"].legend(
                loc="upper left",
                fontsize=7,
            )
        plot_name = os.path.join(
            DATA_PATH,
            "cdf-{nodes}-{count}x{delay}ms"
            .format(nodes=nodes, count=count, delay=delay)
        )
        figs[fig_key]["fig"].savefig(
            "{}.pdf".format(plot_name),
            bbox_inches="tight"
        )
        figs[fig_key]["fig"].savefig(
            "{}.pgf".format(plot_name),
            bbox_inches="tight"
        )
        plt.gcf()


if __name__ == "__main__":
    plot(sys.argv[1:])
