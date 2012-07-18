from . import cons

def findnsnames(el):
    names = {}
    nid = [1]
    def proc(el):
        if isinstance(el, cons.element):
            if el.ns not in names:
                names[el.ns] = "n" + str(nid[0])
                nid[:] = [nid[0] + 1]
            for ch in el.children:
                proc(ch)
    proc(el)
    if None in names:
        names[None] = None
    else:
        names[el.ns] = None
    return names

class formatter(object):
    def __init__(self, out, root, nsnames=None, charset="utf-8", doctype=None):
        self.root = root
        if nsnames is None:
            nsnames = findnsnames(root)
        self.nsnames = nsnames
        self.out = out
        self.charset = charset
        self.doctype = doctype

    def write(self, text):
        self.out.write(text.encode(self.charset))

    def quotewrite(self, buf):
        for ch in buf:
            if ch == '&':
                self.write("&amp;")
            elif ch == '<':
                self.write("&lt;")
            elif ch == '>':
                self.write("&gt;")
            else:
                self.write(ch)

    def text(self, el):
        self.quotewrite(el)

    def rawcode(self, el):
        self.write(el)

    def attrval(self, buf):
        qc, qt = ("'", "&apos;") if '"' in buf else ('"', "&quot;")
        self.write(qc)
        for ch in buf:
            if ch == '&':
                self.write("&amp;")
            elif ch == '<':
                self.write("&lt;")
            elif ch == '>':
                self.write("&gt;")
            elif ch == qc:
                self.write(qt)
            else:
                self.write(ch)
        self.write(qc)

    def attr(self, k, v):
        self.write(k)
        self.write('=')
        self.attrval(v)

    def shorttag(self, el, **extra):
        self.write('<' + self.elname(el))
        for k, v in el.attrs.items():
            self.write(' ')
            self.attr(k, v)
        for k, v in extra.items():
            self.write(' ')
            self.attr(k, v)
        self.write(" />")

    def elname(self, el):
        ns = self.nsnames[el.ns]
        if ns is None:
            return el.name
        else:
            return ns + ':' + el.name

    def starttag(self, el, **extra):
        self.write('<' + self.elname(el))
        for k, v in el.attrs.items():
            self.write(' ')
            self.attr(k, v)
        for k, v in extra.items():
            self.write(' ')
            self.attr(k, v)
        self.write('>')

    def endtag(self, el):
        self.write('</' + self.elname(el) + '>')

    def longtag(self, el):
        self.starttag(el, **extra)
        for ch in el.children:
            self.node(ch)
        self.endtag(el)

    def element(self, el, **extra):
        if len(el.children) == 0:
            self.shorttag(el, **extra)
        else:
            self.longtag(el, **extra)

    def node(self, el):
        if isinstance(el, cons.element):
            self.element(el)
        elif isinstance(el, cons.text):
            self.text(el)
        elif isinstance(el, cons.raw):
            self.rawcode(el)
        else:
            raise Exception("Unknown object in element tree: " + el)

    def start(self):
        self.write('<?xml version="1.0" encoding="' + self.charset + '" ?>\n')
        if self.doctype:
            self.write('<!DOCTYPE %s PUBLIC "%s" "%s">\n' % (self.root.name,
                                                             self.doctype[0],
                                                             self.doctype[1]))
        extra = {}
        for uri, nm in self.nsnames.items():
            if uri is None:
                continue
            if nm is None:
                extra["xmlns"] = uri
            else:
                extra["xmlns:" + nm] = uri
        self.element(self.root, **extra)

    @classmethod
    def output(cls, out, el, *args, **kw):
        cls(out=out, root=el, *args, **kw).start()

    @classmethod
    def fragment(cls, out, el, *args, **kw):
        cls(out=out, root=el, *args, **kw).node(el)

    def update(self, **ch):
        ret = type(self).__new__(type(self))
        ret.__dict__.update(self.__dict__)
        ret.__dict__.update(ch)
        return ret

class iwriter(object):
    def __init__(self, out):
        self.out = out
        self.atbol = True
        self.col = 0

    def write(self, buf):
        for i in range(len(buf)):
            c = buf[i:i + 1]
            if c == b'\n':
                self.col = 0
            else:
                self.col += 1
            self.out.write(c)
        self.atbol = False

    def indent(self, indent):
        if self.atbol:
            return
        if self.col != 0:
            self.write(b'\n')
        self.write(indent)
        self.atbol = True

class indenter(formatter):
    def __init__(self, indent="  ", *args, **kw):
        super(indenter, self).__init__(*args, **kw)
        self.out = iwriter(self.out)
        self.indent = indent
        self.curind = ""

    def simple(self, el):
        for ch in el.children:
            if not isinstance(ch, cons.text):
                return False
        return True

    def longtag(self, el, **extra):
        self.starttag(el, **extra)
        sub = self
        reind = False
        if not self.simple(el):
            sub = self.update(curind=self.curind + self.indent)
            sub.reindent()
            reind = True
        for ch in el.children:
            sub.node(ch)
        if reind:
            self.reindent()
        self.endtag(el)

    def element(self, el, **extra):
        super(indenter, self).element(el, **extra)
        if self.out.col > 80 and self.simple(el):
            self.reindent()

    def reindent(self):
        self.out.indent(self.curind.encode(self.charset))

    def start(self):
        super(indenter, self).start()
        self.write('\n')
