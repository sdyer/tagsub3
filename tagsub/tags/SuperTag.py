

from .Tag import Tag
from .SaveOverrideTag import SaveOverrideTag
from .RootTag import RootTag
from ..exceptions import TagsubTemplateSyntaxError

class SuperTag(Tag):
	tag = "super"
	def __init__(self, tagchar, template):
		super().__init__(tagchar, template)
		self._parent = None
		self._overriddenValue = None
		self.closeTag()

	# Before we write the results of the parsed saveoverride tag back into the NamespaceStack (like we do with
	# saveraw), we need, when we hit the super tag, to pull the current value of the variable specified in
	# saveoverride and save a reference to it on the super tag (essentially the value). If it is simply text,
	# then it would be a ConstantValue. If it is a SaverawTag or SaveOverrideTag, then that should be the value of
	# super (or at least it should retain a reference to it) so when asked to format output, it can pass the request
	# into the referenced tag.

	def setReference(self, overriddenValue):
		# overriddenValue may be a str, a SaveOverrideTag or SaveRawTag or None
		self._overriddenValue = overriddenValue

	@property
	def parent(self):
		return self._parent

	@parent.setter
	def parent(self, a_parent):
		self._parent = a_parent
		while True:
			if isinstance(a_parent, RootTag):
				raise TagsubTemplateSyntaxError(f"Misplaced {self.tag} tag", tag=self)
			if isinstance(a_parent, SaveOverrideTag):
				a_parent.addSuperTagReference(self)
				break
			a_parent = a_parent.parent

	def format(self, outputFormatter):
		outputFormatter.markLineSuppressible()
		if isinstance(self._overriddenValue, Tag):
			# Assume a SaveRaw or SaveOverride
			outputFormatter.pushOutputBuffer()
			self._overriddenValue.formatAtReference(outputFormatter)
			value = outputFormatter.popOutputBuffer()
			outputFormatter.outputString(value)
		else:
			outputFormatter.outputString(str(self._overriddenValue) if self._overriddenValue is not None else "")
		outputFormatter.markLineSuppressible()
