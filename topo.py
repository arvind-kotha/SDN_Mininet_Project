from mininet.topo import Topo

class FailoverTopo(Topo):
    def build(self):
        # Create three switches that form a triangle
        s1 = self.addSwitch('s1')
        s2 = self.addSwitch('s2')
        s3 = self.addSwitch('s3')

        # Create three hosts, one per switch
        h1 = self.addHost('h1')
        h2 = self.addHost('h2')
        h3 = self.addHost('h3')

        # Connect each host to its switch
        self.addLink(h1, s1)
        self.addLink(h2, s2)
        self.addLink(h3, s3)

        # Connect switches in a triangle so there is always a backup path
        self.addLink(s1, s2)  # primary link between s1 and s2
        self.addLink(s2, s3)
        self.addLink(s1, s3)  # backup path: if s1-s2 fails, traffic goes s1-s3-s2

# Register topology so Mininet can find it via --topo failover
topos = {'failover': FailoverTopo}
