#!/usr/bin/env python
import sys
from twisted.internet.protocol import Factory,Protocol
from twisted.internet import reactor,defer,threads
from twisted.python import log
from diameter import parser,dictionary


class StackProtocol(parser.DiameterProtocol):

  def addOrigin(self,reply):
    dict = self.factory.settings['dictionary']

    avp = dict.getAVP('Origin-Host')
    avp.setOctetString(self.factory.settings['origin_host'])
    reply.addAVP(avp)

    avp = dict.getAVP('Origin-Realm')
    avp.setOctetString(self.factory.settings['origin_realm'])
    reply.addAVP(avp)

  def handleDWR(self,msg):
    dict = self.factory.settings['dictionary']
    reply = parser.DiameterAnswer(msg)
    self.addOrigin(reply)

    avp = dict.getAVP('Result-Code')
    avp.setInteger32(2001)
    reply.addAVP(avp)

    return reply

  def handleCER(self,msg):
    dict = self.factory.settings['dictionary']

    reply = parser.DiameterAnswer(msg)
    self.addOrigin(reply)
    appId = msg.findAVP(dict.getAVPCode('Vendor-Specific-Application-Id'))[0]
    reply.addAVP(appId)

    avp = dict.getAVP('Vendor-Id')
    avp.setInteger32(11610)
    reply.addAVP(avp)

    avp = dict.getAVP('Inband-Security-Id')
    avp.setInteger32(0)
    reply.addAVP(avp)

    avp = dict.getAVP('Result-Code')
    avp.setInteger32(2001)
    reply.addAVP(avp)

    avp = dict.getAVP('Product-Name')
    avp.setOctetString('sdp')
    reply.addAVP(avp)

    avp = dict.getAVP('Firmware-Revision')
    avp.setInteger32(1)
    reply.addAVP(avp)

    return reply

  def handleCCRI(self,msg,reply):
    dict = self.factory.settings['dictionary']
    avp = dict.getAVP('Result-Code')
    avp.setInteger32(2001)
    reply.addAVP(avp)

  def handleCCRU(self,msg,reply):
    dict = self.factory.settings['dictionary']
    avp = dict.getAVP('Result-Code')
    avp.setInteger32(2001)
    reply.addAVP(avp)

#set session failover handling
    avp = dict.getAVP('CC-Session-Failover')
    avp.setInteger32(0)
    reply.addAVP(avp)

#get all All RG
    rgs = msg.findAVP(dict.getAVPCode('Multiple-Services-Credit-Control'))
    for rg in rgs:
      rg.getGroup()
      response = dict.getAVP('Multiple-Services-Credit-Control')
#copy rg
      avp = rg.findAVP(dict.getAVPCode('Rating-Group'))[0]
      response.addAVP(avp)

#check if something was consumed
      usu = rg.findAVP(dict.getAVPCode('Used-Service-Unit'))
      if len(usu)>0:
        usu = usu[0]
        usu.getGroup()
        ccbytes = usu.findAVP(dict.getAVPCode('CC-Total-Octets'))
        if len(ccbytes)>0:
          print("Used bytes %d" % ccbytes[0].getInteger64())

        cctime = usu.findAVP(dict.getAVPCode('CC-Time'))
        if len(cctime)>0:
          print("Used time %d" % cctime[0].getInteger32())


#check if we need to give back something
      rsu = rg.findAVP(dict.getAVPCode('Requested-Service-Unit'))
#ok, let's give some quota
      if len(rsu)>0:
        avp = dict.getAVP('Result-Code')
        avp.setInteger32(2001)
        response.addAVP(avp)

        gsu = dict.getAVP('Granted-Service-Unit')
        cctotal = dict.getAVP('CC-Total-Octets')
#grant 512k
        cctotal.setInteger64(long(5*1024))
        gsu.addAVP(cctotal)
        response.addAVP(gsu)
      reply.addAVP(response)



  def handleCCRT(self,msg,reply):
    dict = self.factory.settings['dictionary']
    avp = dict.getAVP('Result-Code')
    avp.setInteger32(2001)
    reply.addAVP(avp)

  def handleCCR(self,msg):
    dict = self.factory.settings['dictionary']
    copyList = ('Session-Id','CC-Request-Type','CC-Request-Number','Auth-Application-Id')
    reply = parser.DiameterAnswer(msg)
    self.addOrigin(reply)

    for i in copyList:
      avp = msg.findAVP(dict.getAVPCode(i))[0]
      reply.addAVP(avp)

    avp = msg.findAVP(dict.getAVPCode('CC-Request-Type'))[0]
    requestType = avp.getInteger32()
    if requestType == 1:
      self.handleCCRI(msg,reply)
    elif requestType == 2:
      self.handleCCRU(msg,reply)
    elif requestType == 3:
      self.handleCCRT(msg,reply)

    return reply


  def receiveMessage(self,msg):
    if msg.commandCode == 257:
      reply = self.handleCER(msg)
    elif msg.commandCode == 280:
      reply = self.handleDWR(msg)
    elif msg.commandCode == 272:
      reply = self.handleCCR(msg)

    buf = reply.getWire()
    self.transport.write(buf)

def main():
  dict = dictionary.DiameterDictionary("3gpp_32_299_v7_70.xml.sample")
  print(dict.getAVPCode("Session-Id"))
  factory = parser.DiameterFactory(dictionary=dict,origin_host='primaryserver.sandvine.com',origin_realm='sandvine.com')
  factory.protocol = StackProtocol
  log.startLogging(sys.stdout)
  reactor.listenTCP(3868,factory)
  reactor.run()

if __name__ == "__main__":
	main()
