import dispatch, proto, env
from sp import xhtml
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
        super(usererror, self).__init__()
        self.message = message
        self.detail = detail

    def handle(self, req):
        return skelfor(req).error(req, self.message, *self.detail)

class message(dispatch.restart):
    def __init__(self, msg, *detail):
        super(message, self).__init__()
        self.message = msg
        self.detail = detail

    def handle(self, req):
        return skelfor(req).message(req, self.message, *self.detail)

class httperror(usererror):
    def __init__(self, status, message = None, detail = None):
        if message is None:
            message = proto.statusinfo[status][0]
        if detail is None:
            detail = (proto.statusinfo[status][1],)
        super(httperror, self).__init__(message, *detail)
        self.status = status

    def handle(self, req):
        req.status(self.status, self.message)
        return super(httperror, self).handle(req)

class notfound(httperror):
    def __init__(self):
        return super(notfound, self).__init__(404)

class redirect(dispatch.restart):
    bases = {"url": proto.requrl,
             "script": proto.scripturl,
             "site": proto.siteurl}

    def __init__(self, url, status = 303, base = "url"):
        super(redirect, self).__init__()
        self.url = url
        self.status = status
        self.bases[base]
        self.base = base

    def handle(self, req):
        req.status(self.status, "Redirect")
        req.ohead["Location"] = proto.appendurl(self.bases[self.base](req), self.url)
        req.ohead["Content-Length"] = 0
        return []

class unmodified(dispatch.restart):
    def handle(self, req):
        req.status(304, "Not Modified")
        req.ohead["Content-Length"] = "0"
        return []
