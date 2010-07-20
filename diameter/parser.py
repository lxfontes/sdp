from twisted.internet.protocol import Factory,Protocol
from twisted.internet import reactor
from twisted.python import log
import sys, warnings
import struct



class DiameterAVP:
	typeSize = 0
	avpSize = 0
	avpCode = 0
	#0x80
	avpVendor = 0
	avpData = ""
	avpGroup = []
	__groupOpen = False
	#0x60
	mandatoryFlag = False
	#0x40
	protectedFlag = False
	def __init__(self):
		pass
	
	def __str__(self):
		mflag = self.mandatoryFlag and "M" or "."
		vflag = self.avpVendor>0 and "V" or "."
		pflag = self.protectedFlag and "P" or "."
		return "code %d vendor %d size %d [%c%c%c]" % (self.avpCode,self.avpVendor,self.typeSize,vflag,mflag,pflag)

	def setMandatory(self,t):
		self.mandatoryFlag = t
	def setProtected(self,p):
		self.protectedFlag = p
	def setVendorAVP(self,code,vendor=0):
		self.avpCode = code
		self.avpVendor = vendor
		if vendor > 0:
			self.avpSize = 12
		else:
			self.avpSize = 8
		
	def setInteger(self,i):
		self.typeSize = 4
		self.avpData = struct.pack("!I",i)
	def getInteger(self):
		i = struct.unpack("!I",self.avpData)[0]
		return i
	
	def setOctetString(self,str):
		self.typeSize = len(str)
		self.avpData = str

	def getOctetString(self):
		return self.avpData

	def addAVP(self,avp):
		self.avpGroup.append(avp)
		self.typeSize += avp.getFinalSize()
		self.avpData += avp.getWire()

	def findAVP(self,code,vendor=0):
		retList = []
		if self.__groupOpen == False:
			self.getGroup()

		for avp in self.avpGroup:
			if avp.avpCode == code and avp.avpVendor == vendor:
				retList.append(avp)
		return retList


	def getGroup(self):
		if self.__groupOpen:
			return self.avpGroup
		i = 0
		while i < self.typeSize:
			avp = DiameterAVP()
			i += avp.parseFromBuffer(self.avpData,i)
			self.addAVP(avp)
		self.__groupOpen = True
		return self.avpGroup
	
	def getFinalSize(self):
		return self.avpSize + self.typeSize

	def getWire(self):
		buffers = ["","","",""]
		flags = 0
		
		if self.avpVendor > 0:
			flags |= 0x80
			buffers[1] = struct.pack("!I",self.avpVendor)
		if self.mandatoryFlag:
			flags |= 0x60
		if self.protectedFlag:
			flags |= 0x20
			
		fl = (flags << 24) | (self.getFinalSize())
        
		buffers[0] = struct.pack("!II",fl,self.avpCode)	
		buffers[2] = self.avpData
		
		#put padding in place
		length  = 4 - (self.typeSize % 4)
		for i in range(length,0,-1):
			buffers[3] += struct.pack("c","0")
			
		retVal = "".join(buffers)
		return retVal
		
	def parseFromBuffer(self,inBuf,index):
		cc,fl = struct.unpack("!II",inBuf[index:index+8])
		self.avpCode = cc
		flags = fl >> 24
		length = fl & 0x000000ff
		#skip header (length) 
		self.typeSize = length - 8
		if flags & 0x80:
			self.avpSize = 12
			self.avpVendor = struct.unpack("!I",inBuf[index+8:index+12])[0]
			self.typeSize -= 4
			self.avpData = inBuf[index + 12:index + 12 + self.typeSize]
		else:
			self.avpData = inBuf[index + 8:index + 8 + self.typeSize]
			self.avpSize = 8

		if flags & 0x60:
			self.mandatoryFlag = True
		if flags & 0x20:
			self.protectedFlag = True

		retLength  = ((self.avpSize+3)&~3)
		return retLength
        
