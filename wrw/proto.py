import time, calendar, collections.abc, binascii, base64

statusinfo = {
    400: ("Bad Request", "Invalid HTTP request."),
    401: ("Unauthorized", "Authentication must be provided for the requested resource."),
    403: ("Forbidden", "You are not authorized to request the requested resource."),
    404: ("Not Found", "The requested resource was not found."),
    405: ("Method Not Allowed", "The request method is not recognized or permitted by the requested resource."),
    406: ("Not Acceptable", "No way was found to satisfy the given content-negotiation criteria."),
    407: ("Proxy Authentication Required", "Authentication must be provided to proxy the request."),
    408: ("Request Timeout", "The connection timed out."),
    409: ("Conflict", "The request conflicts with the live state."),
    410: ("Gone", "The requested resource has been deleted."),
    411: ("Length Required", "The requested resource requires the Content-Length header."),
    412: ("Precondition Failed", "The preconditions specified in the request are not met."),
    413: ("Payload Too Large", "The request entity is larger than permitted."),
    414: ("URI Too Long", "The requested URI is too long."),
    415: ("Unsupported Media Type", "The request entity format is not supported."),
    416: ("Range Not Satisfiable", "The specified Range cannot be satisfied."),
    417: ("Expectation Failed", "The expectation specified by the Expect header cannot be met."),
    421: ("Misdirected Request", "This server cannot handle the request."),
    422: ("Unprocessable Content", "The requet entity cannot be processed."),
    423: ("Locked", "The requested resource is locked."),
    424: ("Failed Dependency", "A previous required request failed."),
    425: ("TOo Early", "The requested action has already been performed."),
    426: ("Upgrade Required", "The requested resource is not available over this protocol."),
    428: ("Precondition Requred", "The requested resource needs to be conditionally requested."),
    429: ("Too Many Requests", "Your client is sending more frequent requests than are accepted."),
    431: ("Request Header Fields Too Large", "The request headers are too large."),
    451: ("Unavilable For Legal Reasons", "The requested resource has been censored."),
    500: ("Server Error", "An internal error occurred."),
    501: ("Not Implemented", "The requested functionality has not been implemented."),
    502: ("Bad Gateway", "The backing server indicated an error."),
    503: ("Service Unavailable", "Service is being denied at this time."),
    504: ("Gateway Timeout", "The backing server is not responding."),
    505: ("Unsupported HTTP Version", "The server does not support the requested HTTP version."),
    506: ("Variant Also Negotiates", "The server content-negotiation is misconfigured."),
    507: ("Insufficient Storage", "The server is out of storage to process the request."),
    508: ("Loop Detected", "An infinite loop was detected while processing the request."),
    510: ("Not Extended", "The requested extension is not supported."),
    511: ("Network Authentication Required", "Authentication for network access is required."),
    }

def httpdate(ts):
    return time.strftime("%a, %d %b %Y %H:%M:%S +0000", time.gmtime(ts))

def phttpdate(dstr):
    tz = dstr[-6:]
    dstr = dstr[:-6]
    if tz[0] != " " or (tz[1] != "+" and tz[1] != "-") or not tz[2:].isdigit():
        return None
    tz = int(tz[1:])
    tz = (((tz / 100) * 60) + (tz % 100)) * 60
    return calendar.timegm(time.strptime(dstr, "%a, %d %b %Y %H:%M:%S")) - tz

def pmimehead(hstr):
    def pws(p):
        while p < len(hstr) and hstr[p].isspace():
            p += 1
        return p
    def token(p, sep):
        buf = ""
        p = pws(p)
        if p >= len(hstr):
            return "", p
        if hstr[p] == '"':
            p += 1
            while p < len(hstr):
                if hstr[p] == '\\':
                    p += 1
                    if p < len(hstr):
                        buf += hstr[p]
                        p += 1
                    else:
                        break
                elif hstr[p] == '"':
                    p += 1
                    break
                else:
                    buf += hstr[p]
                    p += 1
            return buf, pws(p)
        else:
            while p < len(hstr):
                if hstr[p] in sep:
                    break
                buf += hstr[p]
                p += 1
            return buf.strip(), pws(p)
    p = 0
    val, p = token(p, ";")
    pars = {}
    while p < len(hstr):
        if hstr[p] != ';':
            break
        p += 1
        k, p = token(p, "=")
        if k == "" or hstr[p:p + 1] != '=':
            break
        p += 1
        v, p = token(p, ';')
        pars[k.lower()] = v
    return val, pars

