Application
===========

This application implements all roles within the NDN network for the experiments
for the paper. The role can be configured using the `consume`, `produce`, or
`route` commands respectively. A node can have multiple roles.

Compile-time configuration
--------------------------
Most compile-time configuration for this application we decided to leave
constant as changing them too much might lead to erroneous behavior. You can
have a look at the `CFLAGS` in the [Makefile](./Makefile) to see what
configuration that is exactly.

The following compile-time configurations are exposed and can be changed to the
via environment variables:

- `MODE`: (default: `sfr`) The fragment forwarding variant for the experiment.
  Can be either `reass` (for hop-wise reassembly [HWR]) or `sfr` (for fragment.
  forwarding with selective fragment recovery [SFR])
- `VREP`: (default: `1`) Use the Virtual Reassembling End-point (VREP) extension
  when `1`, for any other value the VREP is not used. Ignored when `MODE=reass`.
- `VRB_SIZE`: (default: 32) The size of the virtual reassembly buffer (with
  `MODE=sfr`).
- `RBUF_DEL_TIMER`: (default: 250) Deletion timer in microseconds for an
  reassembly buffer entry after datagram completion.
- `REASS_TIMEOUT`: (default: 100000) Reassembly buffer entry timeout in
  microseconds.
- `WIN_SIZE`: (default: 1) Window size for SFR.
- `INTER_FRAME_GAP`: (default: 100) Delay in microseconds between two SFR
  frames.
- `RETRY_TIMEOUT`: (default: 150) Retransmission timeout for fragments in and
  datagrams in milliseconds with SFR.
- `RETRIES`: (default: 4) maximum for fragment retransmissions with SFR.
- `DATAGRAM_RETRIES`: (default: 0) maximum for datagram retransmissions with
  SFR.

Usage
-----
### Producer
The producer can be started with the `produce` command:

```
produce <prefix> <data_len>
```

Whenever the producer receives an interest for a name prefixed with `<prefix>`
it generates a content chunk of content length `<data_len>` with repeating
truncated byte sequence `0x52 0x13 0xf6 0xb5`. The name of that content chunk
will be the one requested by the interest.

When a content is first transmitted, it will print a line such as

```
pt;<timestamp>;<suffix>
```

where `<timestamp>` is the value of `xtimer_now_usec()` after the interest was
retransmitted and `<suffix>` is the last component of the name of the
transmitted content's name.

Whenever a content cache entry is hit, the producer will output a line such as

```
cs;;<suffix>
```

with `<suffix>` being the same as above.

Forwarder
---------
The forwarder can be configured using the `route` command:

```
route <prefix> <next hop l2>
```

This will create a FIB entry that forwards Interests with prefix `<prefix>` to
the node with link layer address `<next hop l2>`.

Whenever an interest is retransmitted the forwarder will output a line such as

```
rt;<timestamp>;<suffix>
```

where `<timestamp>` is the value of `xtimer_now_usec()` after the content was
added to the content store and `<suffix>` is the last component of the name of
the transmitted name the interest is addressed to.

Whenever a content cache entry is hit, the producer will output a line such as

```
cs;;<suffix>
```

with `<suffix>` being the same as above.

Consumer
--------
The consumer can be started with the `consume` command:

```
consume <delay> <count> <prefix> [<prefix>]
```

It can receive multiple prefixes (up to `MAX_NAMES=2`), for each producer one.
Once started it will send `<count>` interests to `<prefix>/<suffix>` spaced with
a random delay uniformly distributed between `<delay> +- <delay>/4`.
`<suffix>` will be a 5-digit number (padded with 0s when <10000) unique to each
interest.

Whenever an interest is first transmitted the consumer will output a line such
as

```
qt;<timestamp>;<suffix>
```

where `<timestamp>` is the value of `xtimer_now_usec()` after the interest was
transmitted and `<suffix>` being the same as above.

Whenever an interest is retransmitted the consumer will output a line such as

```
rt;<timestamp>;<suffix>
```

with `<timestamp>` and `<suffix>` being the same as above.

Whenever a content chunk for an interest is received the consumer will output a
line such as

```
pr;<timestamp>;<suffix>
```

where `<timestamp>` is the value of `xtimer_now_usec()` after the content chunk
was received and `<suffix>` is the last component of the name of the
transmitted content's name.
