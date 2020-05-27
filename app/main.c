/*
 * Copyright (C) 2020 Freie Universität Berlin
 * Copyright (C) 2020 HAW Hamburg
 *
 * This file is subject to the terms and conditions of the GNU Lesser
 * General Public License v2.1. See the file LICENSE in the top level
 * directory for more details.
 */

/**
 * @{
 *
 * @file
 * @author  Martine Lenders <m.lenders@fu-berlin.de>
 * @author  Cenk Gündoğan <cenk.guendogan@haw-hamburg.de>
 */

#include <stdio.h>

#include "msg.h"
#include "shell.h"
#include "ccn-lite-riot.h"
#include "net/gnrc/netif.h"
#include "ccnl-callbacks.h"
#include "ccnl-producer.h"
#include "random.h"

/* main thread's message queue */
#define MAIN_QUEUE_SIZE     (8)

static msg_t _main_msg_queue[MAIN_QUEUE_SIZE];
static uint8_t _hwaddr[GNRC_NETIF_L2ADDR_MAXLEN];
static char _hwaddr_str[GNRC_NETIF_L2ADDR_MAXLEN * 3];
static gnrc_netif_t *_netif = NULL;

extern int start_producer(int argc, char **argv);
extern int set_route(int argc, char **argv);
extern int send_get(int argc, char **argv);

static const shell_command_t shell_commands[] = {
    { "produce", "", start_producer },
    { "route", "", set_route },
    { "consume", "", send_get },
    { NULL, NULL, NULL }
};

static int _configure_interface(gnrc_netif_t *netif)
{
    int res;
    gnrc_nettype_t netreg_type = GNRC_NETTYPE_SIXLOWPAN;
    uint16_t src_len = 8U;

    gnrc_netapi_set(netif->pid, NETOPT_PROTO, 0, &netreg_type,
                    sizeof(gnrc_nettype_t));
    gnrc_netapi_set(netif->pid, NETOPT_SRC_LEN, 0, &src_len, sizeof(src_len));
    if ((res = gnrc_netapi_get(netif->pid, NETOPT_ADDRESS_LONG, 0, _hwaddr,
                               sizeof(_hwaddr))) < 0) {
        perror("Cannot get address");
        return -1;
    }
    gnrc_netif_addr_to_str(_hwaddr, res, _hwaddr_str);
    random_init(*((uint32_t *)_hwaddr));
    return 0;
}

int main(void)
{
    char line_buf[SHELL_DEFAULT_BUFSIZE];
    msg_init_queue(_main_msg_queue, MAIN_QUEUE_SIZE);

    ccnl_core_init();

    ccnl_start();

    _netif = gnrc_netif_iter(NULL);
    ccnl_open_netif(_netif->pid, GNRC_NETTYPE_CCN);
    if (_configure_interface(_netif) < 0) {
        return -1;
    }
    shell_run(shell_commands, line_buf, SHELL_DEFAULT_BUFSIZE);
    return 0;
}

/** @} */