def htmlq(html):
    ret = ""
    for c in html:
        if c == "&":
            ret += "&amp;"
        elif c == "<":
            ret += "&lt;"
        elif c == ">":
            ret += "&gt;"
        else:
            ret += c
    return ret

def simpleerror(env, startreq, code, title, msg):
    buf = """<?xml version="1.0" encoding="US-ASCII"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en-US">
<head>
<title>%s</title>
</head>
<body>
<h1>%s</h1>
<p>%s</p>
</body>
</html>
""" % (title, title, htmlq(msg))
    buf = buf.encode("us-ascii")
    startreq("%i %s" % (code, title), [("Content-Type", "text/html"), ("Content-Length", str(len(buf)))])
    return [buf]

def urlq(url):
    if isinstance(url, str):
        url = url.encode("utf-8")
    ret = ""
    invalid = b"%;&=+#?/\"'"
    for c in url:
        if c in invalid or (c <= 32) or (c >= 128):
            ret += "%%%02X" % c
        else:
            ret += chr(c)
    return ret

class urlerror(ValueError):
    pass

def parseurl(url):
    p = url.find("://")
    if p < 0:
        raise urlerror("Protocol not found in absolute URL `%s'" % url)
    proto = url[:p]
    l = url.find("/", p + 3)
    if l < 0:
        raise urlerror("Local part not found in absolute URL `%s'" % url)
    host = url[p + 3:l]
    local = url[l:]
    q = local.find("?")
    if q < 0:
        query = ""
    else:
        query = local[q + 1:]
        local = local[:q]
    return proto, host, local, query

def consurl(proto, host, local, query=""):
    if len(local) < 1 and local[0] != '/':
        raise urlerror("Local part of URL must begin with a slash")
    ret = "%s://%s%s" % (proto, host, local)
    if len(query) > 0:
        ret += "?" + query
    return ret

def appendurl(url, other):
    if "://" in other:
        return other
    proto, host, local, query = parseurl(url)
    if len(other) > 0 and other[0] == '/':
        return consurl(proto, host, other)
    else:
        p = local.rfind('/')
        return consurl(proto, host, local[:p + 1] + other)

def siteurl(req):
    host = req.ihead.get("Host", None)
    if host is None:
        raise Exception("Could not reconstruct URL because no Host header was sent")
    proto = "http"
    if req.https:
        proto = "https"
    return "%s://%s/" % (proto, host)

def scripturl(req):
    s = siteurl(req)
    if req.uriname[0] != '/':
        raise Exception("Malformed local part when reconstructing URL")
    return siteurl(req) + req.uriname[1:]

def requrl(req, qs=True):
    s = siteurl(req)
    if req.uri[0] != '/':
        raise Exception("Malformed local part when reconstructing URL")
    pf = req.uri[1:]
    if not qs:
        p = pf.find('?')
        if not p < 0:
            pf = pf[:p]
    return siteurl(req) + pf

def parstring(pars={}, **augment):
    buf = ""
    for key in pars:
        if key in augment:
            val = augment[key]
            del augment[key]
        else:
            val = pars[key]
        if val is None:
            continue
        if buf != "": buf += "&"
        buf += urlq(key) + "=" + urlq(str(val))
    for key, val in augment.items():
        if val is None:
            continue
        if buf != "": buf += "&"
        buf += urlq(key) + "=" + urlq(str(val))
    return buf

