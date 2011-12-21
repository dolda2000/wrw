from . import req, dispatch, session

def wsgiwrap(callable):
    def wrapper(env, startreq):
        return dispatch.handle(req.origrequest(env), startreq, callable)
    return wrapper

def persession(data = None):
    def dec(callable):
        def wrapper(req):
            sess = session.get(req)
            if callable not in sess:
                if data is None:
                    sess[callable] = callable()
                else:
                    if data not in sess:
                        sess[data] = data()
                    sess[callable] = callable(data)
            return sess[callable].handle(req)
        return wrapper
    return dec

class sessiondata(object):
    @classmethod
    def get(cls, req):
        sess = cls.sessdb().get(req)
        with sess.lock:
            try:
                return sess[cls]
            except KeyError:
                ret = cls(req)
                ret._is_dirty = [False]
                sess[cls] = ret
                return ret

    @classmethod
    def sessdb(cls):
        return session.default

    def sessfrozen(self):
        self._is_dirty[:] = [False]

    def sessdirty(self):
        return self._is_dirty[0]

    def __setattr__(self, name, value):
        if hasattr(self, "_is_dirty"):
            self._is_dirty[:] = [True]
        super().__setattr__(name, value)

    def __delattr__(self, name):
        super().__delattr__(name)
        self._is_dirty[:] = [True]
