import sys
from twisted.internet.protocol import Factory,Protocol
from twisted.internet import reactor,defer,threads
from twisted.python import log
from diameter import protocol,dictionary

class DiameterApplication:
  def handleDWR(self,msg,reply):
    reply.addInteger32('Result-Code',2001)


  def handleCER(self,msg,reply):
    log.msg("sending CEA to %s:%s" % (msg.findAVP('Origin-Host')[0].getOctetString(),
                                      msg.findAVP('Origin-Realm')[0].getOctetString()) )
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
    rules = ['Gold','Shape']
    for rule in rules:
      gavp = msg.getAVP("Charging-Rule-Install")
      gavp.addOctetString("Charging-Rule-Name",rule)
      reply.addAVP(gavp)

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

class Application(protocol.DiameterFactory):
  def __init__(self,config,redis):
    protocol.DiameterFactory.__init__(self,origin_host=config.server_name,origin_realm=config.server_realm)
    self.loadDictionary(16777238,config.server_dictionary)
    app = DiameterApplication()
    self.setApplication(app)

