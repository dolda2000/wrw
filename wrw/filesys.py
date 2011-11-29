import os
import resp
pj = os.path.join

__all__ = ["filehandler"]

class filehandler(object):
    def __init__(self, basedir):
        self.basedir = basedir

    def handledir(self, req, path):
        raise resp.notfound()

    def handlefile(self, req, path):
        ctype = "application/octet-stream"
        bn = os.path.basename(path)
        if '.' in bn:
            ext = bn[bn.rindex('.') + 1:].lower()
            if ext == "jpg" or ext == "jpeg":
                ctype = "image/jpeg"
            elif ext == "png":
                ctype = "image/png"
            elif ext == "gif":
                ctype = "image/gif"
            elif ext == "txt":
                ctype = "text/plain"
            elif ext == "css":
                ctype = "text/css"
            elif ext == "html":
                ctype = "text/html"
        req.ohead["Content-Type"] = ctype
        return open(path, "r")

    def resolvefile(self, req, curpath, el):
        if os.path.isfile(pj(curpath, el)):
            return pj(curpath, el)
        if '.' not in el:
            for f in os.listdir(curpath):
                p = f.find('.')
                if p > 0:
                    if f[:p] == el:
                        return pj(curpath, f)
        raise resp.notfound()

    def handlefinal(self, req, curpath, el):
        if el == "":
            return self.handledir(req, curpath)
        return self.handlefile(req, self.resolvefile(req, curpath, el))

    def handlenonfinal(self, req, curpath, el, rest):
        raise resp.notfound()

    def handleentry(self, req, curpath, el, rest):
        if el == "":
            raise resp.notfound()
        if '/' in el or el[0] == '.':
            raise resp.notfound()
        if os.path.isdir(pj(curpath, el)):
            return self.handlepath(req, pj(curpath, el), rest)
        return self.handlenonfinal(req, curpath, el, rest)

    def handlepath(self, req, curpath, rest):
        p = rest.find('/')
        if p < 0:
            return self.handlefinal(req, curpath, rest)
        else:
            return self.handleentry(req, curpath, rest[:p], rest[p + 1:])

    def handle(self, req):
        pi = req.pathinfo
        if len(pi) > 0 and pi[0] == '/':
            pi = pi[1:]
        return self.handlepath(req, self.basedir, pi)
