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
