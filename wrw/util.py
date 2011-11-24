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
