import sys, os, math
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
        return skelfor(req).message(req, self.message, *self.detail)

class httperror(usererror):
    def __init__(self, status, message=None, detail=None):
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
    bases = {"url": proto.requrl,
             "script": proto.scripturl,
             "site": proto.siteurl}

    def __init__(self, url, status=303, base="url"):
        super().__init__()
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

class fileiter(object):
    def __init__(self, fp):
        self.fp = fp

    def __iter__(self):
        return self

    def __next__(self):
        if self.fp is None:
            raise StopIteration()
        data = self.fp.read(16384)
        if data == b"":
            self.fp.close()
            self.fp = None
            raise StopIteration()
        return data

    def close(self):
        if self.fp is not None:
            self.fp.close()
            self.fp = None

class fileresp(dispatch.restart):
    def __init__(self, fp, ctype, charset=None, cachable=True):
        self.fp = fp
        self.ctype = ctype
        if charset is None and ctype.startswith("text/"):
            charset = sys.getdefaultencoding()
        self.charset = charset
        self.cachable = cachable

    def handle(self, req):
        sb = None
        if hasattr(self.fp, "fileno"):
            sb = os.fstat(self.fp.fileno())
        if self.cachable and sb and sb.st_mtime != 0:
            if "If-Modified-Since" in req.ihead:
                rtime = proto.phttpdate(req.ihead["If-Modified-Since"])
                if rtime is not None and rtime >= math.floor(sb.st_mtime):
                    raise unmodified()
            req.ohead["Last-Modified"] = proto.httpdate(sb.st_mtime)
        ctype = self.ctype
        if self.charset is not None:
            ctype += "; charset=%s" % (self.charset)
        req.ohead["Content-Type"] = ctype
        if sb and sb.st_size > 0:
            req.ohead["Content-Length"] = str(sb.st_size)
        return fileiter(self.fp)
