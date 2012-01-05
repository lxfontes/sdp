from diameter.protocol import DiameterMessage, DiameterAVP
import struct

class PeerStateMachine:
    # starts 'sending' CER
    PEER_CLIENT = 0
    # starts 'waiting' for CER
    PEER_SERVER = 1
    # just accepts connections
    PEER_LISTEN = 2
    def __init__(self, peer, peer_type):
        self.peer = peer
        self.stack = peer.stack
        if peer_type == PeerStateMachine.PEER_CLIENT:
            self.run = self.send_cer
        elif peer_type == PeerStateMachine.PEER_SERVER:
            self.run = self.receive_cer
        elif peer_type == PeerStateMachine.PEER_LISTEN:
            self.run = None

    def send_cer(self, consumed, message):
        msg = self.stack.createRequest(0, 257)
        #vendorid
        tmp = DiameterAVP()
        tmp.setCode(266)
        tmp.setMandatory(True)
        tmp.setInteger32(self.stack.vendor_id)
        msg.addAVP(tmp)

        #productname
        tmp = DiameterAVP()
        tmp.setCode(269)
        tmp.setMandatory(True)
        tmp.setOctetString(self.stack.product_name)
        msg.addAVP(tmp)

        #firmware
        tmp = DiameterAVP()
        tmp.setCode(267)
        tmp.setMandatory(True)
        tmp.setInteger32(self.stack.firmware_revision)
        msg.addAVP(tmp)

        #host ip
        tmp = DiameterAVP()
        tmp.setCode(257)
        tmp.setMandatory(True)
        tmp.setIPV4(self.stack.ip4_address)
        msg.addAVP(tmp)

        #get applications from stack
        apps = self.stack.applications.keys()
        for app in apps:
            #acct
            acc = DiameterAVP()
            acc.setCode(259)
            acc.setMandatory(True)
            acc.setInteger32(app[1])
            #auth
            auth = DiameterAVP()
            auth.setCode(258)
            auth.setMandatory(True)
            auth.setInteger32(app[1])

            if app[0]:
                tmp = DiameterAVP()
                tmp.setCode(260)
                tmp.setMandatory(True)
                #vendor
                v = DiameterAVP()
                v.setCode(266)
                v.setMandatory(True)
                v.setInteger32(app[0])
                tmp.addAVP(v)
                tmp.addAVP(auth)
                tmp.addAVP(acc)
                msg.addAVP(tmp)
                msg.addAVP(v)
            else:
                msg.addAVP(auth)
                msg.addAVP(acc)

        self.stack.sendByPeer(self.peer, msg, False)

        self.run = self.receive_cea

    def receive_cea(self, consumed, message):

        #check Result-Code
        tmp = message.findFirstAVP(268)
        # missing result code!
        if tmp == None:
            pass

        result = tmp.getInteger32()

        # register peer!
        if result == 2001:
            tmp = message.findFirstAVP(264)
            if tmp == None:
                pass
            identity = tmp.getOctetString()

            tmp = message.findFirstAVP(296)
            if tmp == None:
                pass
            realm = tmp.getOctetString()

            apps = dict()
            tmp = message.findAVP(258)
            for auth in apps:
                v = auth.getInteger32()
                if not apps.has_key((0,v)):
                    apps[(0,v)] = True

            tmp = message.findAVP(259)
            for acct in apps:
                v = acct.getInteger32()
                if not apps.has_key((0,v)):
                    apps[(0,v)] = True

            vtmp = message.findAVP(260)
            for vendor in vtmp:
                vid = vendor.findFirstAVP(266).getInteger32()
                acct = vendor.findFirstAVP(259)
                auth = vendor.findFirstAVP(258)
                tmp = message.findAVP(259)

                if auth and not apps.has_key((vid,auth.getInteger32())):
                    apps[(vid,auth.getInteger32())] = True
                if acct and not apps.has_key((vid,acct.getInteger32())):
                    apps[(vid,acct.getInteger32())] = True

            if self.stack.registerPeer(self.peer, identity, realm, apps):
                self.run = self.app_handler


    def app_handler(self, consumed, message):
        """
        Watch out for application-Id 0
        DPR/DWR will also show up in here
        """

        print("app_handler %d %d" % (message.application_id,message.command_code))
        print("length %d" % message.message_length)
        #watchdog, don't send it up the stack
        if message.application_id == 0 and \
           message.command_code == 280:
            if message.request_flag:
                answ = message.createAnswer()
                tmp = DiameterAVP()
                tmp.setCode(268)
                tmp.setMandatory(True)
                tmp.setInteger32(2001)
                answ.addAVP(tmp)
                self.stack.sendByPeer(self.peer, answ, False)
            return

        self.stack.handleIncomingMessage(self.peer, message)


    def receive_cer(self, consumed, message):
        pass

