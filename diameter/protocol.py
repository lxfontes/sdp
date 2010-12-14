from twisted.internet.protocol import Factory,Protocol
from twisted.internet import reactor
from twisted.python import log
from dictionary import DiameterDictionary
import sys, warnings
import socket
import struct

class DiameterAVP:
  def __init__(self,msg):
    self.msg = msg
    self.type_size = 0
    self.avp_size = 0
    self.avp_code = 0
    self.avp_vendor = 0
    self.avp_data = ""
    self.avp_group = []
    self.__groupOpen = False
    self.mandatory_flag = False
    self.protected_flag = False


  def __str__(self):
    mflag = self.mandatory_flag and "M" or "."
    vflag = self.avp_vendor>0 and "V" or "."
    pflag = self.protected_flag and "P" or "."
    return "code %d vendor %d size %d [%c%c%c]" % (self.avp_code,self.avp_vendor,self.type_size,vflag,mflag,pflag)

  def setMandatory(self,t):
    self.mandatory_flag = t
  def setProtected(self,p):
    self.protected_flag = p
  def setVendorAVP(self,code,vendor=0):
    self.avp_code = code
    self.avp_vendor = vendor
    if vendor > 0:
      self.avp_size = 12
    else:
      self.avp_size = 8

  def setInteger32(self,i):
    self.type_size = 4
    self.avp_data = struct.pack("!I",i)
  def getInteger32(self):
    i = struct.unpack("!I",self.avp_data)[0]
    return i

  def setInteger64(self,i):
    self.type_size = 8
    self.avp_data = struct.pack("!Q",i)
  def getInteger64(self):
    i = struct.unpack("!Q",self.avp_data)[0]
    return i

  def setOctetString(self,str):
    self.type_size = len(str)
    self.avp_data = str

  def getOctetString(self):
    return self.avp_data

  def getIPV4(self):
    return socket.inet_ntop(socket.AF_INET,self.avp_data[2:])

  def setIPV4(self,addr):
    address=socket.getaddrinfo(addr, 0)
    for a in address:
      if a[0]==socket.AF_INET:
        raw = socket.inet_pton(socket.AF_INET,a[4][0]);
        self.avp_data = struct.pack("!h4s",1,raw)
        # 2 = socket type, 4 = octects for ip
        self.type_size = 6

  def addInteger32(self,name,value):
    x = self.msg.getAVP(name)
    x.setInteger32(value)
    self.addAVP(x)

  def addInteger64(self,name,value):
    x = self.msg.getAVP(name)
    x.setInteger64(value)
    self.addAVP(x)

  def addOctetString(self,name,value):
    x = self.msg.getAVP(name)
    x.setOctetString(value)
    self.addAVP(x)

  def addIPV4(self,name,value):
    x = self.msg.getAVP(name)
    x.setIPV4(value)
    self.addAVP(x)

  def addAVP(self,avp):
    self.avp_group.append(avp)
    self.type_size += avp.getPaddedSize()
    self.avp_data += avp.getWire()

  def findAVP(self,name,vendor=0):
    retList = []
    t = self.msg.dictionary.getAVPCode(name)
    vendor = t[1]
    code = t[0]

    if self.__groupOpen == False:
      self.getGroup()

    for avp in self.avp_group:
      if avp.avp_code == code and avp.avp_vendor == vendor:
        retList.append(avp)
    return retList


  def getGroup(self):
    if self.__groupOpen:
      return self.avp_group
    i = 0
    while i < self.type_size:
      avp = DiameterAVP(self.msg)
      i += avp.parseFromBuffer(self.avp_data,i)
      self.avp_group.append(avp)
    self.__groupOpen = True
    return self.avp_group

  def getFinalSize(self):
    return self.avp_size + self.type_size


  def getPaddedSize(self):
    length  = ((self.getFinalSize()+3)&~3)
    return length

  def getWire(self):
    buffers = ["","","",""]
    flags = 0

    if self.avp_vendor > 0:
      flags |= 0x80
      buffers[1] = struct.pack("!I",self.avp_vendor)
    if self.mandatory_flag:
      flags |= 0x40
    if self.protected_flag:
      flags |= 0x20

    fl = (flags << 24) | (self.getFinalSize())

    buffers[0] = struct.pack("!II",self.avp_code,fl)	
    buffers[2] = self.avp_data

    #put padding in place
    length  = self.getPaddedSize() - self.getFinalSize()
    for i in range(length,0,-1):
      buffers[3] += struct.pack("b",0)

    retVal = "".join(buffers)
    return retVal

  def parseFromBuffer(self,inBuf,index):
    cc,fl = struct.unpack("!II",inBuf[index:index+8])
    self.avp_code = cc
    flags = fl >> 24
    length = fl & 0x00ffffff
    #skip header (length) 
    self.type_size = length - 8
    if flags & 0x80:
      self.avp_size = 12
      self.avp_vendor = struct.unpack("!I",inBuf[index+8:index+12])[0]
      self.type_size -= 4
      self.avp_data = inBuf[index + 12:index + 12 + self.type_size]
    else:
      self.avp_data = inBuf[index + 8:index + 8 + self.type_size]
      self.avp_size = 8

    if flags & 0x60:
      self.mandatory_flag = True
    if flags & 0x20:
      self.protected_flag = True

    retLength  = ((self.type_size+3)&~3) + self.avp_size
    return retLength

