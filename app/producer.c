/*
 * Copyright (C) 2020 Freie Universität Berlin
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
 */

#include <stdbool.h>

#include "ccn-lite-riot.h"
#include "ccnl-producer.h"
#include "xtimer.h"

#define CMPCNT          (3U)
#define CMPLEN          (10U)
#define SUFFIX_CNT      (1U)
#define DATA_MAX_SIZE   (1024U)

static unsigned char _data_buf[CCNL_MAX_PACKET_SIZE];
static unsigned char _name_prefix[CMPCNT][CMPLEN];
static unsigned char _data[DATA_MAX_SIZE];
static unsigned _name_prefix_cmpcnt = 0;
static size_t _data_len = 0;
static uint8_t _data_cnt[] = { 0x52, 0x13, 0xf6, 0xb5 };

static struct ccnl_content_s *_cont_and_cache(struct ccnl_relay_s *relay,
                                              struct ccnl_pkt_s *pkt)
{
    size_t offs = CCNL_MAX_PACKET_SIZE;

    size_t reslen = 0;

    ccnl_ndntlv_prependContent(pkt->pfx, _data, _data_len, NULL, NULL,
                               &offs, _data_buf, &reslen);

    size_t len = _data_len;

    unsigned char *olddata;
    unsigned char *data = olddata = _data_buf + offs;

    uint64_t typ;

    if (ccnl_ndntlv_dehead(&data, &reslen, &typ, &len) || typ != NDN_TLV_Data) {
        puts("ERROR in producer_func");
        return 0;
    }

    struct ccnl_content_s *c = 0;
    struct ccnl_pkt_s *pk = ccnl_ndntlv_bytes2pkt(typ, olddata, &data, &reslen);
    c = ccnl_content_new(&pk);
    if (c) {
        unsigned i = c->pkt->pfx->compcnt - 1;
        ccnl_content_add2cache(relay, c);
        char s[CCNL_MAX_PREFIX_SIZE];
        ccnl_prefix_to_str(c->pkt->pfx, s, CCNL_MAX_PREFIX_SIZE);
        uint32_t resptx = xtimer_now_usec();
        printf("pt;%lu;%.*s\n", (unsigned long)resptx,
               (size_t)c->pkt->pfx->complen[i],
               c->pkt->pfx->comp[i]);
    }

    return c;
}

static struct ccnl_content_s *_producer_func(struct ccnl_relay_s *relay,
                                             struct ccnl_face_s *from,
                                             struct ccnl_pkt_s *pkt) {
    (void) from;

    if(pkt->pfx->compcnt == (_name_prefix_cmpcnt + SUFFIX_CNT)) {
        bool match = true;

        for (unsigned i = 0; match && (i < _name_prefix_cmpcnt); i++) {
            match = match && (memcmp(pkt->pfx->comp[i], _name_prefix[i],
                              pkt->pfx->complen[i]) == 0);
            if (!match) {
                printf("component %u does not match %.*s != %s\n", i,
                       pkt->pfx->complen[i], pkt->pfx->comp[i],
                       _name_prefix[i]);
            }
        }
        if (match) {
            return _cont_and_cache(relay, pkt);
        }
    }
    else {
        printf("compcnt does not match %u != %u\n",
               (unsigned)pkt->pfx->compcnt, _name_prefix_cmpcnt + SUFFIX_CNT);
    }
    return NULL;
}

int start_producer(int argc, char **argv)
{
    char *cmp, *prefix_str = argv[1];
    unsigned i = 0;

    if (_name_prefix_cmpcnt != 0) {
        puts("Producer already started");
        return -1;
    }

    if ((argc < 3) || (strlen(argv[1]) >= CCNL_MAX_PREFIX_SIZE) ||
        ((unsigned)atoi(argv[2]) >= DATA_MAX_SIZE) || (atoi(argv[2]) <= 0)) {
        printf("usage: %s <prefix> <data_len>\n", argv[0]);
        return -1;
    }

    while ((cmp = strtok(prefix_str, "/"))) {
        prefix_str = NULL;
        if (strlen(cmp) > CMPLEN) {
            printf("Prefix component %s longer than CMPLEN=%u\n",
                   cmp, CMPLEN);
            return -1;
        }
        strcpy((char *)_name_prefix[i], cmp);
        if (++i > CMPCNT) {
            printf("Too many components (%u > %u)\n", i, CMPCNT);
            return -1;
        }
    }
    _name_prefix_cmpcnt = i;
    for (unsigned i = 0; i < _name_prefix_cmpcnt; i++) {
        printf("prefix comp [i=%u]=%s\n", i, _name_prefix[i]);
    }
    _data_len = atoi(argv[2]);
    for (i = 0; i < _data_len; i += sizeof(_data_cnt)) {
        if ((_data_len - i) < sizeof(_data_cnt)) {
            memcpy(&_data[i], _data_cnt, _data_len - i);
        }
        else {
            memcpy(&_data[i], _data_cnt, sizeof(_data_cnt));
        }
    }
    ccnl_set_local_producer(_producer_func);
    puts("Started producer");
    return 0;
}

/** @} */
