
from . import TagContainer
from .text.TextNode import Line
from .text.CommentNode import CommentNode
from .text.TagsubCommentNode import TagsubCommentNode
from ..exceptions import TagsubTemplateSyntaxError

class TagAlternateChoice(TagContainer.TagContainer):
	def __init__(self, tagchar, template):
		super().__init__(tagchar, template)
		# Create alternate choice structure.
		self._alternateChoices = []

	def addAlternate(self, alternateChoice):
		if self.tagchar != alternateChoice.tagchar:
			raise TagsubTemplateSyntaxError("Mismatched tagchar for %s tag" % alternateChoice.tag, tag=alternateChoice)
		self._alternateChoices.append(alternateChoice)
		# FIXME Verify this is actually workable and that IfTagContainer and CaseTag do not need different code to do tracebacks correctly
		alternateChoice.parent = self

	def addChild(self, node):
		if not self._alternateChoices:
			# I think this can only happen with a case tag between it and the
			# first option tag.
			if isinstance(node, Line) or isinstance(node, (TagsubCommentNode, CommentNode)):
				return
			else:
				raise TagsubTemplateSyntaxError("Misplaced tag", tag=node)
		else:
			self._alternateChoices[-1].addChild(node)

	# These methods may be implemented entirely differently for the two
	# subclasses: IfTagContainer and CaseTag
	def chooseAlternate(self, outputFormatter):
		raise NotImplementedError()

	def format(self, outputFormatter):
		activeAlternate = self.chooseAlternate(outputFormatter)
		if activeAlternate:
			activeAlternate.format(outputFormatter)
