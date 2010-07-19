from twisted.internet.protocol import Factory,Protocol
from twisted.python import log
import sys, warnings
import struct


class DiameterAVP:
	typeSize = 0
	avpSize = 0
	avpCode = 0
	#0x80
	avpVendor = 0
	avpData = None
	avpGroup = []
	#0x60
	mandatoryFlag = False
	#0x40
	protectedFlag = False
	def __init__(self):
		pass
	
	def __str__(self):
		if self.mandatoryFlag:
			mflag = "M"
		else:
			mflag = "."
		
		if self.avpVendor > 0:
			vflag = "V"
		else:
			vflag = "."
		
		if self.protectedFlag:
			pflag = "P"
		else:
			pflag = "."
		return "code %d vendor %d size %d [%c%c%c]" % (self.avpCode,self.avpVendor,self.typeSize,vflag,mflag,pflag)

	def setMandatory(self,t):
		self.mandatoryFlag = t
	def setProtected(self,p):
		self.protectedFlag = p
	def setVendorAVP(self,code,vendor=0):
		self.avpCode = code
		self.avpVendor = vendor
		
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

	def findAVP(self,code,vendor=0):
		retList = []
		for avp in self.avpGroup:
			if avp.avpCode == code and avp.avpVendor == vendor:
				retList.append(avp)
		return retList


	def getGroup(self):
		i = 0
		while i < self.typeSize:
			avp = DiameterAVP()
			i += avp.parseFromBuffer(self.avpData,i)
			self.addAVP(avp)
		
		
		
	def parseFromBuffer(self,inBuf,index):
		cc,fl = struct.unpack("!II",inBuf[index:index+8])
		self.avpCode = cc
		flags = fl >> 24
		length = fl & 0x000000ff
		self.avpSize = length
		#skip header (length) 
		self.typeSize = length - 8
		if flags & 0x80:
			self.avpVendor = struct.unpack("!I",inBuf[index+8:index+12])[0]
			self.typeSize -= 4
			self.avpData = inBuf[index + 12:index + 12 + self.typeSize]
		else:
			self.avpData = inBuf[index + 8:index + 8 + self.typeSize]

		if flags & 0x60:
			self.mandatoryFlag = True
		if flags & 0x40:
			self.protectedFlag = True

		retLength  = ((self.avpSize+3)&~3)
		return retLength
        
class DiameterMessage:
	eTe = 0
	hBh = 0
	applicationId = 0
	commandCode = 0
	version = 0 
	#0x80
	requestFlag = False
	#0x40
	proxiableFlag = False
	#0x20
	errorFlag = False
	#0x10
	retransmitFlag = False
	messageLength = 0
	avpGroup = []
	def __init__(self):
		pass
		
	def findAVP(self,code,vendor=0):
		retList = []
		for avp in self.avpGroup:
			if avp.avpCode == code and avp.avpVendor == vendor:
				retList.append(avp)
		return retList
				
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
			self.addAVP(avp)

		
	def addAVP(self,avp):
		self.avpGroup.append(avp)

class DiameterDecoder(Protocol):
	incomingBuffer = ""
	receivedHeader = False
	incomingSize = 0
	
	def setup(self):
		self.incomingBuffer = ""
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
		self.factory.handleMessage(msg)
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
		print("died..")
	
	
class DiameterFactory(Factory):
	protocol = DiameterDecoder
	clientInitCallback = None
	messageHandler = None
	
	def setClientCallback(self,d):
		self.clientInitCallback = d
	
	def setMessageHandler(self,d):
		self.messageHandler = d
	
	def getClientCallback(self):
		return self.clientInitCallback
	
	def getServerInitCallback(self):
		return self.serverInitCallback
	
	def handleMessage(self,msg):
		self.messageHandler.callback(msg)
	
		
		