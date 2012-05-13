import xml.dom.minidom

class node(object):
    def __str__(self):
        doc = xml.dom.minidom.Document()
        return self.__todom__(doc).toxml()

class text(node, str):
    def __todom__(self, doc):
        return doc.createTextNode(self)

class element(node):
    def __init__(self, ns, name, ctx):
        self.ns = ns
        self.name = str(name)
        self.ctx = ctx
        self.attrs = {}
        self.children = []

    def __call__(self, *children, **attrs):
        for child in children:
            self.children.append(self.ctx.nodefrom(child))
        for k, v in attrs.items():
            self.attrs[str(k)] = str(v)
        return self

    def __todom__(self, doc):
        el = doc.createElementNS(self.ns, self.name)
        for k, v in self.attrs.items():
            el.setAttribute(k, v)
        for child in self.children:
            el.appendChild(child.__todom__(doc))
        return el

class context(object):
    def __init__(self):
        self.nodeconv = {}
        self.nodeconv[bytes] = lambda ob: text(ob, "utf-8")
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
        raise Exception("No node conversion known for %s objects" % str(type(ob)))

class constructor(object):
    def __init__(self, ns, elcls = element, ctx=None):
        self._ns = ns
        self._elcls = elcls
        if ctx is None: ctx = context()
        self._ctx = ctx

    def __getattr__(self, name):
        return self._elcls(self._ns, name, self._ctx)
