from . import dispatch, proto, env

__all__ = ["skeleton", "skelfor", "setskel", "usererror"]

class skeleton(object):
    def page(self, title, content):
        return """<?xml version="1.0" ?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en-US">
<head>
%s
</head>
<body>
%s
</body>
</html>""" % (self.head(title), content)

    def head(self, title):
        return """<title>%s</title>\n%s""" % (title, self.style())

    def style(self):
        return ""

    def error(self, message, detail):
        return self.page(message, """<h1>%s</h1>\n<p>%s</p>\n""" % (message, detail))

    def message(self, message, detail):
        return self.page(message, """<h1>%s</h1>\n<p>%s</p>\n""" % (message, detail))

defskel = env.var(skeleton())

def getskel(req):
    return [defskel.val]
def skelfor(req):
    return req.item(getskel)[0]
def setskel(req, skel):
    req.item(getskel)[0] = skel

class usererror(dispatch.restart):
    def __init__(self, message, detail):
        super().__init__()
        self.message = message
        self.detail = detail

    def handle(self, req):
        return [skelfor(req).error(self.message, self.detail)]

class message(dispatch.restart):
    def __init__(self, message, detail):
        super().__init__()
        self.message = message
        self.detail = detail

    def handle(self, req):
        return [skelfor(req).message(self.message, self.detail)]

class httperror(usererror):
    def __init__(self, status, message = None, detail = None):
        if message is None:
            message = proto.statusinfo[status][0]
        if detail is None:
            detail = proto.statusinfo[status][1]
        super().__init__(message, detail)
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
