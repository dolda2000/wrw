import inspect, math
from . import req, dispatch, session, form, resp, proto

def wsgiwrap(callable):
    def wrapper(env, startreq):
        return dispatch.handleenv(env, startreq, callable)
    wrapper.__wrapped__ = callable
    return wrapper

def formparams(callable):
    sig = inspect.signature(callable)
    haskw = inspect.Parameter.VAR_KEYWORD in (par.kind for par in sig.parameters.values())
    def wrapper(req):
        try:
            data = dict(form.formdata(req).items())
        except IOError:
            raise resp.httperror(400, "Invalid request", "Form data was incomplete")
        
        data["req"] = req
        if haskw:
            args = data
        else:
            args = {}
            for par in sig.parameters.values():
                if par.name in data:
                    args[par.name] = data[par.name]
        for par in sig.parameters.values():
            if par.default is inspect.Parameter.empty and par.name not in args:
                raise resp.httperror(400, "Missing parameter", ("The query parameter `", resp.h.code(par.name), "' is required but not supplied."))
        return callable(**args)
    wrapper.__wrapped__ = callable
    return wrapper

class funplex(object):
    def __init__(self, *funs, **nfuns):
        self.dir = {}
        self.dir.update(((self.unwrap(fun).__name__, fun) for fun in funs))
        self.dir.update(nfuns)

    @staticmethod
    def unwrap(fun):
        while hasattr(fun, "__wrapped__"):
            fun = fun.__wrapped__
        return fun

    def __call__(self, req):
        if req.pathinfo == "":
            if "__root__" in self.dir:
                return self.dir["__root__"](req)
            raise resp.redirect(req.uriname + "/")
        if req.pathinfo[:1] != "/":
            raise resp.notfound()
        p = req.pathinfo[1:]
        if p == "":
            p = "__index__"
            bi = 1
        else:
            p = p.partition("/")[0]
            bi = len(p) + 1
        if p in self.dir:
            sreq = req.shift(bi)
            sreq.selfpath = req.pathinfo[1:]
            return self.dir[p](sreq)
        raise resp.notfound()

    def add(self, fun):
        self.dir[self.unwrap(fun).__name__] = fun
        return fun

    def name(self, name):
        def dec(fun):
            self.dir[name] = fun
            return fun
        return dec

def persession(data=None):
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
        wrapper.__wrapped__ = callable
        return wrapper
    return dec

class preiter(object):
    __slots__ = ["bk", "bki", "_next"]
    end = object()
    def __init__(self, real):
        self.bk = real
        self.bki = iter(real)
        self._next = None
        self.__next__()

    def __iter__(self):
        return self

    def __next__(self):
        if self._next is self.end:
            raise StopIteration()
        ret = self._next
        try:
            self._next = next(self.bki)
        except StopIteration:
            self._next = self.end
        return ret

    def close(self):
        if hasattr(self.bk, "close"):
            self.bk.close()

def pregen(callable):
    def wrapper(*args, **kwargs):
        return preiter(callable(*args, **kwargs))
    wrapper.__wrapped__ = callable
    return wrapper

def stringwrap(charset):
    def dec(callable):
        @pregen
        def wrapper(*args, **kwargs):
            for string in callable(*args, **kwargs):
                yield string.encode(charset)
        wrapper.__wrapped__ = callable
        return wrapper
    return dec

class sessiondata(object):
    @classmethod
    def get(cls, req, create=True):
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
        super().__init__(name, bases, tdict)
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

class specdirty(sessiondata, metaclass=specclass):
    __slots__ = ["session", "__sslots__", "_is_dirty"]
    
    def __specinit__(self):
        pass

    @staticmethod
    def __new__(cls, req, sess):
        self = super().__new__(cls)
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

def datecheck(req, mtime):
    if "If-Modified-Since" in req.ihead:
        rtime = proto.phttpdate(req.ihead["If-Modified-Since"])
        if rtime is not None and rtime >= math.floor(mtime):
            raise resp.unmodified()
    req.ohead["Last-Modified"] = proto.httpdate(mtime)
