import sys, collections.abc
import xml.dom.minidom

class node(object):
    pass

class text(node, str):
    def __todom__(self, doc):
        return doc.createTextNode(self)

class raw(node, str):
    def __todom__(self, doc):
        raise Exception("Cannot convert raw code to DOM objects")

class element(node):
    def __init__(self, ns, name, ctx):
        self.ns = ns
        self.name = str(name)
        self.ctx = ctx
        self.attrs = {}
        self.children = []

    def __call__(self, *children, **attrs):
        for child in children:
            self.ctx.addchild(self, child)
        for k, v in attrs.items():
            self.ctx.addattr(self, k, v)
        return self

    def __todom__(self, doc):
        el = doc.createElementNS(self.ns, self.name)
        for k, v in self.attrs.items():
            el.setAttribute(k, v)
        for child in self.children:
            el.appendChild(child.__todom__(doc))
        return el

    def __str__(self):
        doc = xml.dom.minidom.Document()
        return self.__todom__(doc).toxml()

class context(object):
    charset = (sys.getfilesystemencoding() or "ascii")

    def __init__(self):
        self.nodeconv = {}
        self.nodeconv[bytes] = lambda ob: text(ob, self.charset)
        self.nodeconv[str] = text
        self.nodeconv[int] = text
        self.nodeconv[float] = text

    def nodefrom(self, ob):
        if isinstance(ob, node):
            return ob
        if hasattr(ob, "__tonode__"):
            return ob.__tonode__()
        if type(ob) in self.nodeconv:
            return self.nodeconv[type(ob)](ob)
        return None

    def addchild(self, node, child):
        if child is None:
            return
        new = self.nodefrom(child)
        if new is not None:
            node.children.append(self.nodefrom(child))
        elif isinstance(child, collections.abc.Iterable):
            for ch in child:
                self.addchild(node, ch)
        else:
            raise Exception("No node conversion known for %s objects" % str(type(ob)))

    def addattr(self, node, k, v):
        if v is not None:
            node.attrs[str(k)] = str(v)

class constructor(object):
    def __init__(self, ns, elcls=element, ctx=None):
        self._ns = ns
        self._elcls = elcls
        if ctx is None: ctx = context()
        self._ctx = ctx

    def __getattr__(self, name):
        return self._elcls(self._ns, name, self._ctx)

class doctype(node):
    def __init__(self, rootname, pubid, dtdid):
        self.rootname = rootname
        self.pubid = pubid
        self.dtdid = dtdid
