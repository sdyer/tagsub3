
from .Operator import Operator
class OrOperator(Operator):
	def __init__(self, leftOperand, rightOperand):
		super().__init__(leftOperand, rightOperand)

	def getValue(self, tagchar, outputFormatter):
		leftOperand, rightOperand = self._operands
		return (bool(leftOperand.getValue(tagchar, outputFormatter)) or
			bool(rightOperand.getValue(tagchar, outputFormatter)))
