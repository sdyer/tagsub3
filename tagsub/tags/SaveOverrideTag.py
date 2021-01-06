

from .TagContainer import TagContainer
from .values.Token import Token
from .values.Value import Value
from ..exceptions import InvalidTagKeyName

class SaveOverrideTag(TagContainer):
	tag = "saveoverride"
	def __init__(self, tagchar, template):
		super().__init__(tagchar, template)
		# Parse the name Token and validate. Must be a simple name, not an object attribute or implied loop var.
		token = Token(template)
		if token.attributeChain or token.impliedLoopVarName:
			raise InvalidTagKeyName("Must only have simple name for save tags", tag=self)
		self.value = Value.createValue(token, template, self)
		self.closeTag()
		self._superTagReferences = []

	def addSuperTagReference(self, superTag):
		self._superTagReferences.append(superTag)

	def formatAtReference(self, outputFormatter):
		super().format(outputFormatter)

	def format(self, outputFormatter):
		namespace = outputFormatter.rootMapping[self.tagchar]
		# When we hit it, saveraw tag does not get formatted into the output, nor do we walk the children and format
		# them. Instead, we save a reference to the tag. The Value object recognizes that we have a Tag and calls the
		# above formatAtReference to get it formatted into the output with the current NamespaceStack.
		outputFormatter.markLineSuppressible()
		overriddenValue = namespace.get(self.value._name)
		for superTag in self._superTagReferences:
			superTag.setReference(overriddenValue)
		namespace[self.value._name] = self

