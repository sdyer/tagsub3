from io import StringIO

from .CommentNode import CommentNode
from ..TagContainer import TagContainer
from ...exceptions import TagsubTemplateSyntaxError


# Refactored in an incompatible way (we never used tagsub comments much anyway). Our new behavior is an open "tag"
#  of <@!--> with whatever we want commented out between the open and close "tags". The close tag would look like
#  <@-->. This would make us a TagContainer subclass.s
class TagsubCommentNode(TagContainer):
	tag = "comment"
	def __init__(self, tagchar, template):
		super().__init__(tagchar, template)

		# Consume any additional trailing whitespace and the required ">"
		self.closeTag()

	def validateCloseTag(self, tagchar, template):
		if tagchar != self._tagchar:
			raise TagsubTemplateSyntaxError("Misplaced tag", template=template)
		try:
			char = next(template.templateIter)
			char2 = next(template.templateIter)
			if char != "-" or char2 != "-":
				raise TagsubTemplateSyntaxError("Illegal tag name", template=template)

			char = next(template.templateIter)
			while char.isspace():
				char = next(template.templateIter)
		except StopIteration:
			raise TagsubTemplateSyntaxError("Invalid close tag", template=template)
		if char != ">":
			raise TagsubTemplateSyntaxError("Invalid close tag", template=template)

	def format(self, outputFormatter):
		# We always suppress tagsub comments. We do need to communicate with the outputFormatter that we are being
		# suppressed so it can deal with blank line suppression.
		outputFormatter.markLineSuppressible()
