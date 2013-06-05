import sys, traceback
from . import env, req, proto

__all__ = ["restart"]

class restart(Exception):
    def handle(self, req):
        pass

def mangle(result):
    try:
        iter(result)
    except TypeError:
        pass
    else:
        return result
    return [str(result)]

def defaulterror(req, excinfo):
    from . import resp
    traceback.print_exception(*excinfo)
    raise resp.httperror(500)

def wraphandler(handler, excinfo):
    def wrapped(req):
        return handler(req, excinfo)
    wrapped.__wrapped__ = handler
    return wrapped

errorhandler = env.var(defaulterror)

def handle(req, startreq, handler):
    eh = errorhandler.val
    try:
        resp = [""]
        while True:
            try:
                resp = handler(req)
                break
            except restart as i:
                handler = i.handle
            except Exception as i:
                if eh is None:
                    raise
                handler = wraphandler(eh, sys.exc_info())
                eh = None
        req.commit(startreq)
        return resp
    finally:
        req.cleanup()

def handleenv(env, startreq, handler):
    if not "HTTP_HOST" in env:
        return proto.simpleerror(env, startreq, 400, "Bad Request", "Request must include Host header.")
    r = req.origrequest(env)
    return handle(r, startreq, handler)
