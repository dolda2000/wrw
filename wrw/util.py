import req, dispatch

def wsgiwrap(callable):
    def wrapper(env, startreq):
        return dispatch.handle(req.request(env), startreq, callable)
    return wrapper
