from dictionary import DiameterDictionary
import sys, warnings
import socket
import struct
import time

class DiameterAVP:
  def __init__(self):
    self.type_size = 0
    self.avp_size = 8
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

  def setCode(self,code):
    self.avp_code = code

  def setVendor(self, vendor):
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

  def addAVP(self,avp):
    self.avp_group.append(avp)
    self.type_size += avp.getPaddedSize()
    self.avp_data += avp.getWire()


  def findFirstAVP(self, code, vendor=0):
    r = self.findAVP(code, vendor)
    if len(r) > 0:
        return r[0]
    else:
        return None

  def findAVP(self,code, vendor=0):
    retList = []

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
      avp = DiameterAVP()
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
    buffers = [r'',r'',r'',r'']
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

    retVal = r''.join(buffers)
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
    self.eTe = 0
    self.hBh = 0
    self.application_id = 0
    self.command_code = 0
    self.version = 1
    self.request_flag = False
    self.proxiable_flag = False
    self.error_flag = False
    self.retransmit_flag = False
# minimum header size
    self.message_length = 20
    self.avp_group = []

    self.retries = 0
    self.last_try = 0

  def getGroup(self):
    return self.avp_group

  def findFirstAVP(self, code, vendor=0):
    r = self.findAVP(code, vendor)
    if len(r) > 0:
        return r[0]
    else:
        return None

  def findAVP(self, code, vendor=0):
    retList = []

    for avp in self.avp_group:
      if avp.avp_code == code and avp.avp_vendor == vendor:
        retList.append(avp)
    return retList

  def getWire(self):
    if self.retries > 0:
        self.retransmit_flag = True
    self.retries += 1
    self.last_retry = int(time.time())

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
    buffers = [r'']
    buffers[0] = struct.pack("!IIIII",v_ml,f_code,self.application_id,self.hBh,self.eTe)
    for avp in self.avp_group:
      buffers.append(avp.getWire())

    retVal = r''.join(buffers)
    return retVal

  def parseFromBuffer(self,inBuf):
    v_ml = struct.unpack("!I",inBuf[0:4])[0]
    f_code = struct.unpack("!I",inBuf[4:8])[0]
    appId = struct.unpack("!I",inBuf[8:12])[0]
    hbh = struct.unpack("!I",inBuf[12:16])[0]
    ete = struct.unpack("!I",inBuf[16:20])[0]

    self.version = v_ml >> 24;
    self.message_length =  (v_ml & 0x00ffffff)
    self.command_code = f_code & 0x00ffffff
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
      avp = DiameterAVP()
      i += avp.parseFromBuffer(inBuf,i)
      self.avp_group.append(avp)
    return self.message_length

  def addAVP(self,avp):
    self.avp_group.append(avp)
    self.message_length += avp.getPaddedSize()

  def createAnswer(self):
    reply = DiameterMessage()
    reply.request_flag = False
    reply.proxiable_flag = self.proxiable_flag
    reply.eTe = self.eTe
    reply.hBh = self.hBh
    reply.application_id = self.application_id
    reply.command_code = self.command_code
    return reply


