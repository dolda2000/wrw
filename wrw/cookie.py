import Cookie

__all__ = ["cookies", "get", "add"]

def addcookies(req):
    ck = cookies(req)
    for nm in ck.codec:
        req.ohead.add("Set-Cookie", ck.codec[nm].OutputString())

class cookiedict(object):
    def __init__(self, req):
        self.bk = Cookie.SimpleCookie(req.ihead.get("Cookie"))
        self.codec = Cookie.SimpleCookie()
        req.oncommit(addcookies)

    def __getitem__(self, name):
        return self.bk[name].value

    def __contains__(self, name):
        return name in self.bk

    def get(self, name, default = None):
        if name not in self.bk:
            return default
        return self.bk[name].value

    def add(self, name, value, path = None):
        self.codec[name] = value
        if path is not None: self.codec[name]["path"] = path

    def __setitem__(self, name, value):
        self.add(name, value)

def cookies(req):
    return req.item(cookiedict)

def get(req, name, default = None):
    return cookies(req).get(name, default)

def add(req, name, value, path = None):
    cookies(req).add(name, value, path)
