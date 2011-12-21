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
        self.next()

    def __iter__(self):
        return self

    def next(self):
        if self._next is None:
            raise StopIteration()
        ret = self._next[0]
        try:
            self._next[:] = [self.bki.next()]
        except StopIteration:
            self._next = None
        return ret

    def close(self):
        if hasattr(self.bk, "close"):
            self.bk.close()

def handle(req, startreq, handler):
    try:
        resp = [""]
        while True:
            try:
                resp = iterproxy(handler(req))
                break
            except restart, i:
                handler = i.handle
        req.commit(startreq)
        return resp
    finally:
        req.cleanup()
