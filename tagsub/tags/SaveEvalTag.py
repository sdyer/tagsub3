
from .TagContainer import TagContainer
from .values.Token import Token
from .values.Value import Value
from ..exceptions import InvalidTagKeyName


class SaveEvalTag(TagContainer):
	tag = "saveeval"
	def __init__(self, tagchar, template):
		super().__init__(tagchar, template)

		# Parse the name Token and validate. Must be a simple name, not an object attribute or implied loop var.
		token = Token(template)
		if token.attributeChain or token.impliedLoopVarName:
			raise InvalidTagKeyName("Must only have simple name for save tags", tag=self)
		self.value = Value.createValue(token, template, self)
		self.closeTag()

	def format(self, outputFormatter):
		# Create a new output buffer in the OutputFormatter at this point and then format the
		#  children into that. Then we need to get the results and save that into the NamespaceStack.
		outputFormatter.markLineSuppressible()
		outputFormatter.pushOutputBuffer()
		super().format(outputFormatter)
		saveValue = outputFormatter.popOutputBuffer()
		namespace = outputFormatter.rootMapping[self.tagchar]
		namespace[self.value._name] = saveValue