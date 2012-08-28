__all__ = ["request"]

class headdict(object):
    def __init__(self):
        self.dict = {}

    def __getitem__(self, key):
        return self.dict[key.lower()][1]

    def __setitem__(self, key, val):
        self.dict[key.lower()] = [key, val]

    def __contains__(self, key):
        return key.lower() in self.dict

    def __delitem__(self, key):
        del self.dict[key.lower()]

    def __iter__(self):
        return iter((list[0] for list in self.dict.itervalues()))
    
    def get(self, key, default = ""):
        if key.lower() in self.dict:
            return self.dict[key.lower()][1]
        return default

    def getlist(self, key):
        return self.dict.setdefault(key.lower(), [key])[1:]

    def add(self, key, val):
        self.dict.setdefault(key.lower(), [key]).append(val)

    def __repr__(self):
        return repr(self.dict)

    def __str__(self):
        return str(self.dict)

def fixcase(str):
    str = str.lower()
    i = 0
    b = True
    while i < len(str):
        if b:
            str = str[:i] + str[i].upper() + str[i + 1:]
        b = False
        if str[i] == '-':
            b = True
        i += 1
    return str

class request(object):
    def copy(self):
        return copyrequest(self)

    def shift(self, n):
        new = self.copy()
        new.uriname = self.uriname + self.pathinfo[:n]
        new.pathinfo = self.pathinfo[n:]
        return new

class origrequest(request):
    def __init__(self, env):
        self.env = env
        self.method = env["REQUEST_METHOD"].upper()
        self.uriname = env["SCRIPT_NAME"]
        self.filename = env.get("SCRIPT_FILENAME")
        self.uri = env["REQUEST_URI"]
        self.pathinfo = env["PATH_INFO"]
        self.query = env["QUERY_STRING"]
        self.remoteaddr = env["REMOTE_ADDR"]
        self.serverport = env["SERVER_PORT"]
        self.servername = env["SERVER_NAME"]
        self.https = "HTTPS" in env
        self.ihead = headdict()
        if "CONTENT_TYPE" in env:
            self.ihead["Content-Type"] = env["CONTENT_TYPE"]
        if "CONTENT_LENGTH" in env:
            self.ihead["Content-Length"] = env["CONTENT_LENGTH"]
        self.ohead = headdict()
        for k, v in env.items():
            if k[:5] == "HTTP_":
                self.ihead.add(fixcase(k[5:].replace("_", "-")), v)
        self.items = {}
        self.statuscode = (200, "OK")
        self.ohead["Content-Type"] = "text/html"
        self.resources = set()
        self.clean = set()
        self.commitfuns = []

    def status(self, code, msg):
        self.statuscode = code, msg

    def item(self, id):
        if id in self.items:
            return self.items[id]
        self.items[id] = new = id(self)
        if hasattr(new, "__enter__") and hasattr(new, "__exit__"):
            self.withres(new)
        return new

    def withres(self, res):
        if res not in self.resources:
            done = False
            res.__enter__()
            try:
                self.resources.add(res)
                self.clean.add(res.__exit__)
                done = True
            finally:
                if not done:
                    res.__exit__(None, None, None)
                    self.resources.discard(res)

    def cleanup(self):
        def clean1(list):
            if len(list) > 0:
                try:
                    list[0]()
                finally:
                    clean1(list[1:])
        clean1(list(self.clean))

    def oncommit(self, fn):
        if fn not in self.commitfuns:
            self.commitfuns.append(fn)

    def commit(self, startreq):
        for fun in reversed(self.commitfuns):
            fun(self)
        hdrs = []
        for nm in self.ohead:
            for val in self.ohead.getlist(nm):
                hdrs.append((nm, val))
        startreq("%s %s" % self.statuscode, hdrs)

    def topreq(self):
        return self

class copyrequest(request):
    def __init__(self, p):
        self.parent = p
        self.top = p.topreq()
        self.env = p.env
        self.method = p.method
        self.uriname = p.uriname
        self.filename = p.filename
        self.uri = p.uri
        self.pathinfo = p.pathinfo
        self.query = p.query
        self.remoteaddr = p.remoteaddr
        self.serverport = p.serverport
        self.https = p.https
        self.ihead = p.ihead
        self.ohead = p.ohead

    def status(self, code, msg):
        return self.parent.status(code, msg)

    def item(self, id):
        return self.top.item(id)

    def withres(self, res):
        return self.top.withres(res)

    def oncommit(self, fn):
        return self.top.oncommit(fn)

    def topreq(self):
        return self.parent.topreq()