class DiameterMessage:
	eTe = 0
	hBh = 0
	applicationId = 0
	commandCode = 0
	version = 1 
	#0x80
	requestFlag = False
	#0x40
	proxiableFlag = False
	#0x20
	errorFlag = False
	#0x10
	retransmitFlag = False
	messageLength = 20
	avpGroup = []
	def __init__(self):
		pass
		
	def getGroup(self):
		return self.avpGroup

	def findAVP(self,code,vendor=0):
		retList = []
		for avp in self.avpGroup:
			if avp.avpCode == code and avp.avpVendor == vendor:
				retList.append(avp)
		return retList
	
	def getWire(self):
		v_ml = (self.version<<24)|self.messageLength
		flags = 0
		if self.requestFlag:
			flags |= 0x80
		if self.proxiableFlag:
			flags |= 0x40
		if self.errorFlag:
			flags |= 0x20
		if self.retransmitFlag:
			flags |= 0x10
		f_code = (flags << 24) | self.commandCode
		buffers = [""]
		buffers[0] = struct.pack("!IIIII",v_ml,f_code,self.applicationId,self.hBh,self.eTe)
		for avp in self.avpGroup:
			buffers.append(avp.getWire())
		
		retVal = "".join(buffers)
		return retVal
		
	def parseFromBuffer(self,inBuf):
		v_ml,f_code,appId,hbh,ete = struct.unpack("!IIIII",inBuf[0:20])
		self.version = v_ml >> 24;
		self.messageLength =  (v_ml & 0x000000ff)		
		self.commandCode = f_code&0x00ffffff
		self.applicationId = appId
		self.eTe = ete
		self.hBh = hbh
		flags = f_code>>24
		if flags & 0x80:
			requestFlag = True
		if flags & 0x40:
			proxiableFlag = True	
		if flags & 0x20:
			errorFloag = True
		if flags & 0x10:
			retransmitFlag = True
		#parse the root avps
		i = 20
		while i < self.messageLength:
			avp = DiameterAVP()
			i += avp.parseFromBuffer(inBuf,i)
			self.avpGroup.append(avp)

	
	def addAVP(self,avp):
		self.avpGroup.append(avp)
		self.messageLength += avp.getFinalSize()

class DiameterProtocol(Protocol):
	incomingBuffer = ""
	receivedHeader = False
	incomingSize = 0
	
	def setup(self):
		self.receiveHeader = False
		self.incomingSize = 0
	
	
	#server setup
	def connectionMade(self):
		self.transport.write("hey\n")
			
	def getHeader(self):
		versionAndLength = struct.unpack("!I",self.incomingBuffer[0:4])[0]
		version = versionAndLength >> 24;
		length =  (versionAndLength & 0x000000ff)
		# hop by hop and end to end are set already
		#as per rfc 3588, version should be = 1
		if version != 1:
			self.transport.loseConnection()
			return
		self.incomingSize = length
		log.msg("Expecting %d bytes" % length)
		
	
	
	def getMessage(self):
		msg = DiameterMessage()
		msg.parseFromBuffer(self.incomingBuffer)
		self.incomingBuffer = self.incomingBuffer[self.incomingSize:]
		self.processMessage(msg)
		self.setup()
	
	def processIncomingBuffer(self):
		#20 = diameter header size (fixed)
		if len(self.incomingBuffer) < 20:
			return False
		else:
			if self.receivedHeader == False:
				self.getHeader()
				self.receivedHeader = True
		
		if self.receivedHeader == True and len(self.incomingBuffer) >= self.incomingSize:
			self.getMessage()
			self.receivedHeader = False
		return True
    
	def dataReceived(self,data):
		self.incomingBuffer += data
		
		while True:
			if self.processIncomingBuffer() == False:
				break
    
	def connectionLost(self,reason):
		pass
	
	def processMessage(self,msg):
		pass
	
	
class DiameterFactory(Factory):
	protocol = DiameterProtocol	
		
		
# helper functions
def DiameterAnswer(msg):
	reply = DiameterMessage()
	reply.requestFlag = False
	reply.proxiableFlag = msg.proxiableFlag
	reply.eTe = msg.eTe
	reply.hBh = msg.hBh
	reply.applicationId = msg.applicationId
	reply.commandCode = msg.commandCode
	return reply

