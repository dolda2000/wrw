import inspect
from . import req, dispatch, session, form

def wsgiwrap(callable):
    def wrapper(env, startreq):
        return dispatch.handle(req.origrequest(env), startreq, callable)
    return wrapper

def formparams(callable):
    def wrapper(req):
        data = form.formdata(req)
        spec = inspect.getargspec(callable)
        args = dict(data.items())
        args["req"] = req
        if not spec.keywords:
            for arg in list(args):
                if arg not in spec.args:
                    del args[arg]
        return callable(**args)
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
    def get(cls, req, create = True):
        sess = cls.sessdb().get(req)
        with sess.lock:
            try:
                return sess[cls]
            except KeyError:
                if not create:
                    return None
                ret = cls(req)
                sess[cls] = ret
                return ret

    @classmethod
    def sessdb(cls):
        return session.default.val

class autodirty(sessiondata):
    @classmethod
    def get(cls, req):
        ret = super().get(req)
        if "_is_dirty" not in ret.__dict__:
            ret.__dict__["_is_dirty"] = False
        return ret

    def sessfrozen(self):
        self.__dict__["_is_dirty"] = False

    def sessdirty(self):
        return self._is_dirty

    def __setattr__(self, name, value):
        super().__setattr__(name, value)
        if "_is_dirty" in self.__dict__:
            self.__dict__["_is_dirty"] = True

    def __delattr__(self, name):
        super().__delattr__(name, value)
        if "_is_dirty" in self.__dict__:
            self.__dict__["_is_dirty"] = True

class manudirty(object):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__dirty = False

    def sessfrozen(self):
        self.__dirty = False

    def sessdirty(self):
        return self.__dirty

    def dirty(self):
        self.__dirty = True
