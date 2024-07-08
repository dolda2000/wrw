import threading, weakref

__all__ = ["environment", "root", "get", "binding", "var"]

class stack(object):
    __slots__ = ["env", "prev"]
    def __init__(self, env, prev):
        self.env = env
        self.prev = prev

class environment(object):
    __slots__ = ["parent", "map"]
    def __init__(self, parent=None):
        self.parent = parent
        self.map = weakref.WeakKeyDictionary()

    def get(self, var):
        if var in self.map:
            return self.map[var]
        if self.parent is None:
            return None
        return self.parent.get(var)

    def set(self, var, val):
        self.map[var] = val

    def __enter__(self):
        cur = context.env
        context.prev = stack(cur, context.prev)
        context.env = self
        return None

    def __exit__(self, *excinfo):
        prev = context.prev
        if prev is None:
            raise Exception("Unbalanced __enter__/__exit__")
        context.env = prev.env
        context.prev = prev.prev
        return False

root = environment()

class context(threading.local):
    env = root
    prev = None
context = context()

def get():
    return context.env

class binding(object):
    __slots__ = ["bindings"]
    def __init__(self, bindings):
        if isinstance(bindings, dict):
            bindings = list(bindings.items())
        self.bindings = bindings

    def __enter__(self):
        cur = context.env
        new = environment(cur)
        for var, val in self.bindings:
            new.map[var] = val
        context.prev = stack(cur, context.prev)
        context.env = new
        return None

    def __exit__(self, *excinfo):
        prev = context.prev
        if prev is None:
            raise Exception("Unbalanced __enter__/__exit__")
        context.env = prev.env
        context.prev = prev.prev
        return False

class var(object):
    __slots__ = ["__weakref__"]
    def __init__(self, default=None):
        if default is not None:
            root.map[self] = default

    @property
    def val(self):
        return context.env.get(self)

    def binding(self, val):
        return binding([(self, val)])

def boundvars(bindings, dynamic=[]):
    if isinstance(bindings, dict):
        bindings = list(bindings.items())
    if isinstance(dynamic, dict):
        dynamic = list(dynamic.items())
    def dec(fun):
        def wrapper(*args, **kwargs):
            calc = bindings
            if dynamic:
                calc = list(calc)
                for var, val in dynamic:
                    calc.append((var, val()))
            with binding(bindings):
                return fun(*args, **kwargs)
        wrapper.__wrapped__ = callable
        return wrapper
    return dec
