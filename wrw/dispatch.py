import sys, traceback
from . import env

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

class iterproxy(object):
    # Makes sure iter(real).next() is called immediately, in order to
    # let generator code run.
    def __init__(self, real):
        self.bk = real
        self.bki = iter(real)
        self._next = [None]
        self.__next__()

    def __iter__(self):
        return self

    def __next__(self):
        if self._next is None:
            raise StopIteration()
        ret = self._next[0]
        try:
            self._next[:] = [self.bki.__next__()]
        except StopIteration:
            self._next = None
        return ret

    def close(self):
        if hasattr(self.bk, "close"):
            self.bk.close()

def defaulterror(req, excinfo):
    from . import resp
    traceback.print_exception(*excinfo)
    raise resp.httperror(500)

def wraphandler(handler, excinfo):
    def wrapped(req):
        return handler(req, excinfo)
    return wrapped

errorhandler = env.var(defaulterror)

def handle(req, startreq, handler):
    eh = errorhandler.val
    try:
        resp = [""]
        while True:
            try:
                resp = iterproxy(handler(req))
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
