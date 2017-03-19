import time, calendar

statusinfo = {
    400: ("Bad Request", "Invalid HTTP request."),
    401: ("Unauthorized", "Authentication must be provided for the requested resource."),
    403: ("Forbidden", "You are not authorized to request the requested resource."),
    404: ("Not Found", "The requested resource was not found."),
    405: ("Method Not Allowed", "The request method is not recognized or permitted by the requested resource."),
    500: ("Server Error", "An internal error occurred."),
    501: ("Not Implemented", "The requested functionality has not been implemented."),
    503: ("Service Unavailable", "Service is being denied at this time."),
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
    invalid = b"%;&=#?/\"'"
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

def requrl(req):
    s = siteurl(req)
    if req.uri[0] != '/':
        raise Exception("Malformed local part when reconstructing URL")
    return siteurl(req) + req.uri[1:]

def parstring(pars={}, **augment):
    buf = ""
    for key in pars:
        if key in augment:
            val = augment[key]
            del augment[key]
        else:
            val = pars[key]
        if buf != "": buf += "&"
        buf += urlq(key) + "=" + urlq(str(val))
    for key in augment:
        if buf != "": buf += "&"
        buf += urlq(key) + "=" + urlq(str(augment[key]))
    return buf

def parurl(url, pars={}, **augment):
    qs = parstring(pars, **augment)
    if qs != "":
        return url + "?" + qs
    else:
        return url
