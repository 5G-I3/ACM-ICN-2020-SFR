#!/bin/sh
#
# Copyright (C) Freie Universität Berlin
#
# This file is subject to the terms and conditions of the GNU Lesser
# General Public License v2.1. See the file LICENSE in the top level
# directory for more details.

SCRIPT_DIR="$(readlink -f "$(dirname $0)")"
APP_DIR=${SCRIPT_DIR}
DOCKER_APP_DIR=/data/riotbuild/riotproject/app
BOARD=iotlab-m3
APP_NAME=icn20-icnlowpan-sfr

if [ -z "${DATA_DIR}" ]; then
    DATA_DIR="$(readlink -f ${SCRIPT_DIR}/../results)"
fi

if [ "$1" = "-w" ]; then
    COSY_OPT=""
    shift 1
else
    COSY_OPT="-d"
fi

MODE=$1
VREP=$2

if [ -z "${MODE}" ]; then
    echo "usage: $0 [-w] <mode> [vrep]" >&2
    exit 1
else
    BINDIRNAME=${MODE}-bin
fi

if [ -z "${VREP}" ]; then
    VREP=0
elif [ "${VREP}" = "0" ]; then
    VREP=0
else
    VREP=1
    if [ "${MODE}" = "sfr" ]; then
        BINDIRNAME=${MODE}-vrep-bin
    fi
fi

if [ -d "${SCRIPT_DIR}/cosy" ]; then
    git -C "${SCRIPT_DIR}/cosy" pull
else
    cd ${SCRIPT_DIR}
    git clone https://github.com/haukepetersen/cosy "cosy"
fi

if [ -n "${COSY_OPT}" ]; then
    COSY_OPT="${COSY_OPT} -c ${DATA_DIR}/${BINDIRNAME}-size.csv"
fi

BINDIR=${APP_DIR}/${BINDIRNAME}

# workaround for pkg issue I had
rm -rf "${BINDIR}"/pkg/*/ccn-lite/bin
BINDIRBASE=${BINDIR} MODE=${MODE} VREP=${VREP} BOARD=${BOARD} RIOT_CI_BUILD=1 \
    make -C ${APP_DIR}
rm -rf "${BINDIR}"/pkg/*/ccn-lite/bin

MODE=${MODE} VREP=${VREP} BOARD=${BOARD} \
    DOCKER_ENVIRONMENT_CMDLINE="-e BINDIRBASE=${DOCKER_APP_DIR}/${BINDIRNAME}" \
    BUILD_IN_DOCKER=1 RIOT_CI_BUILD=1 DOCKER_MAKE_ARGS=-j \
    make -C ${APP_DIR} clean all
cd ${SCRIPT_DIR}/cosy
./cosy.py ${COSY_OPT} "${BINDIR}" ${BOARD} \
    "${BINDIR}/${BOARD}/${APP_NAME}.elf" \
    "${BINDIR}/${BOARD}/${APP_NAME}.map"
