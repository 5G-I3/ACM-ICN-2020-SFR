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

#include "ccn-lite-riot.h"
#include "net/gnrc/netif.h"

static struct ccnl_face_s *_intern_face_get(uint8_t *addr, size_t addr_len)
{
    sockunion sun;
    sun.sa.sa_family = AF_PACKET;
    memcpy(&(sun.linklayer.sll_addr), addr, addr_len);
    sun.linklayer.sll_halen = addr_len;
    sun.linklayer.sll_protocol = htons(ETHERTYPE_NDN);
    return ccnl_get_face_or_create(&ccnl_relay, 0, &sun.sa,
                                   sizeof(sun.linklayer));
}

static int _install_route(char *prefix_str,
                          uint8_t *nh_addr, size_t nh_addr_len)
{
    int suite = CCNL_SUITE_NDNTLV;
    struct ccnl_prefix_s *prefix = ccnl_URItoPrefix((char *)prefix_str, suite,
                                                    NULL);
    if (prefix == NULL) {
        puts("Cannot convert URI to prefix\n");
        return -1;
    }
    struct ccnl_face_s *fibface = _intern_face_get(nh_addr, nh_addr_len);

    fibface->flags |= CCNL_FACE_FLAGS_STATIC;
    ccnl_fib_add_entry(&ccnl_relay, prefix, fibface);
    return 0;
}

int set_route(int argc, char **argv)
{
    uint8_t nh_addr[GNRC_NETIF_L2ADDR_MAXLEN];
    size_t nh_addr_len;

    if (argc < 3) {
        printf("usage: %s <prefix> <next hop l2>\n", argv[0]);
        return -1;
    }

    memset(nh_addr, UINT8_MAX, GNRC_NETIF_L2ADDR_MAXLEN);
    nh_addr_len = gnrc_netif_addr_from_str(argv[2], nh_addr);
    if (nh_addr_len == 0) {
        puts("Unable to parse next hop address");
        return -1;
    }
    return _install_route(argv[1], nh_addr, nh_addr_len);
}

/** @} */
