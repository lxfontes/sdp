#!/usr/bin/env python
import sys
from twisted.internet.protocol import Factory,Protocol
from twisted.internet import reactor,defer,threads
from twisted.python import log
from diameter import parser,dictionary


class StackProtocol(parser.DiameterProtocol):

  def addOrigin(self,reply):
    dict = self.factory.settings['dictGy']

    avp = dict.getAVP('Origin-Host')
    avp.setOctetString(self.factory.settings['origin_host'])
    reply.addAVP(avp)

    avp = dict.getAVP('Origin-Realm')
    avp.setOctetString(self.factory.settings['origin_realm'])
    reply.addAVP(avp)

  def handleCER(self,msg):
    reply = parser.DiameterAnswer(msg)
    self.addOrigin(reply)
    appId = msg.findAVP(260)[0]
    reply.addAVP(appId)
    originIP = msg.findAVP(257)[0]
    return reply

  def handleCCR(self,msg):
    reply = parser.DiameterAnswer(msg)
    self.addOrigin(reply)
    dict = self.factory.settings['dictGy']
    avp = dict.getAVP('Session-Id')
    avp.setOctetString('testing')
    reply.addAVP(avp)
    return reply


  def receiveMessage(self,msg):
    print("got cmd %d" % msg.commandCode)

    if msg.commandCode == 257:
      reply = self.handleCER(msg)
    elif msg.commandCode == 271:
      reply = self.handleCCR(msg)

    buf = reply.getWire()
    self.transport.write(buf)

def main():
  dictGy = dictionary.DiameterDictionary("3gpp_32_299_v7_70.xml.sample")
  factory = parser.DiameterFactory(dictGy=dictGy,origin_host='lxfontes',origin_realm='l3f.org')
  factory.protocol = StackProtocol
  log.startLogging(sys.stdout)
  reactor.listenTCP(3868,factory)
  reactor.run()

if __name__ == "__main__":
	main()