class Peer:
    def __init__(self, manager, peer_type):
        self.applications = None
        self.manager = manager
        self.stack = manager.stack
        self.identity = None
        self.realm = None
        self.last_watchdog = None
        self.next_tick = None
        self.state = None
        self.ipv4 = None
        self.port = None
        self.peer_type = peer_type
        self.fsm = PeerStateMachine(self, peer_type)
        pass

    def feed(self, buf, length):
        """Returns the amount of bytes consumed from buf"""

        # special signal, send it up the stack
        if length == 0:
            self.fsm.run(0, None)
            return 0

        # read error, disconnect
        if length == -1:
            self.fsm.run(-1, None)
            return -1

        # dont have an entire diameter header yet
        if length < 20:
            return 0

        version_length = struct.unpack("!i",buf[:4])[0]
        version = version_length >> 24
        msg_length = (version_length & 0x00ffffff)

        # protocol error, disconnect
        if version != 1:
            pass

        # can't read one entire message
        # caller should buffer
        if msg_length > length:
            return 0

        msg = DiameterMessage()
        consumed = msg.parseFromBuffer(buf)
        self.fsm.run(consumed, msg)

        # protocol error, disconnect
        if consumed <= 0:
            pass

        return consumed


    def destroy(self):
        pass


class Realm:
    def __init__(self):
        self.name = None
        self.applications = dict()
        self.identities = dict()

    def addPeer(self, peer, identity, apps):
        """Add identity, add application"""
        if self.identities.has_key(identity):
            return False

        self.identities[identity] = peer

        for app in apps:
            if self.applications.has_key(app):
                appentry = self.applications[app]
            else:
                appentry = list()
                self.applications[app] = appentry
            appentry.append(peer)
        return True

class PeerIOCallbacks:
    def __init__(self):
        pass
    def connectV4(self, peer, host, port):
        pass
    def listenV4(self, peer, host, port):
        pass
    def close(self, peer):
        pass

    def write(self, peer, data, length):
        pass

class PeerManager:
    def __init__(self, stack):
        self.stack = stack
        self.realms = dict()
        self.peers = list()
        self.io_cb = PeerIOCallbacks()

    def clientV4Add(self, host, port):
        peer = Peer(self, PeerStateMachine.PEER_CLIENT)
        return self.io_cb.connectV4(peer, host, port)

    def serverV4Add(self, host, port):
        peer = Peer(self, PeerStateMachine.PEER_LISTEN)
        return self.io_cb.listenV4(peer, host, port)

    def serverV4Accept(self, peer, host, port):
        client_peer = Peer(self, PeerStateMachine.PEER_SERVER)
        return client_peer

    def registerPeerIO(self, pio):
        self.io_cb = pio

    def send(self, peer, message):
        wire = message.getWire()
        self.io_cb.write(peer, wire, len(wire))

    def registerPeer(self, peer, identity, realm, apps):
        peer.identity = identity
        peer.realm = realm
        peer.applications = apps
        if self.realms.has_key(realm):
            prealm = self.realms[realm]
        else:
            prealm = Realm()
            prealm.name = realm
            self.realms[prealm.name] = prealm

        return prealm.addPeer(peer, identity, apps)
