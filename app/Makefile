# name of your application
APPLICATION = icn20-icnlowpan-sfr

# If no BOARD is found in the environment, use this default:
BOARD ?= iotlab-m3

# This has to be the absolute path to the RIOT base directory:
RIOTBASE ?= $(CURDIR)/../RIOT

# IEEE 802.15.4 radio channel to run the experiments on
DEFAULT_CHANNEL ?= 20

# Include packages that pull up and auto-init the link layer.
USEMODULE += gnrc_netdev_default
USEMODULE += auto_init_gnrc_netif
# include command to analyze packet buffer (requires DEVELHELP = 1)
USEMODULE += gnrc_pktbuf_cmd
USEMODULE += od
# include command to check stats on reassembly buffers
USEMODULE += gnrc_sixlowpan
USEMODULE += gnrc_sixlowpan_frag_stats
# Queue packets when device is busy
USEMODULE += gnrc_netif_pktq
# Add PRNG
USEMODULE += random
# Add also the shell, some shell commands
USEMODULE += shell
USEMODULE += shell_commands
USEMODULE += ps
# include statistics modules
USEMODULE += netstats_l2
USEMODULE += netstats_ipv6
# include timers
USEMODULE += evtimer
USEMODULE += xtimer

# include CCN-lite
USEPKG += ccn-lite
USEPKG += libicnl

# Comment this out to disable code in RIOT that does safety checking
# which is not needed in a production environment but helps in the
# development process:
DEVELHELP ?= 1

# configure experiment mode
# - reass: hop-wise reassembly (HWR)
# - sfr: selective fragment recovery (SFR)
MODE ?= sfr
VREP ?= 1

ifeq (reass,$(MODE))
  USEMODULE += gnrc_sixlowpan_frag
endif
ifeq (sfr,$(MODE))
  USEMODULE += gnrc_sixlowpan_frag_sfr
  USEMODULE += gnrc_sixlowpan_frag_sfr_stats
  ifeq (1,$(VREP))
    USEMODULE += gnrc_sixlowpan_frag_vrep
  endif
endif

# Provide entry points for compile-time configuration via environment variables
VRB_SIZE ?= 32              # Virtual reassembly buffer size
RBUF_DEL_TIMER ?= 250       # Deletion timer for reassembly buffer entry after datagram completion
REASS_TIMEOUT ?= 100000     # Reassembly buffer timeout (1s)
FRAG_MSG_SIZE ?= 64         # Fragmentation buffer size
AGGRESSIVE_REASS ?= 0       # Deactivate aggressive reassembly (don't override when full)
WIN_SIZE ?= 1               # Window size for recovery mechanism
INTER_FRAME_GAP ?= 100      # Microseconds between two SFR frames
RETRY_TIMEOUT ?= 150        # Retry timeout for recovery mechanism
RETRIES ?= 4                # Number of retries for recovery mechanism
DATAGRAM_RETRIES ?= 0       # Number of datagram retries for SFR
SIMULATED_LOSS ?= 0

# Expose environment variable to build docker image
DOCKER_ENV_VARS += DEVELHELP
DOCKER_ENV_VARS += MODE
DOCKER_ENV_VARS += VRB_SIZE
DOCKER_ENV_VARS += VREP
DOCKER_ENV_VARS += RBUF_DEL_TIMER
DOCKER_ENV_VARS += FRAG_MSG_SIZE
DOCKER_ENV_VARS += AGGRESSIVE_REASS
DOCKER_ENV_VARS += REASS_TIMEOUT

ifeq (sfr,${MODE})
  CFLAGS += -DGNRC_SIXLOWPAN_SFR_OPT_WIN_SIZE=$(WIN_SIZE)
  CFLAGS += -DGNRC_SIXLOWPAN_SFR_MAX_WIN_SIZE=$(WIN_SIZE)
  CFLAGS += -DGNRC_SIXLOWPAN_SFR_INTER_FRAME_GAP_US=$(INTER_FRAME_GAP)
  CFLAGS += -DGNRC_SIXLOWPAN_SFR_OPT_ARQ_TIMEOUT_MS=$(RETRY_TIMEOUT)
  CFLAGS += -DGNRC_SIXLOWPAN_SFR_FRAG_RETRIES=$(RETRIES)
  CFLAGS += -DGNRC_SIXLOWPAN_SFR_DG_RETRIES=$(DATAGRAM_RETRIES)
  CFLAGS += -DCONFIG_GNRC_SIXLOWPAN_FRAG_FB_SIZE=32
endif
CFLAGS += -DGNRC_PKTBUF_SIZE=8192
CFLAGS += -DCONFIG_GNRC_NETIF_SIMULATED_LOSS=$(SIMULATED_LOSS)
CFLAGS += -DCONFIG_GNRC_SIXLOWPAN_FRAG_RBUF_DEL_TIMER=$(RBUF_DEL_TIMER)
CFLAGS += -DCONFIG_GNRC_SIXLOWPAN_FRAG_VRB_SIZE=$(VRB_SIZE)
CFLAGS += -DCONFIG_GNRC_SIXLOWPAN_FRAG_RBUF_SIZE=1
CFLAGS += -DGNRC_SIXLOWPAN_FRAG_RBUF_AGGRESSIVE_OVERRIDE=$(AGGRESSIVE_REASS)
CFLAGS += -DDEBUG_ASSERT_VERBOSE
CFLAGS += -DSHELL_NO_PROMPT=1


# CCN-lite config
CFLAGS += -DUSE_LINKLAYER
CFLAGS += -DCCNL_UAPI_H_
CFLAGS += -DUSE_SUITE_NDNTLV
CFLAGS += -DNEEDS_PREFIX_MATCHING
CFLAGS += -DNEEDS_PACKET_CRAFTING

CFLAGS += -DCCNL_CONTENT_TIMEOUT=30
CFLAGS += -DCCNL_FACE_TIMEOUT=3600
CFLAGS += -DCCNL_INTEREST_TIMEOUT=10
CFLAGS += -DCCNL_MAX_PACKET_SIZE=1280
CFLAGS += -DCCNL_MAX_INTEREST_RETRANSMIT=3
CFLAGS += -DCCNL_INTEREST_RETRANS_TIMEOUT=2000
CFLAGS += -DCCNL_CACHE_SIZE=24
CFLAGS += -DCCNL_DEFAULT_MAX_PIT_ENTRIES=60
CFLAGS += -DCCNL_STACK_SIZE="THREAD_STACKSIZE_DEFAULT+THREAD_EXTRA_STACKSIZE_PRINTF+1536"
CFLAGS += -DCCNL_QUEUE_SIZE=32

include $(RIOTBASE)/Makefile.include

# Set a custom channel if needed
include $(RIOTMAKE)/default-radio-settings.inc.mk
