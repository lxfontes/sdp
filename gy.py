#!/usr/bin/env python
import sys
from twisted.internet.protocol import Factory,Protocol
from twisted.internet import reactor,defer,threads
from twisted.python import log
import diameter.protocol
import diameter.dictionary

class DiameterApplication:
  def handleDWR(self,msg,reply):
    log.msg("sending DWA")
    reply.addInteger32('Result-Code',2001)


  def handleCER(self,msg,reply):
    log.msg("sending CEA")
    appId = msg.findAVP('Vendor-Specific-Application-Id')[0]
    reply.addAVP(appId)

    reply.addInteger32('Vendor-Id',11610)
    reply.addInteger32('Inband-Security-Id',0)
    reply.addInteger32('Result-Code',2001)
    reply.addOctetString('Product-Name','sdp')
    reply.addInteger32('Firmware-Revision',1)

  def handleCCRI(self,msg,reply):
    reply.addInteger32('Result-Code',2001)

  def handleCCRU(self,msg,reply):
    reply.addInteger32('Result-Code',2001)

#set session failover handling
    reply.addInteger32('CC-Session-Failover',0)

#get all All RG
    rgs = msg.findAVP('Multiple-Services-Credit-Control')
    for rg in rgs:
      rg.getGroup()
      response = msg.getAVP('Multiple-Services-Credit-Control')
#copy rg
      avp = rg.findAVP('Rating-Group')[0]
      response.addAVP(avp)

#check if something was consumed
      usu = rg.findAVP('Used-Service-Unit')
      if len(usu)>0:
        usu = usu[0]
        usu.getGroup()
        ccbytes = usu.findAVP('CC-Total-Octets')
        if len(ccbytes)>0:
          log.msg("Used bytes %d" % ccbytes[0].getInteger64())

        cctime = usu.findAVP('CC-Time')
        if len(cctime)>0:
          log.msg("Used time %d" % cctime[0].getInteger32())


#check if we need to give back something
      rsu = rg.findAVP('Requested-Service-Unit')
#ok, let's give some quota
      if len(rsu)>0:
        response.addInteger32('Result-Code',2001)

        gsu = msg.getAVP('Granted-Service-Unit')
#grant 512k
        gsu.addInteger64('CC-Total-Octets',long(512*1024))
        response.addAVP(gsu)
      reply.addAVP(response)


  def handleCCRT(self,msg,reply):
    reply.addInteger32('Result-Code',2001)

  def handleCCR(self,msg,reply):
    copyList = ('Session-Id','CC-Request-Type','CC-Request-Number','Auth-Application-Id')

    for i in copyList:
      avp = msg.findAVP(i)[0]
      reply.addAVP(avp)

    avp = msg.findAVP('CC-Request-Type')[0]
    requestType = avp.getInteger32()
    if requestType == 1:
      self.handleCCRI(msg,reply)
    elif requestType == 2:
      self.handleCCRU(msg,reply)
    elif requestType == 3:
      self.handleCCRT(msg,reply)


  def handle(self,msg,reply):
    if msg.command_code == 257:
      self.handleCER(msg,reply)
    elif msg.command_code == 280:
      self.handleDWR(msg,reply)
    elif msg.command_code == 272:
      self.handleCCR(msg,reply)

def main():
  log.startLogging(sys.stdout)
  factory = diameter.protocol.DiameterFactory(origin_host='primaryserver.sandvine.com',origin_realm='sandvine.com')
  factory.loadDictionary(4,"3gpp_32_299_v7_70.xml.sample")
  app = DiameterApplication()
  factory.setApplication(app)
  reactor.listenTCP(3868,factory)
  reactor.run()

if __name__ == "__main__":
	main()
