
from .Tag import Tag

class NullTag(Tag):
	def __init__(self, tagchar, template):
		super().__init__(tagchar, template)

		# Consume any additional trailing whitespace and the required ">"
		self.closeTag()

	def format(self, outputFormatter):
		# Placeholder here. Nothing to output
		pass
