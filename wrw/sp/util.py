import itertools, StringIO
from wrw import dispatch
import cons

def findnsnames(el):
    names = {}
    nid = [1]
    def proc(el):
        if isinstance(el, cons.element):
            if el.ns not in names:
                names[el.ns] = u"n" + unicode(nid[0])
                nid[:] = [nid[0] + 1]
            for ch in el.children:
                proc(ch)
    proc(el)
    if None in names:
        names[None] = None
    else:
        names[el.ns] = None
    return names

def flatiter(root, short=True):
    yield ">", root
    stack = [(root, 0)]
    while len(stack) > 0:
        el, i = stack[-1]
        if i >= len(el.children):
            yield "<", el
            stack.pop()
        else:
            ch = el.children[i]
            stack[-1] = el, i + 1
            if isinstance(ch, cons.element):
                if short and len(ch.children) == 0:
                    yield "/", ch
                else:
                    yield ">", ch
                    stack.append((ch, 0))
            elif isinstance(ch, cons.text):
                yield "", ch
            elif isinstance(ch, cons.raw):
                yield "!", ch
            else:
                raise Exception("Unknown object in element tree: " + el)

class formatter(object):
    def __init__(self, src, nsnames=None, charset="utf-8"):
        self.src = src
        self.nsnames = nsnames or {}
        self.nextns = 1
        self.first = False
        self.buf = bytearray()
        self.charset = charset

    def write(self, text):
        self.buf.extend(text.encode(self.charset))

    def quotewrite(self, buf):
        buf = buf.replace(u'&', u"&amp;")
        buf = buf.replace(u'<', u"&lt;")
        buf = buf.replace(u'>', u"&gt;")
        self.write(buf)

    def __iter__(self):
        return self

    def elname(self, el):
        ns = self.nsnames[el.ns]
        if ns is None:
            return el.name
        else:
            return ns + u":" + el.name

    def attrval(self, v):
        qc, qt = (u"'", u"&apos;") if u'"' in v else (u'"', u"&quot;")
        self.write(qc)
        v = v.replace(u'&', u"&amp;")
        v = v.replace(u'<', u"&lt;")
        v = v.replace(u'>', u"&gt;")
        v = v.replace(qc, qt)
        self.write(v)
        self.write(qc)

    def attr(self, k, v):
        self.write(k)
        self.write(u"=")
        self.attrval(v)

    def attrs(self, attrs):
        for k, v in attrs:
            self.write(u" ")
            self.attr(k, v)

    def inittag(self, el):
        self.write(u"<" + self.elname(el))
        attrs = el.attrs.iteritems()
        if self.first:
            nsnames = []
            for ns, name in self.nsnames.iteritems():
                if ns is None:
                    if name is not None:
                        raise Exception("null namespace must have null name, not" + name)
                    continue
                nsnames.append((u"xmlns" if name is None else (u"xmlns:" + name), ns))
            attrs = itertools.chain(attrs, iter(nsnames))
            self.first = False
        self.attrs(attrs)

    def starttag(self, el):
        self.inittag(el)
        self.write(u">")

    def shorttag(self, el):
        self.inittag(el)
        self.write(u" />")

    def endtag(self, el):
        self.write(u"</" + self.elname(el) + u">")

    def text(self, el):
        self.quotewrite(el)

    def rawcode(self, el):
        self.write(el)

    def start(self, el):
        self.write(u'<?xml version="1.0" encoding="' + self.charset + u'" ?>\n')
        if isinstance(el, cons.doctype):
            self.write(u'<!DOCTYPE %s PUBLIC "%s" "%s">\n' % (el.rootname,
                                                              el.pubid,
                                                              el.dtdid))
        self.first = True

    def end(self, el):
        pass

    def handle(self, ev, el):
        if ev == ">":
            self.starttag(el)
        elif ev == "/":
            self.shorttag(el)
        elif ev == "<":
            self.endtag(el)
        elif ev == "":
            self.text(el)
        elif ev == "!":
            self.rawcode(el)
        elif ev == "^":
            self.start(el)
        elif ev == "$":
            self.end(el)

    def next(self):
        if self.src is None:
            raise StopIteration()
        try:
            ev, el = next(self.src)
        except StopIteration:
            self.src = None
            ev, el = "$", None
        self.handle(ev, el)
        ret = str(self.buf)
        self.buf[:] = ""
        return ret

    def nsname(self, el):
        for t in type(self).__mro__:
            ret = getattr(t, "defns", {}).get(el.ns, None)
            if ret is not None:
                return ret
        if el.ns is None:
            return None
        ret = u"n" + unicode(self.nextns)
        self.nextns += 1
        return ret

    def findnsnames(self, root):
        fnames = {}
        rnames = {}
        def proc(el):
            if isinstance(el, cons.element):
                if el.ns not in fnames:
                    nm = self.nsname(el)
                    fnames[el.ns] = nm
                    rnames[nm] = el.ns
                for ch in el.children:
                    proc(ch)
        proc(root)
        if None not in rnames:
            fnames[root.ns] = None
            rnames[None] = root.ns
        self.nsnames = fnames

    @classmethod
    def output(cls, out, root, nsnames=None, doctype=None, **kw):
        if isinstance(doctype, cons.doctype):
            pass
        elif doctype is not None:
            doctype = cons.doctype(root.name, doctype[0], doctype[1])
        src = itertools.chain(iter([("^", doctype)]), flatiter(root))
        self = cls(src=src, nsnames=nsnames, **kw)
        if nsnames is None:
            self.findnsnames(root)
        self.first = True
        for piece in self:
            out.write(piece)

    @classmethod
    def fragment(cls, out, root, nsnames=None, **kw):
        self = cls(src=flatiter(root), nsnames=nsnames, **kw)
        if nsnames is None:
            self.findnsnames(root)
        for piece in self:
            out.write(piece)

    @classmethod
    def format(cls, root, **kw):
        buf = StringIO.StringIO()
        cls.output(buf, root, **kw)
        return buf.getvalue()

