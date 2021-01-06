
from .TagContainer import TagContainer
from collections import deque

# Will only be one for a template. Will be the top level parent of all tags.
# Only there to hold the top level children.
class RootTag(TagContainer):
	tag = None
	def __init__(self, tagchar, template):
		self._tagchar = tagchar
		self._template = template
		self._charpos = 0
		self._linenum = 0
		self._linepos = 0
		self._children = []
		# We will need this for blank line suppression, since we are not inheriting the TagContainer.__init__
		self._blankLineSuppressionCandidates = deque()
		self._maybeSupressible = True
		self._tagsOnLine = False

	def markLineSuppressible(self, outputFormatter):
		pass
