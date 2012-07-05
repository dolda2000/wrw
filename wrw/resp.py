from . import dispatch, proto, env
from .sp import xhtml
h = xhtml.cons()

__all__ = ["skeleton", "skelfor", "setskel", "usererror"]

class skeleton(object):
    def page(self, req, title, *content):
        return xhtml.forreq(req, h.html(self.head(req, title), h.body(*content)))

    def head(self, req, title):
        return xhtml.head(title=title)

    def error(self, req, message, *detail):
        return self.page(req, message, h.h1(message), h.p(*detail))

    def message(self, req, message, *detail):
        return self.page(req, message, h.h1(message), h.p(*detail))

defskel = env.var(skeleton())

def getskel(req):
    return [defskel.val]
def skelfor(req):
    return req.item(getskel)[0]
def setskel(req, skel):
    req.item(getskel)[0] = skel

class usererror(dispatch.restart):
    def __init__(self, message, *detail):
        super().__init__()
        self.message = message
        self.detail = detail

    def handle(self, req):
        return skelfor(req).error(req, self.message, *self.detail)

class message(dispatch.restart):
    def __init__(self, message, *detail):
        super().__init__()
        self.message = message
        self.detail = detail

    def handle(self, req):
        return skelfor(req).error(req, self.message, *self.detail)

class httperror(usererror):
    def __init__(self, status, message = None, detail = None):
        if message is None:
            message = proto.statusinfo[status][0]
        if detail is None:
            detail = (proto.statusinfo[status][1],)
        super().__init__(message, *detail)
        self.status = status

    def handle(self, req):
        req.status(self.status, self.message)
        return super().handle(req)

class notfound(httperror):
    def __init__(self):
        return super().__init__(404)

class redirect(dispatch.restart):
    def __init__(self, url, status = 303):
        super().__init__()
        self.url = url
        self.status = status

    def handle(self, req):
        req.status(self.status, "Redirect")
        req.ohead["Location"] = proto.appendurl(proto.requrl(req), self.url)
        return []