class indenter(formatter):
    def __init__(self, indent=u"  ", *args, **kw):
        super(indenter, self).__init__(*args, **kw)
        self.indent = indent
        self.col = 0
        self.curind = u""
        self.atbreak = True
        self.inline = False
        self.stack = []
        self.last = None, None
        self.lastendbr = True

    def write(self, text):
        lines = text.split(u"\n")
        if len(lines) > 1:
            for ln in lines[:-1]:
                self.buf.extend(ln.encode(self.charset))
                self.buf.extend("\n")
            self.col = 0
        self.buf.extend(lines[-1].encode(self.charset))
        self.col += len(lines[-1])
        self.atbreak = False

    def br(self):
        if not self.atbreak:
            self.buf.extend((u"\n" + self.curind).encode(self.charset))
            self.col = 0
            self.atbreak = True

    def inlinep(self, el):
        for ch in el.children:
            if isinstance(ch, cons.text):
                return True
        return False

    def push(self, el):
        self.stack.append((el, self.curind, self.inline))

    def pop(self):
        el, self.curind, self.inline = self.stack.pop()
        return el

    def starttag(self, el):
        if not self.inline:
            if self.last[0] == "<" and self.last[1].name == el.name and self.lastendbr:
                pass
            else:
                self.br()
        self.push(el)
        self.inline = self.inline or self.inlinep(el)
        self.curind += self.indent
        super(indenter, self).starttag(el)

    def shorttag(self, el):
        if not self.inline:
            self.br()
        super(indenter, self).shorttag(el)

    def endtag(self, el):
        il = self.inline
        self.pop()
        if il or (self.last[0] == ">" and self.last[1] == el):
            self.lastendbr = False
        else:
            self.br()
            self.lastendbr = True
        super(indenter, self).endtag(el)

    def start(self, el):
        super(indenter, self).start(el)
        self.atbreak = True

    def end(self, el):
        self.br()

    def handle(self, ev, el):
        super(indenter, self).handle(ev, el)
        self.last = ev, el

class textindenter(indenter):
    maxcol = 70

    def text(self, el):
        left = unicode(el)
        while True:
            if len(left) + self.col > self.maxcol:
                bp = max(self.maxcol - self.col, 0)
                for i in xrange(bp, -1, -1):
                    if left[i].isspace():
                        while i > 0 and left[i - 1].isspace(): i -= 1
                        break
                else:
                    for i in xrange(bp + 1, len(left)):
                        if left[i].isspace():
                            break
                    else:
                        i = None
                if i is None:
                    self.quotewrite(left)
                    break
                else:
                    self.quotewrite(left[:i])
                    self.br()
                    left = left[i + 1:].lstrip()
            else:
                self.quotewrite(left)
                break

class response(dispatch.restart):
    charset = "utf-8"
    doctype = None
    formatter = indenter

    def __init__(self, root):
        super(response, self).__init__()
        self.root = root

    @property
    def ctype(self):
        raise Exception("a subclass of wrw.sp.util.response must override ctype")

    def handle(self, req):
        ret = self.formatter.format(self.root, doctype=self.doctype, charset=self.charset)
        req.ohead["Content-Type"] = self.ctype
        req.ohead["Content-Length"] = len(ret)
        return [ret]
