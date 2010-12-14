from xml.dom.minidom import parse, parseString
from parser import DiameterAVP

class DiameterAVPDef:
  def __init__(self):
    self.mandatoryFlag = False
    self.protectedFlag = False
    self.vendorId = 0
    self.code = 0

class DiameterDictionary:
  def __init__(self,file):
    self.dom = parse(file)
    self.load()
  def load(self):
    """We only load avps for now"""
    self.nameToDef = {}
    self.defToName = {}
    
    vlist = self.dom.getElementsByTagName("vendor")
    vendors = {}
    for vendor in vlist:
      vendors[vendor.attributes['name'].value] = int(vendor.attributes['vendor-id'].value)
    avps = self.dom.getElementsByTagName("avp")
    for avp in avps:
      newAVP = DiameterAVPDef()
      if avp.attributes.has_key('mandatory') and avp.attributes['mandatory'].value == "must":
        newAVP.mandatoryFlag=True
      if avp.attributes.has_key('protected') and avp.attributes['protected'].value == "must":
        newAVP.mandatoryFlag=True
      newAVP.code = int(avp.attributes['code'].value)
      if avp.attributes.has_key('vendor-id'):
        newAVP.vendorId = vendors[avp.attributes['vendor-id'].value]
      self.nameToDef[avp.attributes['name'].value] = newAVP
      self.defToName[(newAVP.vendorId,newAVP.code)] = newAVP

  def getAVPCode(self,name):
    if self.nameToDef.has_key(name):
      df = self.nameToDef[name]
      return (df.code,df.vendorId)
    else:
      return (0,0)

  def getAVP(self,name):
    avp = DiameterAVP()
    if self.nameToDef.has_key(name):
      df = self.nameToDef[name]
      avp.setVendorAVP(df.code,df.vendorId)
      avp.setMandatory(df.mandatoryFlag)
      avp.setProtected(df.protectedFlag)
    return avp
