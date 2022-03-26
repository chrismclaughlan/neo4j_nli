class Neo4jNLIException(Exception):
    def __init__(self, message, is_fatal=False, exception=None):
        super().__init__(message)
        self.isFatal = is_fatal
        self.exceptionDetails = ""
        self.exceptionType = ""
        if exception is not None:
            self.exceptionDetails = exception.args[0]
            self.exceptionType = type(exception).__name__

    def __str__(self):
        details = (". Details (type: " + self.exceptionType + "):\n" + self.exceptionDetails) if  self.exceptionDetails  else ""
        fatal = " Fatal" if self.isFatal else ""
        return "Neo4jNLI" + fatal + " Error Occurred! " + self.args[0] + details


if __name__ == "__main__":
    try:
        raise Neo4jNLIException("12345", False)
    except Neo4jNLIException as e:
        print(e)