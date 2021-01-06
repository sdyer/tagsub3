
import collections.abc

from .TagContainer import TagContainer
from .values.Token import Token
from .values.Value import Value
from ..exceptions import InvalidTagKeyName
from ..exceptions import buildNonTagsubException

def loopTagId():
	idVal = 1
	while True:
		yield idVal
		idVal += 1
loopTagIdIterator = loopTagId()

class LoopTag(TagContainer):
	tag="loop"

	def __init__(self, tagchar, template):
		super().__init__(tagchar, template)

		self.loopId = next(loopTagIdIterator)
		self._value = Value.createValue(Token(template), template, self)
		self.closeTag()

	def setLoopVars(self, index, length, obj, outputFormatter):
		if self.loopId not in outputFormatter.loopTagData:
			outputFormatter.loopTagData[self.loopId] = {"length": length}
		loopDataDict = outputFormatter.loopTagData[self.loopId]
		# Update (or initialize) the implied loop vars.
		# In the C code, we use int values of 1 and 0, not bool True and False.
		loopDataDict["isFirst"] = int(index == 0)
		# If no length, this will always be False
		loopDataDict["isLast"] = int(index+1 == length)
		loopDataDict["isOdd"] = int(index & 1 == 0)
		loopDataDict["isEven"] = int(index & 1 != 0)
		loopDataDict["index0"] = index
		loopDataDict["index"] = index + 1
		loopDataDict["rindex0"] = length - index - 1 if length is not None else None
		loopDataDict["rindex"] = length - index if length is not None else None
		# TODO A proposed extension I had was to allow referencing the object
		# of a loop tag directly and dereference attributes on it. This would
		# require some more specialized syntax for  the Value object. Once we
		# added that behavior in Value, though, it should work automatically.
		# loopDataDict["object"] = obj

	def resetLoopVars(self, outputFormatter):
		if self.loopId in outputFormatter.loopTagData:
			del outputFormatter.loopTagData[self.loopId]

	def getImpliedLoopVar(self, loopVarValue, outputFormatter):
		loopVarName = loopVarValue._impliedLoopVar
		loopDataDict = outputFormatter.loopTagData[self.loopId]
		if loopVarName in loopDataDict:
			return loopDataDict[loopVarName]
		else:
			raise InvalidTagKeyName("Invalid implied loop var name", tag=loopVarValue.tag, outputFormatter=outputFormatter)

	def format(self, outputFormatter):
		# TODO Loop through the dicts in our sequence. The might not need to be
		# dicts if we treat them as objects (obj.xxx ??)
		loopSequence = self._value.getValue(self._tagchar, outputFormatter)
		if isinstance(loopSequence, collections.abc.Sequence):
			# We have a known length and a rindex property (reverse index)
			length = len(loopSequence)
		elif isinstance(loopSequence, collections.abc.Iterable):
			# We have most everything else.
			length = None
		elif not loopSequence:
			loopSequence = []
			length = 0
		else:
			# Since we have not entered the loop sequence yet (not a sequence), leave off outputFormatter so it won't try building the dynamic portion.
			raise buildNonTagsubException(TypeError, "Invalid Sequence for loop tag", tag=self, template=None)

		# LoopTag is special in that it needs to preserve its internal scratch space over all the iterations,
		# which would normally get lost when it pops the previous iteration mapping off of the NamespaceStack. So,
		# we pass it in each iteration
		scratchSpace = {}
		for index, obj in enumerate(loopSequence):
			self.setLoopVars(index, length, obj, outputFormatter)
			if isinstance(obj, collections.abc.Mapping):
				outputFormatter.rootMapping[self._tagchar].push(obj)#), scratchSpace)
				super().format(outputFormatter)
				outputFormatter.rootMapping[self._tagchar].pop()
			else:
				super().format(outputFormatter)
		self.resetLoopVars(outputFormatter)

