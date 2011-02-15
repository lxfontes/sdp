
import ConfigParser
from twisted.python import log

CONFIG_RULES = [
      ["server","host","get"],
      ["server","port","getint"],
      ["server","realm","get"],
      ["server","name","get"],
      ["server","dictionary","get"],
      ["mongo","host","get"],
      ["mongo","port","getint"],
      ["mongo","db","get"],
      ["mongo","pool_size","getint"],
    ]

class _O(dict):
  """Makes a dictionary behave like an object."""
  def __getattr__(self, name):
    try:
      return self[name]
    except KeyError:
      return None
    #raise AttributeError(name)
  def __setattr__(self, name, value):
    self[name] = value

def parse_config(filename):
  config = {}
  cp = ConfigParser.RawConfigParser()
  cp.readfp(open(filename))

  for rule in CONFIG_RULES:
    section,option,method = rule
    key = "%s_%s" % (section,option)
    try:
      value = getattr(cp,method)(section,option)
    except Exception, e:
      log.err(e)
      raise Exception("Could not find config item: %s/%s" %(section,option))
    config[key] = value
  return _O(config)
