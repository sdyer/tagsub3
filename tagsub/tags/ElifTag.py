
from .IfTag import IfTag
from ..exceptions import TagsubTemplateSyntaxError

# This should inherit all useful behavior from IfTag
class ElifTag(IfTag):
	tag = "elif"

	@property
	def parent(self):
		return self._parent

	@parent.setter
	def parent(self, a_parent):
		from .IfTagContainer import IfTagContainer
		if not isinstance(a_parent, IfTagContainer):
			raise TagsubTemplateSyntaxError(f"Misplaced {self.tag} tag", tag=self)
