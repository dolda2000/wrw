from __future__ import with_statement
import inspect
import req, dispatch, session, form

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
        if not spec[2]:
            for arg in list(args):
                if arg not in spec[0]:
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
                ret = cls(req, sess)
                sess[cls] = ret
                return ret

    @classmethod
    def sessdb(cls):
        return session.default.val

class autodirty(sessiondata):
    @classmethod
    def get(cls, req):
        ret = super(autodirty, cls).get(req)
        if "_is_dirty" not in ret.__dict__:
            ret.__dict__["_is_dirty"] = False
        return ret

    def sessfrozen(self):
        self.__dict__["_is_dirty"] = False

    def sessdirty(self):
        return self._is_dirty

    def __setattr__(self, name, value):
        super(autodirty, self).__setattr__(name, value)
        if "_is_dirty" in self.__dict__:
            self.__dict__["_is_dirty"] = True

    def __delattr__(self, name):
        super(autodirty, self).__delattr__(name, value)
        if "_is_dirty" in self.__dict__:
            self.__dict__["_is_dirty"] = True

class manudirty(object):
    def __init__(self, *args, **kwargs):
        super(manudirty, self).__init__(*args, **kwargs)
        self.__dirty = False

    def sessfrozen(self):
        self.__dirty = False

    def sessdirty(self):
        return self.__dirty

    def dirty(self):
        self.__dirty = True

class specslot(object):
    __slots__ = ["nm", "idx", "dirty"]
    unbound = object()
    
    def __init__(self, nm, idx, dirty):
        self.nm = nm
        self.idx = idx
        self.dirty = dirty

    @staticmethod
    def slist(ins):
        # Avoid calling __getattribute__
        return specdirty.__sslots__.__get__(ins, type(ins))

    def __get__(self, ins, cls):
        val = self.slist(ins)[self.idx]
        if val is specslot.unbound:
            raise AttributeError("specslot %r is unbound" % self.nm)
        return val

    def __set__(self, ins, val):
        self.slist(ins)[self.idx] = val
        if self.dirty:
            ins.dirty()

    def __delete__(self, ins):
        self.slist(ins)[self.idx] = specslot.unbound
        ins.dirty()

class specclass(type):
    def __init__(self, name, bases, tdict):
        super(specclass, self).__init__(name, bases, tdict)
        sslots = set()
        dslots = set()
        for cls in self.__mro__:
            css = cls.__dict__.get("__saveslots__", ())
            sslots.update(css)
            dslots.update(cls.__dict__.get("__dirtyslots__", css))
        self.__sslots_l__ = list(sslots)
        self.__sslots_a__ = list(sslots | dslots)
        for i, slot in enumerate(self.__sslots_a__):
            setattr(self, slot, specslot(slot, i, slot in dslots))

class specdirty(sessiondata):
    __metaclass__ = specclass
    __slots__ = ["session", "__sslots__", "_is_dirty"]
    
    def __specinit__(self):
        pass

    @staticmethod
    def __new__(cls, req, sess):
        self = super(specdirty, cls).__new__(cls)
        self.session = sess
        self.__sslots__ = [specslot.unbound] * len(cls.__sslots_a__)
        self.__specinit__()
        self._is_dirty = False
        return self

    def __getnewargs__(self):
        return (None, self.session)

    def dirty(self):
        self._is_dirty = True

    def sessfrozen(self):
        self._is_dirty = False

    def sessdirty(self):
        return self._is_dirty

    def __getstate__(self):
        ret = {}
        for nm, val in zip(type(self).__sslots_a__, specslot.slist(self)):
            if val is specslot.unbound:
                ret[nm] = False, None
            else:
                ret[nm] = True, val
        return ret

    def __setstate__(self, st):
        ss = specslot.slist(self)
        for i, nm in enumerate(type(self).__sslots_a__):
            bound, val = st.pop(nm, (False, None))
            if not bound:
                ss[i] = specslot.unbound
            else:
                ss[i] = val
