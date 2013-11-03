import binascii, hashlib, threading, time
from . import resp

class unauthorized(resp.httperror):
    def __init__(self, challenge, message=None, detail=None):
        super().__init__(401, message, detail)
        if isinstance(challenge, str):
            challenge = [challenge]
        self.challenge = challenge

    def handle(self, req):
        for challenge in self.challenge:
            req.ohead.add("WWW-Authenticate", challenge)
        return super().handle(req)

class forbidden(resp.httperror):
    def __init__(self, message=None, detail=None):
        super().__init__(403, message, detail)

def parsemech(req):
    h = req.ihead.get("Authorization", None)
    if h is None:
        return None, None
    p = h.find(" ")
    if p < 0:
        return None, None
    return h[:p].strip().lower(), h[p + 1:].strip()

def parsebasic(req):
    mech, data = parsemech(req)
    if mech != "basic":
        return None, None
    try:
        data = data.encode("us-ascii")
    except UnicodeError:
        return None, None
    try:
        raw = binascii.a2b_base64(data)
    except binascii.Error:
        return None, None
    try:
        raw = raw.decode("utf-8")
    except UnicodeError:
        raw = raw.decode("latin1")
    p = raw.find(":")
    if p < 0:
        return None, None
    return raw[:p], raw[p + 1:]

class basiccache(object):
    cachetime = 300

    def __init__(self, realm, authfn=None):
        self._lock = threading.Lock()
        self._cache = {}
        self.realm = realm
        if authfn is not None:
            self.auth = authfn

    def _obscure(self, nm, pw):
        dig = hashlib.sha256()
        dig.update(self.realm.encode("utf-8"))
        dig.update(nm.encode("utf-8"))
        dig.update(pw.encode("utf-8"))
        return dig.digest()

    def check(self, req):
        nm, pw = parsebasic(req)
        if nm is None:
            raise unauthorized("Basic Realm=\"%s\"" % self.realm)
        pwh = self._obscure(nm, pw)
        now = time.time()
        with self._lock:
            if (nm, pwh) in self._cache:
                lock, atime, res, resob = self._cache[nm, pwh]
                if now - atime < self.cachetime:
                    if res == "s":
                        return resob
                    elif res == "f":
                        raise resob
            else:
                lock = threading.Lock()
                self._cache[nm, pwh] = (lock, now, None, None)
        with lock:
            try:
                ret = self.auth(req, nm, pw)
            except forbidden as exc:
                with self._lock:
                    self._cache[nm, pwh] = (lock, now, "f", exc)
                raise
            if ret is None:
                raise forbidden()
            with self._lock:
                self._cache[nm, pwh] = (lock, now, "s", ret)
            return ret

    def auth(self, req, nm, pw):
        raise Exception("authentication function neither supplied nor overridden")
