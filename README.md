# SDN_Mininet_Project

A software-defined networking project that demonstrates topology monitoring, link failure detection, automatic flow rule updates, and connectivity restoration using Mininet and the POX OpenFlow controller.

---

## Problem Statement

In traditional networks, switches make independent forwarding decisions and have no centralized awareness of topology changes. When a link fails, recovery is slow and decentralized.

This project implements an SDN-based solution where a central POX controller:
- Monitors all switch port state changes in real time
- Detects link failures immediately via OpenFlow `PortStatus` events
- Clears stale flow rules from affected switches
- Restores connectivity automatically by rerouting traffic through backup paths  

---

## Topology

```
h1 --- s1 --- s2 --- h2
        \     /
          s3
        /
      h3
```

Three switches (s1, s2, s3) form a triangle, providing a backup path when any single link fails. Three hosts (h1, h2, h3) are each connected to one switch.

**Design justification:** The triangle topology ensures there is always an alternate path between any two switches. When the s1-s2 link fails, traffic reroutes via s1-s3-s2 automatically.

---

## Setup

### Prerequisites

- Ubuntu (tested on Ubuntu Questing / 25.10)
- Python 3.x
- Mininet
- POX controller

### Installation

```bash
# Install Mininet
sudo apt update
sudo apt install mininet -y

# Clone POX
git clone https://github.com/noxrepo/pox.git ~/pox

# Copy controller into POX's ext directory
cp failover_controller.py ~/pox/pox/ext/
```

---

## Execution

**Terminal 1 — Start the POX controller:**
```bash
cd ~/pox
python3 pox.py log.level --DEBUG ext.failover_controller
```

You should see:
```
INFO:failover_controller:Failover Controller started
DEBUG:openflow.of_01:Listening on 0.0.0.0:6633
```

**Terminal 2 — Start Mininet:**
```bash
sudo mn --custom topo.py --topo failover --controller remote --mac
```

- `--controller remote` connects switches to POX on port 6633
- `--mac` assigns clean MAC addresses (h1=00:00:00:00:00:01, etc.)
- `--custom topo.py` loads the triangle topology

---

## Test Scenarios

### Scenario 1 — Normal Forwarding

```
mininet> pingall
```

**Expected output:**
```
h1 -> h2 h3
h2 -> h1 h3
h3 -> h1 h2
*** Results: 0% dropped (6/6 received)
```

POX terminal shows `PacketIn` events from all three switches as packets are flooded and reach their destinations.

---

### Scenario 2 — Link Failure and Recovery

```bash
# Start a continuous ping
mininet> h1 ping -c 10 h2

# In another window or after, bring down the s1-s2 link
mininet> link s1 s2 down
```

**Expected POX output:**
```
WARNING:failover_controller:LINK DOWN: switch 00-00-00-00-00-01 port 2 -- clearing flows
```

Traffic automatically reroutes via s1 → s3 → s2. Ping continues with minimal interruption.

```bash
# Restore the link
mininet> link s1 s2 up
```

**Expected POX output:**
```
INFO:failover_controller:LINK UP: switch 00-00-00-00-00-01 port 2 -- connectivity restored
```

---

## Performance Measurements

### Latency (ping)
```bash
mininet> h1 ping -c 5 h2
```

### Throughput (iperf)
```bash
mininet> h2 iperf -s &
mininet> h1 iperf -c 10.0.0.2 -t 5
```

### Flow Table Inspection
```bash
mininet> sh ovs-ofctl dump-flows s1
mininet> sh ovs-ofctl dump-flows s2
mininet> sh ovs-ofctl dump-flows s3
```

---

## Controller Logic

The controller (`failover_controller.py`) handles three OpenFlow events:

**`ConnectionUp`** — Fired when a switch connects. Logged for monitoring.

**`PacketIn`** — Fired when a packet arrives with no matching flow rule. The controller floods the packet out of all ports except the one it arrived on, ensuring delivery across the multi-switch topology.

**`PortStatus`** — The key event for fault tolerance:
- `OFPPR_DELETE` (port down) → logs the failure, sends `OFPFC_DELETE` to wipe all flow rules on that switch, forcing traffic to rediscover paths via flooding
- `OFPPR_ADD` (port up) → logs that connectivity is restored

---

## File Structure

```
├── topo.py                  # Custom Mininet triangle topology
├── failover_controller.py      # POX controller (copy to ~/pox/pox/ext/)
└── README.md
```

---

## References

- [Mininet Documentation](http://mininet.org/walkthrough/)
- [POX Wiki](https://noxrepo.github.io/pox-doc/html/)
- [OpenFlow 1.0 Specification](https://opennetworking.org/wp-content/uploads/2013/04/openflow-spec-v1.0.0.pdf)
- SDN Mininet Simulation Project Guidelines — course assignment handout
