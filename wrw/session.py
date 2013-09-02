import threading, time, pickle, random, os
from . import cookie, env

__all__ = ["db", "get"]

def hexencode(str):
    ret = ""
    for byte in str:
        ret += "%02X" % (ord(byte),)
    return ret

def gennonce(length):
    nonce = ""
    for i in range(length):
        nonce += chr(random.randint(0, 255))
    return nonce

class session(object):
    def __init__(self, lock, expire=86400 * 7):
        self.id = hexencode(gennonce(16))
        self.dict = {}
        self.lock = lock
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

    def get(self, key, default=None):
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
        # The proper lock is set by the thawer

    def __repr__(self):
        return "<session %s>" % self.id

class db(object):
    def __init__(self, backdb=None, cookiename="wrwsess", path="/"):
        self.live = {}
        self.cookiename = cookiename
        self.path = path
        self.lock = threading.Lock()
        self.cthread = None
        self.freezetime = 3600
        self.backdb = backdb

    def clean(self):
        now = int(time.time())
        with self.lock:
            clist = list(self.live.keys())
        for sessid in clist:
            with self.lock:
                try:
                    entry = self.live[sessid]
                except KeyError:
                    continue
            with entry[0]:
                rm = False
                if entry[1] == "retired":
                    pass
                elif entry[1] is None:
                    pass
                else:
                    sess = entry[1]
                    if sess.atime + self.freezetime < now:
                        try:
                            if sess.dirty():
                                self.freeze(sess)
                        except:
                            if sess.atime + sess.expire < now:
                                rm = True
                        else:
                            rm = True
                if rm:
                    entry[1] = "retired"
                    with self.lock:
                        del self.live[sessid]

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

    def _fetch(self, sessid):
        while True:
            now = int(time.time())
            with self.lock:
                if sessid in self.live:
                    entry = self.live[sessid]
                else:
                    entry = self.live[sessid] = [threading.RLock(), None]
            with entry[0]:
                if isinstance(entry[1], session):
                    entry[1].atime = now
                    return entry[1]
                elif entry[1] == "retired":
                    continue
                elif entry[1] is None:
                    try:
                        thawed = self.thaw(sessid)
                        if thawed.atime + thawed.expire < now:
                            raise KeyError()
                        thawed.lock = entry[0]
                        thawed.atime = now
                        entry[1] = thawed
                        return thawed
                    finally:
                        if entry[1] is None:
                            entry[1] = "retired"
                            with self.lock:
                                del self.live[sessid]
                else:
                    raise Exception("Illegal session entry: " + repr(entry[1]))

    def checkclean(self):
        with self.lock:
            if self.cthread is None:
                self.cthread = threading.Thread(target = self.cleanloop)
                self.cthread.setDaemon(True)
                self.cthread.start()

    def mksession(self, req):
        return session(threading.RLock())

    def mkcookie(self, req, sess):
        cookie.add(req, self.cookiename, sess.id,
                   path=self.path,
                   expires=cookie.cdate(time.time() + sess.expire))

    def fetch(self, req):
        now = int(time.time())
        sessid = cookie.get(req, self.cookiename)
        new = False
        try:
            if sessid is None:
                raise KeyError()
            sess = self._fetch(sessid)
        except KeyError:
            sess = self.mksession(req)
            new = True

        def ckfreeze(req):
            if sess.dirty():
                if new:
                    self.mkcookie(req, sess)
                    with self.lock:
                        self.live[sess.id] = [sess.lock, sess]
                try:
                    self.freeze(sess)
                except:
                    pass
                self.checkclean()
        req.oncommit(ckfreeze)
        return sess

    def thaw(self, sessid):
        if self.backdb is None:
            raise KeyError()
        data = self.backdb[sessid]
        try:
            return pickle.loads(data)
        except:
            raise KeyError()

    def freeze(self, sess):
        if self.backdb is None:
            raise TypeError()
        with sess.lock:
            data = pickle.dumps(sess, -1)
        self.backdb[sess.id] = data
        sess.frozen()

    def get(self, req):
        return req.item(self.fetch)

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

default = env.var(db(backdb=dirback(os.path.join("/tmp", "wrwsess-" + str(os.getuid())))))

def get(req):
    return default.val.get(req)
