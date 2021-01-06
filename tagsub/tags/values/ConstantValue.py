
# Exists primarily to allow a constant value that has the same interface as Value
class ConstantValue:
    def __init__(self, value):
        self._value = value

    def getValue(self, tagchar, outputFormatter):
        return self._value