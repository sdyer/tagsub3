
from .TagContainer import TagContainer
from .values.Token import Token
from .values.Value import Value
from .values.ConstantValue import ConstantValue
from ..exceptions import InvalidTagKeyName

class OptionTag(TagContainer):
	tag = "option"

	@property
	def isBalancedTag(self):
		return False

	def __init__(self, tagchar, template):
		super().__init__(tagchar, template)

		self._optionMatchValues = []
		while True:
			token = Token(template, isOptionValue=True)
			if token.isOptionLookup:
				matchValue = Value.createValue(token, template, tag=self)
			else:
				matchValue = ConstantValue(token.tokenstr)
			self._optionMatchValues.append(matchValue)

			char = next(template.templateIter)
			while char.isspace():
				char = next(template.templateIter)
			if char != ",":
				break
		if char != ">":
			raise InvalidTagKeyName("Invalid option tag", tag=self, template=template)

	# Run time. Needs reference to namespace stack and loop stack.
	def matches(self, text, outputFormatter):
		assert text is not None
		# In some cases this might not be a str.
		matchText = str(text)
		for value in self._optionMatchValues:
			if str(value.getValue(self.tagchar, outputFormatter)) == matchText:
				return True
		else:
			return False
