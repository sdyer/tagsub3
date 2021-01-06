
class Operator:
	def __init__(self, *operands):
		# Each operand can be a Value or an Operator. We expect to hit the
		# value property for each and let them recursively look things up.
		self._operands = operands

	def getValue(self, tagchar, outputFormatter):
		raise NotImplementedError()
