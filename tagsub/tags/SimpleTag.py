
from .Tag import Tag
from ..exceptions import InvalidTagKeyName
from html.entities import codepoint2name

class SimpleTag(Tag):
	tag = "simple"
	def __init__(self, tagchar, value, template):
		super().__init__(tagchar, template)
		self._value = value
		value.tag = self

		# Consume any additional trailing whitespace and the required ">"
		self.closeTag(optionalExceptionClass=InvalidTagKeyName, optionalExceptionMessage="Invalid tag name.")

	@staticmethod
	def escapeStringForHtml(strVal):
		def escapedChar(char):
			entity = codepoint2name.get(ord(char))
			return f"&{entity};" if entity else char
		return ''.join([escapedChar(c) for c in strVal])

	def format(self, outputFormatter):
		from .. import rawstr
		# Look up the value. If it is a string (already a string or
		#  saveeval), just substitute (doing HTML entity encoding as needed). If
		#  it is the parsed saveraw structure, call its format method.
		# Apparently we are considering SimpleTags as suppressible too.
		value = self._value.getValue(self._tagchar, outputFormatter)
		outputFormatter.markLineSuppressible()
		if self._template.doEncodeHtml and not isinstance(value, rawstr):
			outputFormatter.outputString(self.escapeStringForHtml(value))
		else:
			outputFormatter.outputString(value)
		outputFormatter.markLineSuppressible()