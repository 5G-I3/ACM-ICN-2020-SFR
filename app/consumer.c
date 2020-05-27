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

#include <stdbool.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#include "ccn-lite-riot.h"
#include "evtimer_msg.h"
#include "random.h"
#include "xtimer.h"

#define MAX_NAMES   (2U)
#define REQ_URI_LEN (32U)
#define EVENT_TIME(t)  (((t) - ((t)/4)) + random_uint32_range(0, (t)/4))

static unsigned char _int_buf[CCNL_MAX_PACKET_SIZE];
static evtimer_t _evtimer;
static evtimer_msg_event_t _events[MAX_NAMES];
static unsigned reqtx = 0, resprx = 0;

static void send_static_request(char *prefix_str, unsigned long i)
{
    unsigned long reqtxt = 0;
    char req_uri[REQ_URI_LEN];
    struct ccnl_prefix_s *prefix = NULL;

    reqtx++;

    memset(_int_buf, 0, CCNL_MAX_PACKET_SIZE);
    snprintf(req_uri, REQ_URI_LEN, "%s/%05lu", prefix_str, i);
    prefix = ccnl_URItoPrefix(req_uri, CCNL_SUITE_NDNTLV, NULL);

    reqtxt = xtimer_now_usec();

    ccnl_send_interest(prefix, _int_buf, CCNL_MAX_PACKET_SIZE, NULL);
    ccnl_prefix_free(prefix);

    printf("qt;%lu;%05lu\n", reqtxt, i++);
}

static void _print_usage(char *cmd)
{
    printf("usage: %s <delay> <count> <name> [<name> [...]]\n", cmd);
    printf("       to a maximum of %u names.\n", MAX_NAMES);
}

static bool _check_names(unsigned name_num, char **names)
{
    if (name_num > MAX_NAMES) {
        return true;
    }
    for (unsigned i = 0; i < name_num; i++) {
        if (strlen(names[i]) > (REQ_URI_LEN - 5 - 2)) {
            return true;
        }
    }
    return false;
}

int send_get(int argc, char **argv)
{
    unsigned delay;
    unsigned count;

    if ((argc < 4) || _check_names(argc - 3, &argv[3])) {
        _print_usage(argv[0]);
        return -1;
    }
    delay = atoi(argv[1]);
    count = atoi(argv[2]);
    if (!delay || !count) {
        _print_usage(argv[0]);
        return -1;
    }
    evtimer_init_msg(&_evtimer);
    for (unsigned i = 0; i < MAX_NAMES; i++) {
        _events[i].event.offset = EVENT_TIME(delay);
        _events[i].msg.content.value = i;
        evtimer_add_msg(&_evtimer, &_events[i], sched_active_pid);
    }
    for (unsigned i = 0; i < (count * MAX_NAMES); i++) {
        msg_t m;
        msg_receive(&m);
        send_static_request(argv[3 + (i % (argc - 3))], i);
        _events[m.content.value].event.offset = EVENT_TIME(delay);
        evtimer_add_msg(&_evtimer, &_events[m.content.value], sched_active_pid);
    }
    return 0;
}

int my_app_RX(struct ccnl_relay_s *ccnl, struct ccnl_content_s *c)
{
    unsigned long resprxt = xtimer_now_usec();
    unsigned i = c->pkt->pfx->compcnt - 1;

    (void)ccnl;
    printf("pr;%lu;%.*s\n", resprxt,
           (size_t)c->pkt->pfx->complen[i],
           c->pkt->pfx->comp[i]);
    resprx++;

    return 0;
}

/** @} */
