from __future__ import with_statement
import os, threading
from mako import template, lookup, filters
import util, form, session, env

# It seems Mako isn't thread-safe.
makolock = threading.Lock()

class liblookup(lookup.TemplateLookup):
    def __init__(self, *args, **kwargs):
        lookup.TemplateLookup.__init__(self, *args, **kwargs)

    def adjust_uri(self, uri, relativeto):
        return uri

libdirs = []
homedir = os.getenv("HOME")
if homedir is not None:
    usrdir = os.path.join(homedir, "wmako")
    if os.path.exists(usrdir):
        libdirs.append(usrdir)
libdirs.append(os.path.join(os.path.dirname(__file__), "makolib"))
cachedir = os.path.join("/tmp/", "mako-" + str(os.getuid()))
defargs = {"output_encoding": "utf-8",
           "input_encoding": "utf-8",
           "default_filters": ["decode.utf8"],
           "module_directory": cachedir,
    }

def makelib(init=liblookup, directories=[], **kwargs):
    ad = dict(defargs)
    ad.update(kwargs)
    return init(directories = libdirs + directories, **ad)

lib = env.var(makelib())

if not os.path.exists(cachedir):
    os.mkdir(cachedir)
def handle(req, filename, **kw):
    with makolock:
        tt = template.Template(filename = filename, lookup = lib.val, **defargs)
    req.ohead["Content-Type"] = "text/html; charset=utf-8"
    return [tt.render(request = req, **kw)]

@util.wsgiwrap
def application(req):
    return handle(req, req.filename,
                  form = form.formdata(req),
                  session = session.get(req))