def parurl(url, pars={}, **augment):
    qs = parstring(pars, **augment)
    if qs != "":
        return url + ("&" if "?" in url else "?") + qs
    else:
        return url

# Wrap these, since binascii is a bit funky. :P
def enhex(bs):
    return base64.b16encode(bs).decode("us-ascii")
def unhex(es):
    if not isinstance(es, collections.abc.ByteString):
        try:
            es = es.encode("us-ascii")
        except UnicodeError:
            raise binascii.Error("non-ascii character in hex-string")
    return base64.b16decode(es)
def enb32(bs):
    return base64.b32encode(bs).decode("us-ascii")
def unb32(es):
    if not isinstance(es, collections.abc.ByteString):
        try:
            es = es.encode("us-ascii")
        except UnicodeError:
            raise binascii.Error("non-ascii character in base32-string")
    if (len(es) % 8) != 0:
        es += b"=" * (8 - (len(es) % 8))
    es = es.upper()             # The whole point of Base32 is that it's case-insensitive :P
    return base64.b32decode(es)
def enb64(bs):
    return base64.b64encode(bs).decode("us-ascii")
def unb64(es):
    if not isinstance(es, collections.abc.ByteString):
        try:
            es = es.encode("us-ascii")
        except UnicodeError:
            raise binascii.Error("non-ascii character in base64-string")
    if (len(es) % 4) != 0:
        es += b"=" * (4 - (len(es) % 4))
    return base64.b64decode(es)

def _quoprisafe():
    ret = [False] * 256
    for c in "-!*+/":
        ret[ord(c)] = True
    for c in range(ord('0'), ord('9') + 1):
        ret[c] = True
    for c in range(ord('A'), ord('Z') + 1):
        ret[c] = True
    for c in range(ord('a'), ord('z') + 1):
        ret[c] = True
    return ret
_quoprisafe = _quoprisafe()
def quopri(s, charset="utf-8"):
    bv = s.encode(charset)
    qn = sum(not _quoprisafe[b] for b in bv)
    if qn == 0:
        return s
    if qn > len(bv) / 2:
        return "=?%s?B?%s?=" % (charset, enb64(bv))
    else:
        return "=?%s?Q?%s?=" % (charset, "".join(chr(b) if _quoprisafe[b] else "=%02X" % b for b in bv))

class mimeparam(object):
    def __init__(self, name, val, fallback=None, charset="utf-8", lang=""):
        self.name = name
        self.val = val
        self.fallback = fallback
        self.charset = charset
        self.lang = lang

    def __str__(self):
        self.name.encode("ascii")
        try:
            self.val.encode("ascii")
        except UnicodeError:
            pass
        else:
            return "%s=%s" % (self.name, self.val)
        val = self.val.encode(self.charset)
        self.charset.encode("ascii")
        self.lang.encode("ascii")
        ret = ""
        if self.fallback is not None:
            self.fallback.encode("ascii")
            ret += "%s=%s; " % (self.name, self.fallback)
        ret += "%s*=%s'%s'%s" % (self.name, self.charset, self.lang, urlq(val))
        return ret

class mimeheader(object):
    def __init__(self, name, val, *, mime_charset="utf-8", mime_lang="", **params):
        self.name = name
        self.val = val
        self.params = {}
        self.charset = mime_charset
        self.lang = mime_lang
        for k, v in params.items():
            self[k] = v

    def __getitem__(self, nm):
        return self.params[nm.lower()]

    def __setitem__(self, nm, val):
        if not isinstance(val, mimeparam):
            val = mimeparam(nm, val, charset=self.charset, lang=self.lang)
        self.params[nm.lower()] = val

    def __delitem__(self, nm):
        del self.params[nm.lower()]

    def value(self):
        parts = []
        if self.val != None:
            parts.append(quopri(self.val))
        parts.extend(str(x) for x in self.params.values())
        return("; ".join(parts))

    def __str__(self):
        if self.name is None:
            return self.value()
        return "%s: %s" % (self.name, self.value())
