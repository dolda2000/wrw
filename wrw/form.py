import urllib.parse
from . import proto

__all__ = ["formdata"]

def formparse(req):
    buf = {}
    buf.update(urllib.parse.parse_qsl(req.query, keep_blank_values=True))
    ctype, ctpars = proto.pmimehead(req.ihead.get("Content-Type", ""))
    if ctype == "application/x-www-form-urlencoded":
        try:
            rbody = req.input.read(2 ** 20)
        except IOError as exc:
            return exc
        if len(rbody) >= 2 ** 20:
            return ValueError("x-www-form-urlencoded data is absurdly long")
        buf.update(urllib.parse.parse_qsl(rbody.decode("latin1"), encoding=ctpars.get("charset", "utf-8"), keep_blank_values=True))
    return buf

class badmultipart(IOError):
    pass

class formpart(object):
    def __init__(self, form):
        self.form = form
        self.buf = b""
        self.eof = False
        self.head = {}

    def parsehead(self):
        pass

    def fillbuf(self, sz):
        req = self.form.req
        mboundary = b"\r\n--" + self.form.boundary + b"\r\n"
        lboundary = b"\r\n--" + self.form.boundary + b"--\r\n"
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
                ret = req.input.read(8192)
                if ret == b"":
                    raise badmultipart("Missing last multipart boundary")
                self.form.buf += ret

    def read(self, limit=-1):
        self.fillbuf(limit)
        if limit >= 0:
            ret = self.buf[:limit]
            self.buf = self.buf[limit:]
        else:
            ret = self.buf
            self.buf = b""
        return ret

    def readline(self, limit=-1):
        last = 0
        while True:
            p = self.buf.find(b'\n', last)
            if p < 0:
                if self.eof:
                    ret = self.buf
                    self.buf = b""
                    return ret
                last = len(self.buf)
                self.fillbuf(last + 128)
            else:
                ret = self.buf[:p + 1]
                self.buf = self.buf[p + 1:]
                return ret

    def close(self):
        while True:
            if self.read(8192) == b"":
                break

    def __enter__(self):
        return self

    def __exit__(self, *excinfo):
        self.close()
        return False

    def parsehead(self, charset):
        def headline():
            ln = self.readline(256)
            if ln[-1] != ord(b'\n'):
                raise badmultipart("Too long header line in part")
            try:
                return ln.decode(charset).rstrip()
            except UnicodeError:
                raise badmultipart("Form part header is not in assumed charset")

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
    def __init__(self, req, charset):
        val, par = proto.pmimehead(req.ihead.get("Content-Type", ""))
        if req.method != "POST" or val != "multipart/form-data":
            raise badmultipart("Request is not a multipart form")
        if "boundary" not in par:
            raise badmultipart("Multipart form lacks boundary")
        try:
            self.boundary = par["boundary"].encode("us-ascii")
        except UnicodeError:
            raise badmultipart("Multipart boundary must be ASCII string")
        self.req = req
        self.buf = b"\r\n"
        self.eof = False
        self.headcs = charset
        self.lastpart = formpart(self)
        self.lastpart.close()

    def __iter__(self):
        return self

    def __next__(self):
        if not self.lastpart.eof:
            raise RuntimeError("All form parts must be read entirely")
        if self.eof:
            raise StopIteration()
        self.lastpart = formpart(self)
        self.lastpart.parsehead(self.headcs)
        return self.lastpart

def formdata(req, onerror=Exception):
    data = req.item(formparse)
    if isinstance(data, Exception):
        if onerror is Exception:
            raise data
        return onerror
    return data
