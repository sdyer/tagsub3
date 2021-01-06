from .TagContainer import TagContainer
from .values.ExpressionParser import ExpressionParser

class IfTag(TagContainer):
	tag = "if"

	@property
	def isBalancedTag(self):
		return False

	def __init__(self, tagchar, template):
		super().__init__(tagchar, template)
		# We now can start parsing the expression from template. Elif will be an almost unmodified subclass

		# Use the ExpressionParser class. This could end up being a simple
		# value, but I think we let the Expression parser take care of that.

		parser = ExpressionParser(template, self)
		self._expression = parser.expression

