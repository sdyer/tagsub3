
from .TagAlternateChoice import TagAlternateChoice
from .OptionTag import OptionTag
from .ElseTag import ElseTag
from .values.Token import Token
from .values.Value import Value
from ..exceptions import TagsubTemplateSyntaxError

class CaseTag(TagAlternateChoice):
	tag="case"

	def __init__(self, tagchar, template):
		super().__init__(tagchar, template)

		token = Token(template)
		self.value = Value.createValue(token, template, self)
		self.closeTag()

	def addChild(self, childNode):
		if isinstance(childNode, (OptionTag, ElseTag)):
			self.addAlternate(childNode)
		else:
			super().addChild(childNode)

	def addAlternate(self, alternateChoice):
		# The above addChild code does not allow any other tags.
		assert isinstance(alternateChoice, (OptionTag, ElseTag))
		if self._alternateChoices:
			# If we have an ElseTag, we cannot add any more
			if isinstance(self._alternateChoices[-1], ElseTag):
				raise TagsubTemplateSyntaxError("Misplaced %s tag" % alternateChoice.tag, tag=alternateChoice)
		super().addAlternate(alternateChoice)

	def chooseAlternate(self, outputFormatter):
		# TODO Based on the current template pageDict, which I assume we have
		# access to here, ask each of the alternate choices if they are true,
		# stopping on the first one. If we hit an else, it always claims to be
		# true.
		# XXX I think we walk through each option, pass it our Value and see if
		# they match. An else tag will always claim to match. Get the contents
		# of the matching alternate choice.
		for choice in self._alternateChoices:
			if choice.matches(self.value.getValue(self.tagchar, outputFormatter), outputFormatter):
				return choice
