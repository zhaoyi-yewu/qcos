class DeveiceDefineError(Exception):

    def __init__(self, msg):
        self.code = 401
        self.msg = msg
        
class DeveiceConnectionError(Exception):
    def __init__(self, msg):
        self.code = 402
        self.msg = msg
        
class DeveiceCloseError(Exception):
    def __init__(self, msg):
        self.code = 403
        self.msg = msg

class DeveiceParameterError(Exception):
    def __init__(self, msg):
        self.code = 404
        self.msg = msg

class DeveiceAccessError(Exception):
    def __init__(self, msg):
        self.code = 405
        self.msg = msg