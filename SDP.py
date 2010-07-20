#!/usr/bin/env python
from twisted.internet.protocol import Factory,Protocol
from twisted.internet import reactor,defer
from twisted.python import log
from diameter.parser import *


class StackProtocol(DiameterProtocol):
	def processMessage(self,msg):
		print("recebeu cmd %d" % msg.commandCode)
		avps = msg.findAVP(266)
		for avp in avps:
			print(avp)
			print(avp.getInteger())
		reply = DiameterAnswer(msg)
		reply.addAVP(avp)
		log.msg("replying %d" % reply.messageLength)
		buf = reply.getWire()
		self.transport.write(buf)
		
	

def main():
	factory = DiameterFactory()
	factory.protocol = StackProtocol
	log.startLogging(sys.stdout)
	reactor.listenTCP(3868,factory)
	reactor.run()

if __name__ == "__main__":
	main()
