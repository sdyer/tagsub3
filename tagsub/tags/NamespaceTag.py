
from .TagContainer import TagContainer
from .values.Token import Token
from .values.Value import Value
from ..exceptions import TagsubTemplateSyntaxError, TagsubTypeError

from collections.abc import Mapping

class NamespaceTag(TagContainer):
	tag="namespace"

	def __init__(self, tagchar, template):
		super().__init__(tagchar, template)

		self._value = Value.createValue(Token(template), template, self)
		self.closeTag()

	# FIXME The format will have a lot in common with the loop tag. Both will
	# put a dict (or optionally a callable) at the top of the namespace stack.
	def format(self, outputFormatter):
		namespaceMapping = self._value.getValue(self.tagchar, outputFormatter)
		if not isinstance(namespaceMapping, Mapping):
			raise TagsubTypeError("Namespace value must be a mapping", tag=self, outputFormatter=outputFormatter)
		outputFormatter.rootMapping[self.tagchar].push(namespaceMapping)
		super().format(outputFormatter)
		outputFormatter.rootMapping[self.tagchar].pop()
