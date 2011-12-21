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
            while True:
                time.sleep(300)
                self.clean()
                if len(self.live) == 0:
                    break
        finally:
            with self.lock:
                self.cthread = None

    def fetch(self, req):
        now = int(time.time())
        sessid = cookie.get(req, self.cookiename)
        new = False
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
                new = True

        def ckfreeze(req):
            if sess.dirty():
                if new:
                    cookie.add(req, self.cookiename, sess.id, self.path)
                    with self.lock:
                        self.live[sess.id] = sess
                try:
                    self.freeze(sess)
                except:
                    pass
        req.oncommit(ckfreeze)
        return sess

    def thaw(self, sessid):
        raise KeyError()

    def freeze(self, sess):
        raise TypeError()

    def get(self, req):
        return req.item(self.fetch)

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
    return default.get(req)
