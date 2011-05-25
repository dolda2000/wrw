import cgi

__all__ = ["formdata"]

class formwrap(object):
    def __init__(self, req):
        if req.ihead["Content-Type"] == "application/x-www-form-urlencoded":
            self.cf = cgi.parse(environ = req.env, fp = req.env["wsgi.input"])
        else:
            self.cf = cgi.parse(environ = req.env)

    def __getitem__(self, key):
        return self.cf[key][0]

    def get(self, key, default = ""):
        if key in self:
            return self.cf[key][0]
        return default

    def __contains__(self, key):
        return key in self.cf and len(self.cf[key]) > 0

    def __iter__(self):
        return iter(self.cf)

    def items(self):
        def iter():
            for key, list in self.cf.items():
                for val in list:
                    yield key, val
        return list(iter())

    def keys(self):
        return self.cf.keys()

    def values(self):
        return [val for key, val in self.items()]

def formdata(req):
    return req.item(formwrap)
