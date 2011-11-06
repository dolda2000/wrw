statusinfo = {
    400: ("Bad Request", "Your issued HTTP request is invalid."),
    403: ("Forbidden", "You are not authorized to view the requested resource."),
    404: ("Not Found", "The requested resource was not found."),
    500: ("Server Error", "An internal error occurred.")
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
    return time.mktime(time.strptime(dstr, "%a, %d %b %Y %H:%M:%S")) - tz - time.altzone

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

def urlq(url):
    ret = ""
    for c in url:
        if c == "&" or c == "=" or c == "#" or c == "?" or c == "/" or (ord(c) <= 32):
            ret += "%%%02X" % ord(c)
        else:
            ret += c
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

def consurl(proto, host, local, query = ""):
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

def requrl(req):
    host = req.ihead.get("Host", None)
    if host is None:
        raise Exception("Could not reconstruct URL because no Host header was sent")
    proto = "http"
    if req.https:
        proto = "https"
    if req.uri[0] != '/':
        raise Exception("Malformed local part when reconstructing URL")
    return "%s://%s%s" % (proto, host, req.uri)

def parstring(pars = {}, **augment):
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
