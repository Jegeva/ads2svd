class DAPException(Exception):

    def __init__(self, description, cause=None):
        self.description = description
        self.cause = cause

    def getCause(self):
        return self.cause

    def __str__(self):
        msg = "DAPException: %s" % (self.description)
        if self.cause is not None:
            msg = msg + "\nCaused by:\n%s" % (self.cause.__str__())
        return msg

    def getMessage(self):
        return "DAPException: %s" % (self.description)
