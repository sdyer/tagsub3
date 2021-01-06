
from ...exceptions import InvalidTagKeyName
from ...exceptions import buildNonTagsubException
from ..Tag import Tag

# This will be used by any Tag that needs a lookup value. An operator can also reference two of these. The actual value will be looked up at run time from the template ChainMap namespace. This is only used for looked up values, not for implied loop variables, which are attributes retrieved from an enclosing loop tag.
class Value:
	def __init__(self, template, name, tag=None, attributeChain=None, loopTag=None, impliedLoopVar=None):
		self._template = template
		# Most tags get the value in their __init__ and can pass themselves in. The exception is SimpleTag, which will manually set it later.
		self.tag = tag
		# Name *might* be empty if this is an implied Loop Variable
		assert name or loopTag, "Must have at least one of name or loopTag"
		self._name = name
		self._attributeChain = attributeChain
		self._loopTag = loopTag
		self._impliedLoopVar = impliedLoopVar
		# loopTag implies we must have an impliedLoopVar. Otherwise, we *cannot* have an impliedLoopVar
		assert impliedLoopVar if loopTag else not impliedLoopVar

	def getValue(self, tagchar, outputFormatter):
		namespace = outputFormatter.rootMapping[tagchar]
		if self._impliedLoopVar:
			return self._loopTag.getImpliedLoopVar(self, outputFormatter)
		else:
			obj = namespace.get(self._name)
			if isinstance(obj, Tag):
				# Must be one of the save tags
				assert not self._attributeChain
				# TODO For saveeval or saveraw tags, we must format the children at some point (either at format time
				#  for saveeval, or when referenced in the case of saveraw, which is what happens here). The formatting of
				#  the children essentially needs its own OutputFormatter that we write to and get the result as the
				#  string we use for substitution.
				outputFormatter.pushOutputBuffer()
				obj.formatAtReference(outputFormatter)
				return outputFormatter.popOutputBuffer()
			if self._attributeChain and obj is not None:
				# TODO Handle name errors here more elegantly. Probably trap the attribute exception and raise an
				#  appropriate tagsub exception
				for attr in self._attributeChain:
					try:
						obj = getattr(obj, attr)
					except AttributeError as e:
						raise buildNonTagsubException(AttributeError, str(e),
													  tag=self.tag, template=None, outputFormatter=outputFormatter)

			returnVal = "" if obj is None else obj
			if self._template.is0False and returnVal == "0":
				return 0
			else:
				return returnVal

	@classmethod
	def createValue(cls, token, template, tag=None):
		if not token.tokenstr:
			name = None
			assert token.impliedLoopVarName
		else:
			name = token.tokenstr

		if token.impliedLoopVarName:
			# Search through enclosing LoopTags on the template TagStack until
			# find our match or hit the bottom of the stack.
			for index in range(1, len(template._tagStack) + 1):
				loopTag = template._tagStack[index]
				if loopTag.tag == "loop":
					if not name:
						# No name. Match first enclosing LoopTag
						break
					if name == loopTag._value._name and token.attributeChain == loopTag._value._attributeChain:
						# Matching Name, This is our LoopTag
						break
			else:
				# Really this is a "no matching loop tag"
				raise InvalidTagKeyName("No matching loop tag for implied loop variable", tag=tag, template=template)
		else:
			loopTag = None

		return cls(template, name, tag, token.attributeChain, loopTag, token.impliedLoopVarName)
