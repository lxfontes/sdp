#!/usr/bin/env python
import sys

from twisted.internet.protocol import Protocol, Factory
from twisted.internet.task import LoopingCall
from twisted.internet import reactor, endpoints, defer

from diameter import protocol,dictionary, stack, peer

class SampleApplication(stack.ApplicationListener):
    def __init__(self):
        pass

    def onRequest(self, peer, request):
        print "Got request"
        x = request.createAnswer()
        self.stack.sendByPeer(peer,x)

    def onAnswer(self, peer, answer):
        print "Got answer %d" % answer.hBh

    def onRedirect(self, peer, request):
        print "Got redirect"

    def onRetransmit(self, peer, request):
        print "Retransmitted message"

    def onTick(self):
        print "App tick"

class SamplePeerListener(stack.PeerListener):

    def __init__(self):
        pass

    def connected(self, peer):
        print("Peer %s connected" % peer.identity)
        gy = peer.stack.getDictionary("Gy")
        req = peer.stack.createRequest(4, 272, True)
        avp = gy.getAVP('Session-Id')
        avp.setOctetString('something')
        req.addAVP(avp)

        peer.stack.sendByPeer(peer, req)

    def disconnected(self, peer):
        print("Peer %s disconnected" % peer.identity)

class SamplePeerIOTwisted(Protocol):
    def __init__(self, peer):
        self.peer = peer
        self.in_buffer = r''
        self.in_pos = 0

    def connectionMade(self):
        self.peer._protocol = self
        self.peer.feed(None, 0)

    def dataReceived(self, data):
        self.in_buffer += data
        self.in_pos += len(data)
        consumed = self.peer.feed(self.in_buffer, self.in_pos)
        print("Consumed %d" % consumed)
        if consumed > 0:
            self.in_buffer = self.in_buffer[consumed:]
            self.in_pos -= consumed

class TwistedClientFactory(Factory):
    def __init__(self, client_peer):
        self.client_peer = client_peer

    def buildProtocol(self, addr):
        print("IO connected!")
        return SamplePeerIOTwisted(self.client_peer)

    def delayedConnect(self, endpoint):
        d = endpoint.connect(self)
        print("Retrying connection")
        d.addErrback(self.failure, endpoint)

    def failure(self, err, endpoint):
        d = defer.Deferred()
        reactor.callLater(10, self.delayedConnect, endpoint)

class TwistedServerFactory(Factory):
    def __init__(self, base_peer):
        self.server_peer = base_peer
        self.stack = base_peer.stack

    def buildProtocol(self, addr):
        client_peer = self.stack.serverV4Accept(self.server_peer, "1.1.1",11)
        print("New client accepted")
        return SamplePeerIOTwisted(client_peer)

class SamplePeerIO(peer.PeerIOCallbacks):
    def __init__(self):
        pass

    def write(self, peer, data, length):
        #twisted protocol is in peer._protocol
        peer._protocol.transport.write(data)

    def connectV4(self, peer, host, port):
        factory = TwistedClientFactory(peer)
        endpoint = endpoints.TCP4ClientEndpoint(reactor, host, port)
        print("Connecting to %s:%d" % (host, port))
        d = endpoint.connect(factory)
        d.addErrback(factory.failure, endpoint)
        pass

    def listenV4(self, peer, host, port):
        factory = TwistedServerFactory(peer)
        endpoint = endpoints.TCP4ServerEndpoint(reactor, port, 50, host)
        print("Listening on %s:%d" % (host, port))
        endpoint.listen(factory)

    def close(self, peer):
        pass

def main():
    dstack = stack.Stack()
    dstack.loadDictionary("Gy", "gy.xml")
    dstack.identity = "primary.nuswit.com"
    dstack.realm = "nuswit.com"

    app = SampleApplication()
    dstack.registerApplication(app, 0, 4)
    dstack.registerApplication(app, 10415, 4)

    peer_listener = SamplePeerListener()
    dstack.registerPeerListener(peer_listener)

    dstack.registerPeerIO(SamplePeerIO())
    dstack.clientV4Add("192.168.214.81", 3868)

    tick = LoopingCall(dstack.tick)
    tick.start(1)
    reactor.run()

if __name__ == "__main__":
    main()
