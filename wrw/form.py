import cgi
import proto

__all__ = ["formdata"]

class formwrap(object):
    def __init__(self, req):
        if req.ihead.get("Content-Type") == "application/x-www-form-urlencoded":
            self.cf = cgi.parse(environ = req.env, fp = req.env["wsgi.input"])
        else:
            self.cf = cgi.parse(environ = req.env)

    def __getitem__(self, key):
        return self.cf[key][0]

    def get(self, key, default = ""):
        if key in self:
            return self.cf[key][0]
        return default

    def __contains__(self, key):
        return key in self.cf and len(self.cf[key]) > 0

    def __iter__(self):
        return iter(self.cf)

    def items(self):
        def iter():
            for key, list in self.cf.items():
                for val in list:
                    yield key, val
        return list(iter())

    def keys(self):
        return self.cf.keys()

    def values(self):
        return [val for key, val in self.items()]

class badmultipart(Exception):
    pass

class formpart(object):
    def __init__(self, form):
        self.form = form
        self.buf = ""
        self.eof = False
        self.head = {}

    def parsehead(self):
        pass

    def fillbuf(self, sz):
        req = self.form.req
        mboundary = "\r\n--" + self.form.boundary + "\r\n"
        lboundary = "\r\n--" + self.form.boundary + "--\r\n"
        while not self.eof:
            p = self.form.buf.find(mboundary)
            if p >= 0:
                self.buf += self.form.buf[:p]
                self.form.buf = self.form.buf[p + len(mboundary):]
                self.eof = True
                break
            p = self.form.buf.find(lboundary)
            if p >= 0:
                self.buf += self.form.buf[:p]
                self.form.buf = self.form.buf[p + len(lboundary):]
                self.eof = True
                self.form.eof = True
                break
            self.buf += self.form.buf[:-len(lboundary)]
            self.form.buf = self.form.buf[-len(lboundary):]
            if sz >= 0 and len(self.buf) >= sz:
                break
            while len(self.form.buf) <= len(lboundary):
                ret = req.env["wsgi.input"].read(8192)
                if ret == "":
                    raise badmultipart("Missing last multipart boundary")
                self.form.buf += ret

    def read(self, limit = -1):
        self.fillbuf(limit)
        if limit >= 0:
            ret = self.buf[:limit]
            self.buf = self.buf[limit:]
        else:
            ret = self.buf
            self.buf = ""
        return ret

    def readline(self, limit = -1):
        last = 0
        while True:
            p = self.buf.find('\n', last)
            if p < 0:
                if self.eof:
                    ret = self.buf
                    self.buf = ""
                    return ret
                last = len(self.buf)
                self.fillbuf(last + 128)
            else:
                ret = self.buf[:p + 1]
                self.buf = self.buf[p + 1:]
                return ret

    def close(self):
        self.fillbuf(-1)

    def __enter__(self):
        return self

    def __exit__(self, *excinfo):
        self.close()
        return False

    def parsehead(self):
        def headline():
            ln = self.readline(256)
            if ln[-1] != '\n':
                raise badmultipart("Too long header line in part")
            return ln.rstrip()

        ln = headline()
        while True:
            if ln == "":
                break
            buf = ln
            while True:
                ln = headline()
                if not ln[1:].isspace():
                    break
                buf += ln.lstrip()
            p = buf.find(':')
            if p < 0:
                raise badmultipart("Malformed multipart header line")
            self.head[buf[:p].strip().lower()] = buf[p + 1:].lstrip()

        val, par = proto.pmimehead(self.head.get("content-disposition", ""))
        if val != "form-data":
            raise badmultipart("Unexpected Content-Disposition in form part: %r" % val)
        if not "name" in par:
            raise badmultipart("Missing name in form part")
        self.name = par["name"]
        self.filename = par.get("filename")
        val, par = proto.pmimehead(self.head.get("content-type", ""))
        self.ctype = val
        self.charset = par.get("charset")
        encoding = self.head.get("content-transfer-encoding", "binary")
        if encoding != "binary":
            raise badmultipart("Form part uses unexpected transfer encoding: %r" % encoding)

class multipart(object):
    def __init__(self, req):
        val, par = proto.pmimehead(req.ihead.get("Content-Type", ""))
        if req.method != "POST" or val != "multipart/form-data":
            raise badmultipart("Request is not a multipart form")
        if "boundary" not in par:
            raise badmultipart("Multipart form lacks boundary")
        self.boundary = par["boundary"]
        self.req = req
        self.buf = "\r\n"
        self.eof = False
        self.lastpart = formpart(self)
        self.lastpart.close()

    def __iter__(self):
        return self

    def next(self):
        if not self.lastpart.eof:
            raise RuntimeError("All form parts must be read entirely")
        if self.eof:
            raise StopIteration()
        self.lastpart = formpart(self)
        self.lastpart.parsehead()
        return self.lastpart

def formdata(req):
    return req.item(formwrap)
