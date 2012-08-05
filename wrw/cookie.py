import http.cookies, time
from . import proto

__all__ = ["cookies", "get", "add"]

def addcookies(req):
    ck = cookies(req)
    for nm in ck.codec:
        req.ohead.add("Set-Cookie", ck.codec[nm].OutputString())

class cookiedict(object):
    def __init__(self, req):
        try:
            self.bk = http.cookies.SimpleCookie(req.ihead.get("Cookie"))
        except http.cookies.CookieError:
            self.bk = http.cookies.SimpleCookie()
        self.codec = http.cookies.SimpleCookie()
        req.oncommit(addcookies)

    def __getitem__(self, name):
        return self.bk[name].value

    def __contains__(self, name):
        return name in self.bk

    def get(self, name, default = None):
        if name not in self.bk:
            return default
        return self.bk[name].value

    def add(self, name, value, **kw):
        self.codec[name] = value
        for key, value in kw.items():
            self.codec[name][key] = value

    def __setitem__(self, name, value):
        self.add(name, value)

def cookies(req):
    return req.item(cookiedict)

def get(req, name, default = None):
    return cookies(req).get(name, default)

def add(req, name, value, **kw):
    cookies(req).add(name, value, **kw)

cdate = proto.httpdate
