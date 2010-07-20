#!/usr/bin/env python
from twisted.internet.protocol import Factory,Protocol
from twisted.internet import reactor,defer
from diameter.parser import *


def test(msg = None):
	print("recebeu cmd %d" % msg.commandCode)
	avps = msg.findAVP(266)
	for avp in avps:
		print(avp)
		print(avp.getInteger())
	avp = msg.findAVP(260)[0]
	gavps = avp.getGroup()
	for avp in gavps:
		print(avp)
		print(avp.getInteger())
	reply = DiameterAnswer(msg)
	

def main():
	factory = DiameterFactory()
	d = defer.Deferred()
	d.addCallback(test)
	factory.setClientCallback(d)
	
	d = defer.Deferred()
	d.addCallback(test)
	factory.setMessageHandler(d)
	
	log.startLogging(sys.stdout)
	reactor.listenTCP(3868,factory)
	reactor.run()

if __name__ == "__main__":
	main()
