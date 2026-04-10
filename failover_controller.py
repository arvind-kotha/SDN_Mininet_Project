from pox.core import core
import pox.openflow.libopenflow_01 as of
from pox.lib.revent import *
from pox.lib.util import dpidToStr

log = core.getLogger()

class FailoverController(EventMixin):
    def __init__(self):
        self.listenTo(core.openflow)
        self.listenTo(core.openflow_discovery)
        self.mac_to_port = {}

    def _handle_ConnectionUp(self, event):
        self.mac_to_port[event.dpid] = {}

    def _handle_LinkEvent(self, event):
        link = event.link
        if event.removed:
            log.info("Link Failed/Removed: %s -> %s", dpidToStr(link.dpid1), dpidToStr(link.dpid2))
            self.clear_all_flows()
        elif event.added:
            log.info("Link Added/Up: %s -> %s", dpidToStr(link.dpid1), dpidToStr(link.dpid2))
            self.clear_all_flows()

    def clear_all_flows(self):
        log.info("Topology change detected! Clearing all flow tables to trigger relearning.")
        self.mac_to_port.clear() 
        
        # Explicitly wildcard the match to guarantee all OVS flows are wiped
        for connection in core.openflow.connections:
            msg = of.ofp_flow_mod(command=of.OFPFC_DELETE)
            msg.match = of.ofp_match() 
            connection.send(msg)

    def _handle_PacketIn(self, event):
        packet = event.parsed
        if not packet.parsed:
            return

        dpid = event.dpid
        in_port = event.port
        mac_src = packet.src
        mac_dst = packet.dst

        if dpid not in self.mac_to_port:
            self.mac_to_port[dpid] = {}

        self.mac_to_port[dpid][mac_src] = in_port

        if mac_dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][mac_dst]
            
            if out_port == in_port:
                return
                
            msg = of.ofp_flow_mod()
            msg.match = of.ofp_match.from_packet(packet, in_port)
            msg.idle_timeout = 10
            msg.hard_timeout = 30
            msg.actions.append(of.ofp_action_output(port = out_port))
            msg.data = event.ofp
            event.connection.send(msg)
            
        else:
            msg = of.ofp_packet_out()
            msg.actions.append(of.ofp_action_output(port = of.OFPP_FLOOD))
            msg.data = event.ofp
            msg.in_port = in_port
            event.connection.send(msg)


def launch():
    from pox.openflow.discovery import launch as discovery_launch
    from pox.openflow.spanning_tree import launch as stp_launch

    log.info("Launching Discovery (Fast Mode), Spanning Tree, and Failover Modules...")
    
    
    discovery_launch(link_timeout=5)
    stp_launch()
    core.registerNew(FailoverController)
