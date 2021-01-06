
from .TagContainer import TagContainer
from .values.ConstantValue import ConstantValue

class ElseTag(TagContainer):
	tag = "else"

	@property
	def isBalancedTag(self):
		return False

	def __init__(self, tagchar, template):
		super().__init__(tagchar, template)

		# Consume any additional trailing whitespace and the required ">"
		self.closeTag()

	# I think this may work, since I think we just take the bool of _expression
	# We may need a constantValue we can use here.
	# TODO Check IfTagContainer to see how it references this attribute
		self._expression = ConstantValue(True)

	# Run time. This is for when it is being used in a case tag
	def matches(self, text, outputFormatter):
		return True

