
from .Operator import Operator
class NotOperator(Operator):
	def __init__(self, operand):
		super().__init__(operand)

	def getValue(self, tagchar, outputFormatter):
		(operand, ) = self._operands
		return not bool(operand.getValue(tagchar, outputFormatter))
