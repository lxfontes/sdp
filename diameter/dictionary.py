from xml.dom.minidom import parse, parseString
import diameter

class DiameterAVPDef:
  def __init__(self):
    self.mandatory_flag = False
    self.protected_flag = False
    self.vendor_id = 0
    self.code = 0
    self.enum_names = {}
    self.enum_vals = {}

  def addEnum(self, name, val):
    self.enum_names[name] = int(val)
    self.enum_vals[int(val)] = name

  def getEnumValue(self, name):
    if self.enum_names.has_key(name):
        return self.enum_names[name]
    else:
        return 0

  def getEnumName(self, code):
    if self.enum_vals.has_key(code):
        return self.enum_vals[code]
    else:
        return 0


class DiameterDictionary:
  def __init__(self,file):
    self.dom = parse(file)
    self.load()
  def load(self):
    """We only load avps for now
    Add vendors and commands"""
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
      #parse enums
      enums = avp.getElementsByTagName("enum")
      for e in enums:
          newAVP.addEnum(e.attributes['name'].value, e.attributes['code'].value)
      self.name_to_def[avp.attributes['name'].value] = newAVP
      self.def_to_name[(newAVP.vendor_id,newAVP.code)] = newAVP

  def getEnumCode(self, avp, name):
      d = self.getAVPDefinition(avp)
      return d.getEnumValue(name)

  def getEnumName(self, avp, code):
      d = self.getAVPDefinition(avp)
      return d.getEnumName(code)
      pass

  def getAVPDefinition(self, name):
    if self.name_to_def.has_key(name):
      return self.name_to_def[name]
    else:
      return None

  def getAVPCode(self,name):
      avp_def = self.getAVPDefinition(name)
      if avp_def == None:
          avp_def = DiameterAVPDef()
      return (avp_def.code,avp_def.vendor_id)

  def getAVP(self, name):
      avp_def = self.getAVPDefinition(name)
      if avp_def == None:
          avp_def = DiameterAVPDef()
      ret = diameter.protocol.DiameterAVP()
      ret.avp_code = avp_def.code
      ret.avp_vendor = avp_def.vendor_id
      ret.mandatory_flag = avp_def.mandatory_flag
      ret.protected_flag = avp_def.protected_flag
      return ret


