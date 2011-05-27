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

def handle(req, startreq, handler):
    try:
        resp = [""]
        while True:
            try:
                resp = handler(req)
                break
            except restart, i:
                handler = i.handle
        req.commit(startreq)
        return resp
    finally:
        req.cleanup()
