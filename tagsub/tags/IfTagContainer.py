from .TagAlternateChoice import TagAlternateChoice
from .IfTag import IfTag
from .ElifTag import ElifTag
from .ElseTag import ElseTag
from ..exceptions import TagsubTemplateSyntaxError

class IfTagContainer(TagAlternateChoice):
	tag = "if"

	def __init__(self, tagchar, template):
		super().__init__(tagchar, template)

		# The main thing to do here is construct a child IfTag and let it parse the expression and add it to our alternate choices.
		# create an IfTag here and add it.
		self.addAlternate(IfTag(tagchar, template))

	def addChild(self, childNode):
		if isinstance(childNode, (ElifTag, ElseTag)):
			self.addAlternate(childNode)
		else:
			super().addChild(childNode)

	def addAlternate(self, alternateChoice):
		if self._alternateChoices:
			assert isinstance(alternateChoice, (ElifTag, ElseTag))
			# We have a first choice (which must be an IfTag). All that is possible is ElifTag or ElseTag
			if isinstance(self._alternateChoices[-1], ElseTag):
				raise TagsubTemplateSyntaxError("Misplaced %s tag" % alternateChoice.tag, tag=alternateChoice)
		else:
			# Empty. IfTag must be added first (from the constructor above).
			assert isinstance(alternateChoice, IfTag)
		super().addAlternate(alternateChoice)

	# Runtime
	def chooseAlternate(self, outputFormatter):
		# Based on the current template pageDict, which I assume we have
		# access to here, ask each of the alternate choices if they are true,
		# stopping on the first one. If we hit an else, it always claims to be
		# true.
		for choice in self._alternateChoices:
			if bool(choice._expression.getValue(self.tagchar, outputFormatter)):
				return choice
