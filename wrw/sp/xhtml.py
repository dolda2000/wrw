import xml.dom.minidom, StringIO
import cons as _cons
import util
dom = xml.dom.minidom.getDOMImplementation()

ns = u"http://www.w3.org/1999/xhtml"
doctype = u"-//W3C//DTD XHTML 1.1//EN"
dtd = u"http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd"

class htmlelement(_cons.element):
    def __todoc__(self):
        doc = dom.createDocument(None, None, None)
        doc.appendChild(dom.createDocumentType("html", doctype, dtd))
        doc.appendChild(self.__todom__(doc))
        return doc

class xhtmlcontext(_cons.context):
    attrmap = {u"klass": u"class"}

    def addattr(self, node, k, v):
        k = unicode(k)
        super(xhtmlcontext, self).addattr(node, self.attrmap.get(k, k), v)

def cons(ctx=None):
    if ctx is None: ctx = xhtmlcontext()
    return _cons.constructor(ns, htmlelement, ctx)

def head(title=None, css=None):
    h = cons()
    head = h.head
    if title:
        head(h.title(title))
    if isinstance(css, str) or isinstance(css, unicode):
        head(h.link(rel="stylesheet", type="text/css", href=css))
    elif css:
        for ss in css:
            head(h.link(rel="stylesheet", type="text/css", href=ss))
    return head

class htmlformatter(util.formatter):
    allowshort = set([u"br", u"hr", u"img", u"input", u"meta", u"link"])
    def shorttag(self, el):
        if el.name in self.allowshort:
            super(htmlformatter, self).shorttag(el)
        else:
            self.starttag(el)
            self.endtag(el)

class htmlindenter(util.textindenter, htmlformatter):
    pass

def forreq(req, tree):
    # XXX: Use proper Content-Type for clients accepting it.
    req.ohead["Content-Type"] = "text/html; charset=utf-8"
    buf = StringIO.StringIO()
    htmlindenter.output(buf, tree, doctype=(doctype, dtd), charset="utf-8")
    ret = buf.getvalue()
    req.ohead["Content-Length"] = len(ret)
    return [ret]

def xhtmlresp(callable):
    def wrapper(req):
        return forreq(req, callable(req))
    wrapper.__wrapped__ = callable
    return wrapper
