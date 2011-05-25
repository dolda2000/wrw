import threading, time, pickle, random, os
import cookie

__all__ = ["db", "get"]

def hexencode(str):
    ret = ""
    for byte in str:
        ret += "%02X" % (ord(byte),)
    return ret

def gennonce(length):
    nonce = ""
    for i in xrange(length):
        nonce += chr(random.randint(0, 255))
    return nonce

class session(object):
    def __init__(self, expire = 86400 * 7):
        self.id = hexencode(gennonce(16))
        self.dict = {}
        self.lock = threading.Lock()
        self.ctime = self.atime = self.mtime = int(time.time())
        self.expire = expire
        self.dctl = set()
        self.dirtyp = False

    def dirty(self):
        for d in self.dctl:
            if d.sessdirty():
                return True
        return self.dirtyp

    def frozen(self):
        for d in self.dctl:
            d.sessfrozen()
        self.dirtyp = False

    def __getitem__(self, key):
        return self.dict[key]

    def get(self, key, default = None):
        return self.dict.get(key, default)

    def __setitem__(self, key, value):
        self.dict[key] = value
        if hasattr(value, "sessdirty"):
            self.dctl.add(value)
        else:
            self.dirtyp = True

    def __delitem__(self, key):
        old = self.dict.pop(key)
        if old in self.dctl:
            self.dctl.remove(old)
        self.dirtyp = True

    def __contains__(self, key):
        return key in self.dict

    def __getstate__(self):
        ret = []
        for k, v in self.__dict__.items():
            if k == "lock": continue
            ret.append((k, v))
        return ret
    
    def __setstate__(self, st):
        for k, v in st:
            self.__dict__[k] = v
        self.lock = threading.Lock()

class db(object):
    def __init__(self, cookiename = "wrwsess", path = "/"):
        self.live = {}
        self.cookiename = cookiename
        self.path = path
        self.lock = threading.Lock()
        self.lastuse = 0
        self.cthread = None
        self.freezetime = 3600

    def clean(self):
        now = int(time.time())
        with self.lock:
            dlist = []
            for sess in self.live.itervalues():
                if sess.atime + self.freezetime < now:
                    try:
                        if sess.dirty():
                            self.freeze(sess)
                    except:
                        if sess.atime + sess.expire < now:
                            dlist.append(sess)
                    else:
                        dlist.append(sess)
            for sess in dlist:
                del self.live[sess.id]

    def cleanloop(self):
        try:
            lastuse = self.lastuse
            while self.lastuse >= lastuse:
                lastuse = self.lastuse
                time.sleep(300)
                self.clean()
        finally:
            with self.lock:
                self.cthread = None

    def fetch(self, req):
        now = int(time.time())
        self.lastuse = now
        sessid = cookie.get(req, self.cookiename)
        with self.lock:
            if self.cthread is None:
                self.cthread = threading.Thread(target = self.cleanloop)
                self.cthread.setDaemon(True)
                self.cthread.start()
            try:
                if sessid is None:
                    raise KeyError()
                elif sessid in self.live:
                    sess = self.live[sessid]
                else:
                    sess = self.thaw(sessid)
                    self.live[sessid] = sess
                if sess.atime + sess.expire < now:
                    raise KeyError()
                sess.atime = now
            except KeyError:
                sess = session()
                self.live[sess.id] = sess
                req.oncommit(self.addcookie)
        req.oncommit(self.ckfreeze)
        return sess

    def addcookie(self, req):
        sess = req.item(self.fetch)
        cookie.add(req, self.cookiename, sess.id, self.path)

    def ckfreeze(self, req):
        sess = req.item(self.fetch)
        if sess.dirty():
            try:
                self.freeze(sess)
            except:
                pass

    def thaw(self, sessid):
        raise KeyError()

    def freeze(self, sess):
        raise TypeError()

class backeddb(db):
    def __init__(self, backdb, *args, **kw):
        super(backeddb, self).__init__(*args, **kw)
        self.backdb = backdb

    def thaw(self, sessid):
        data = self.backdb[sessid]
        try:
            return pickle.loads(data)
        except Exception, e:
            raise KeyError()

    def freeze(self, sess):
        self.backdb[sess.id] = pickle.dumps(sess)
        sess.frozen()

class dirback(object):
    def __init__(self, path):
        self.path = path

    def __getitem__(self, key):
        try:
            with open(os.path.join(self.path, key)) as inf:
                return inf.read()
        except IOError:
            raise KeyError(key)

    def __setitem__(self, key, value):
        if not os.path.exists(self.path):
            os.makedirs(self.path)
        with open(os.path.join(self.path, key), "w") as out:
            out.write(value)

default = backeddb(dirback(os.path.join("/tmp", "wrwsess-" + str(os.getuid()))))

def get(req):
    return req.item(default.fetch)
