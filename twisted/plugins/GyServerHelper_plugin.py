#coding: utf-8

from zope.interface import implements
from twisted.python import usage
from twisted.plugin import IPlugin
from twisted.application import service, internet
from twisted.internet import protocol

from GyServer import util,server
import txredisapi

class Options(usage.Options):
  optParameters = [
      ["config","c","config/ocs.conf","configuration file"],
      ]


class ServiceMaker(object):
  implements(service.IServiceMaker, IPlugin)
  tapname = "GyServerHelper"
  description = "SV Lab Helper"
  options = Options

  def makeService(self,options):
    config = util.parse_config(options['config'])
    s = service.MultiService()
    redis = txredisapi.RedisConnectionPool(config.redis_host,
        config.redis_port,config.redis_pool_size)

    i = internet.TCPServer(config.server_port,
        server.Application(config,redis),interface=config.server_host)

    i.setServiceParent(s)

    return s

serviceMaker = ServiceMaker()