class DiameterMessage:
  def __init__(self):
    self.dictionary = None
    self.eTe = 0
    self.hBh = 0
    self.application_id = 0
    self.command_code = 0
    self.version = 1
    self.request_flag = False
    self.proxiable_flag = False
    self.error_flag = False
    self.retransmit_flag = False
    self.message_length = 20
    self.avp_group = []

  def setDict(self,d):
    self.dictionary = d

  def getAVP(self,name):
    avp = DiameterAVP(self)
    if self.dictionary.name_to_def.has_key(name):
      df = self.dictionary.name_to_def[name]
      avp.setVendorAVP(df.code,df.vendor_id)
      avp.setMandatory(df.mandatory_flag)
      avp.setProtected(df.protected_flag)
    return avp

  def getGroup(self):
    return self.avp_group

  def findAVP(self,name,vendor=0):
    retList = []

    t = self.dictionary.getAVPCode(name)
    vendor = t[1]
    code = t[0]

    for avp in self.avp_group:
      if avp.avp_code == code and avp.avp_vendor == vendor:
        retList.append(avp)
    return retList

  def getWire(self):
    v_ml = (self.version<<24)|self.message_length
    flags = 0
    if self.request_flag:
      flags |= 0x80
    if self.proxiable_flag:
      flags |= 0x40
    if self.error_flag:
      flags |= 0x20
    if self.retransmit_flag:
      flags |= 0x10
    f_code = (flags << 24) | self.command_code
    buffers = [""]
    buffers[0] = struct.pack("!IIIII",v_ml,f_code,self.application_id,self.hBh,self.eTe)
    for avp in self.avp_group:
      buffers.append(avp.getWire())

    retVal = "".join(buffers)
    return retVal

  def parseFromBuffer(self,inBuf):
    v_ml,f_code,appId,hbh,ete = struct.unpack("!IIIII",inBuf[0:20])
    self.version = v_ml >> 24;
    self.message_length =  (v_ml & 0x00ffffff)		
    self.command_code = f_code&0x00ffffff
    self.application_id = appId
    self.eTe = ete
    self.hBh = hbh
    flags = f_code>>24
    if flags & 0x80:
      self.request_flag = True
    if flags & 0x40:
      self.proxiable_flag = True
    if flags & 0x20:
      self.error_flag = True
    if flags & 0x10:
      self.retransmit_flag = True
    #parse the root avps
    i = 20
    while i < self.message_length:
      avp = DiameterAVP(self)
      i += avp.parseFromBuffer(inBuf,i)
      self.avp_group.append(avp)

  def addInteger32(self,name,value):
    x = self.getAVP(name)
    x.setInteger32(value)
    self.addAVP(x)

  def addInteger64(self,name,value):
    x = self.getAVP(name)
    x.setInteger64(value)
    self.addAVP(x)

  def addOctetString(self,name,value):
    x = self.getAVP(name)
    x.setOctetString(value)
    self.addAVP(x)

  def addIPV4(self,name,value):
    x = self.getAVP(name)
    x.setIPV4(value)
    self.addAVP(x)


  def addAVP(self,avp):
    self.avp_group.append(avp)
    self.message_length += avp.getPaddedSize()


class DiameterBaseProtocol(Protocol):
  def __init__(self):
    self.incoming_buffer = ""
    self.received_header = False
    self.incoming_size = 0

  def setup(self):
    self.received_header = False
    self.incoming_buffer = self.incoming_buffer[self.incoming_size:]
    self.incoming_size = 0

#server setup
  def connectionMade(self):
    pass

  def getHeader(self):
    vv = struct.unpack("c",self.incoming_buffer[:1])[0]

    version_length = struct.unpack("!i",self.incoming_buffer[:4])[0]
    version = version_length >> 24
    length = (version_length & 0x00ffffff)
    if version != 1:
      log.msg("Version should be 1")
      self.transport.loseConnection()
      return
    self.incoming_size = length
    self.received_header = True

  def getMessage(self):
    msg = DiameterMessage()
    msg.parseFromBuffer(self.incoming_buffer)
    self.receiveMessage(msg)
    self.setup()

#20 = diameter header size
  def processIncomingBuffer(self):
    if len(self.incoming_buffer) < 20:
      return False
    else:
      if self.received_header == False:
        self.getHeader()

    if self.received_header == True and len(self.incoming_buffer) >= self.incoming_size:
      self.getMessage()
    return True

  def dataReceived(self,data):
    self.incoming_buffer += data

    while True:
      if self.processIncomingBuffer() == False:
        return

  def connectionLost(self,reason):
    pass


  def addOrigin(self,msg):
    avp = msg.getAVP('Origin-Host')
    avp.setOctetString(self.factory.settings['origin_host'])
    msg.addAVP(avp)
    avp = msg.getAVP('Origin-Realm')
    avp.setOctetString(self.factory.settings['origin_realm'])
    msg.addAVP(avp)


  def receiveMessage(self,msg):
    if self.factory.dictionaries.has_key(msg.application_id):
      msg.setDict(self.factory.dictionaries[msg.application_id])
    else:
      msg.setDict(next(self.factory.dictionaries.itervalues()))
    reply = DiameterAnswer(msg)
    self.addOrigin(reply)
    self.factory.application.handle(msg,reply)
    buf = reply.getWire()
    self.transport.write(buf)


class DiameterFactory(Factory):
  protocol = DiameterBaseProtocol

  def __init__(self,**settings):
    self.settings = settings
    self.application = None
    self.dictionaries = {}
  def setApplication(self,app):
    self.application = app

  def loadDictionary(self,application_id,file_name):
    self.dictionaries[application_id] = DiameterDictionary(file_name)


# helper functions
def DiameterAnswer(msg):
  reply = DiameterMessage()
  reply.request_flag = False
  reply.proxiable_flag = msg.proxiable_flag
  reply.eTe = msg.eTe
  reply.hBh = msg.hBh
  reply.application_id = msg.application_id
  reply.command_code = msg.command_code
  reply.setDict(msg.dictionary)
  return reply


