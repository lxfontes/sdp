#!/usr/bin/env python
from twisted.internet.protocol import Factory,Protocol
from twisted.internet import reactor,defer,threads
from twisted.python import log
from diameter.parser import *


class StackProtocol(DiameterProtocol):
	def receiveMessage(self,msg):
#		print("got cmd %d" % msg.commandCode)
		reply = DiameterAnswer(msg)
		
		if msg.commandCode == 257:
			appId = msg.findAVP(260)[0]
			reply.addAVP(appId)
			originIP = msg.findAVP(257)[0]
		elif msg.commandCode == 301:
			resultCode = DiameterAVP()
			resultCode.setVendorAVP(268)
			resultCode.setInteger(2001)
			reply.addAVP(resultCode)

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
