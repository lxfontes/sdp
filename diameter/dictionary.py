from xml.dom.minidom import parse, parseString

class DiameterAVPDef:
  def __init__(self):
    self.mandatory_flag = False
    self.protected_flag = False
    self.vendor_id = 0
    self.code = 0

class DiameterDictionary:
  def __init__(self,file):
    self.dom = parse(file)
    self.load()
  def load(self):
    """We only load avps for now"""
    self.name_to_def = {}
    self.def_to_name = {}
    
    vlist = self.dom.getElementsByTagName("vendor")
    vendors = {}
    for vendor in vlist:
      vendors[vendor.attributes['name'].value] = int(vendor.attributes['vendor-id'].value)
    avps = self.dom.getElementsByTagName("avp")
    for avp in avps:
      newAVP = DiameterAVPDef()
      if avp.attributes.has_key('mandatory') and avp.attributes['mandatory'].value == "must":
        newAVP.mandatory_flag=True
      if avp.attributes.has_key('protected') and avp.attributes['protected'].value == "must":
        newAVP.mandatory_flag=True
      newAVP.code = int(avp.attributes['code'].value)
      if avp.attributes.has_key('vendor-id'):
        newAVP.vendor_id = vendors[avp.attributes['vendor-id'].value]
      self.name_to_def[avp.attributes['name'].value] = newAVP
      self.def_to_name[(newAVP.vendor_id,newAVP.code)] = newAVP

  def getAVPCode(self,name):
    if self.name_to_def.has_key(name):
      df = self.name_to_def[name]
      return (df.code,df.vendor_id)
    else:
      return (0,0)

