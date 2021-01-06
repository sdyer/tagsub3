from ..exceptions import TagsubTemplateSyntaxError

class Tag:
	def __init__(self, tagchar, template):
		# Base class for other tag types.
		# No child tags.
		self._tagchar = tagchar
		self._template = template
		self._charpos = template.templateIter._lastTagCharpos
		self._linenum = template.templateIter._lastTagLinenum
		self._linepos = template.templateIter._lastTagLinepos

	@property
	def tagchar(self):
		return self._tagchar
	@property
	def charpos(self):
		return self._charpos
	@property
	def linenum(self):
		return self._linenum
	@property
	def linepos(self):
		return self._linepos

	@property
	def isBalancedTag(self):
		return False

	def closeTag(self, optionalExceptionClass=None, optionalExceptionMessage=None):
		# Consume any whitespace and the closing '>' character. Raise a
		# TagsubTemplateSyntaxError if we do not find that. All tags may use
		# this to do the common behavior of getting past the close of the tag.
		char = next(self._template.templateIter)
		while char.isspace():
			char = next(self._template.templateIter)

		if char != ">":
			if optionalExceptionMessage:
				msg = optionalExceptionMessage
			else:
				msg = "Invalid {self.tag} tag."
			if optionalExceptionClass:
				excClass = optionalExceptionClass
			else:
				excClass = TagsubTemplateSyntaxError
			raise excClass(msg.format(**locals()), tag=self)
