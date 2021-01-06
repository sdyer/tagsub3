from numbers import Number

from .tags import IfTagContainer
from .tags import ElifTag
from .tags import ElseTag
from .tags import CaseTag
from .tags import OptionTag
from .tags import LoopTag
from .tags import NamespaceTag
from .tags.NullTag import NullTag
from .tags import SaveEvalTag
from .tags import SaveRawTag
from .tags import SaveOverrideTag
from .tags import SuperTag
from .tags import SimpleTag
from .tags.Tag import Tag

from .tags.RootTag import RootTag
from .tags.text.TagsubCommentNode import TagsubCommentNode

from .tags.values.Token import Token
from .tags.values.Value import Value
from .tags.text.TextNode import TextNode, Line
from .tags.text.CommentNode import CommentNode
from .exceptions import TagsubTemplateSyntaxError, TagStackOverflowError
from .exceptions import TagcharSequenceMismatchError
from .exceptions import TagsubEofParsingTokenError

from collections import ChainMap, deque
from collections.abc import Sequence, Mapping
from io import StringIO
from .constants import max_nested_tag_depth

# TagStack gets used during parsing/compiling the template
from .util.Stack import Stack


class TagStack:
    def __init__(self, depth=None):
        self.__stack = deque()
        self._depth = depth

    def push(self, tag):
        assert isinstance(tag, Tag)
        if self._depth and len(self.__stack) > self._depth:
            raise TagStackOverflowError("Tag Stack Overflow", tag=tag)
        self.__stack.append(tag)

    def pop(self):
        # Let it raise the IndexError for now. If we need we can catch it and
        # raise something appropriate, but it should never happen.
        return self.__stack.pop()

    @property
    def top(self):
        # We should probably check to make sure we still have our RootTag our
        # logic should prevent looking at the top when it is empty, because pop
        # will fail earlier than that.
        return self.__stack[-1]

    def __len__(self):
        return len(self.__stack)

    def __getitem__(self, index):
        # For a stack, we are looking from the end
        assert index > 0
        return self.__stack[-index]


# implement as a collections.ChainMap
# XXX Maybe subclass so any set operations always happen at the root level.
#  - So, namespaceStack = ChainMap(root)
#  - to push, do: namespaceStack = namespaceStack.new_child(namespace)
#  - to  pop, do: namespaceStack = namespaceStack.parents
# XXX NamespaceStack only gets used during formatting.
class NamespaceStack:
    def __init__(self, rootMap):
        # FIXME We don't really treat the case where we pass in a callable, but
        #   want to set a value. And for namespace stacks, we need to deal with
        #   the situation that any mapping might be a callable instead. (Or do
        #   we really need to support this use case?)
        # if isinstance(rootMap, operations.Callable):
        # There is always the initial map for save tags to store values in.
        self._rootMap = rootMap
        #self._map = ChainMap({}, rootMap)
        self._map = ChainMap(rootMap)

    # For each namespace added, we add a new scratch space for save tags. This has the net effect that for every
    # namespace we enter (including loop tags), we can override variable names, but see the original value when we
    # exit back out of the nested namespaces.
    # FIXME This currently causes a few tests to fail. We may want to set
    #  values inside a loop and have them available outside the loop (from the last iteration). We might need a
    #  separate notation to explicitly set a value at a global level instead of locally (or be sure not to make a loop
    #  an actual separate settable namespace, although it does need to be a separate readable namespace)
    #def push(self, mapping, scratchSpace={}):
    def push(self, mapping):
        assert isinstance(mapping, Mapping)
        #self._map = self._map.new_child(mapping).new_child(scratchSpace)
        self._map = self._map.new_child(mapping)

    def pop(self):
        # With each namespace having its own scratch namespace, we must pop two entries off (for the two we previously added)
        #scratchSpace = self._map.maps[0]
        self._map = self._map.parents#.parents
        #return scratchSpace

    def __setitem__(self, key, value):
        #self._map[key] = value
        self._rootMap[key] = value

    def __getitem__(self, key):
        return self._map[key]

    def get(self, key, default=None):
        return self._map.get(key, default)

    def __len__(self):
        return len(self._map)


# TODO Need to modify OutputFormatter to be intrinsically line oriented. We will be getting output a line at a time,
#  courtesy of TextNode. We do not care about simple substitution having lines, because the only reason we are
#  tracking lines is for blank line suppression. In particular, each line of text starts as a potential suppressed
#  line. If we see no tags on that line, then we do not suppress. If we have non-whitespace, we do not suppress. We
#  only suppress if the line has a tags that produce no output and the rest of the text is white space only.

# TODO Based on that, we should be able to prepare for blank line suppression entirely in the parsing stage. The
#  BlankLine container will have the blank line text nodes and tags, suppressing if the tags produce no output,
#  and outputting everything if they do produce output.
class OutputBuffer(StringIO):
    __slots__ = ["maybeSuppressLine", "suppressibleTagFound", "lineTextNodes", "outputBuffer"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.maybeSuppressLine = True
        self.suppressibleTagFound = False
        self.lineTextNodes = []


class OutputBufferStack(Stack):
    def __init__(self):
        super().__init__(lambda buffer: isinstance(buffer, OutputBuffer))


class OutputFormatter:
    def __init__(self, tagchars, pageDictMapping):
        self.rootMapping = {}
        # Need one NamespaceStack for each tagchar, based on the initial pageDict.
        for tagchar in tagchars:
            self.rootMapping[tagchar] = NamespaceStack(pageDictMapping[tagchar])

        self.loopTagData = {}
        self.outputCharCount = 0
        self.outputBufferStack = OutputBufferStack()
        # Start with the initial tracking entry. Some save tags will cause other entries.
        self.pushOutputBuffer()

    def pushOutputBuffer(self):
        self.outputBufferStack.push(OutputBuffer())

    def popOutputBuffer(self):
        for text in self.outputBufferStack.top.lineTextNodes:
            self.outputCharCount += len(text)
            self.outputBufferStack.top.write(text)
        outputValue = self.outputBufferStack.pop()
        return outputValue.getvalue()

    def markLineSuppressible(self):
        self.outputBufferStack.top.suppressibleTagFound = True

    def outputString(self, textString):
        assert textString is not None

        self.outputBufferStack.top.lineTextNodes.append(str(textString))
        assert isinstance(textString, (Line, str, Number))
        if isinstance(textString, Line):
            self.outputBufferStack.top.maybeSuppressLine &= textString.isspace()

            # if we found a line end, everything gets reset
            if textString.isCompleteLine:
                self.suppressOrOutputLine()
        elif isinstance(textString, (str, Number)):
            self.outputBufferStack.top.maybeSuppressLine &= not str(textString)

    def suppressOrOutputLine(self):
        # Not suppressible, then output it at this point
        if not self.outputBufferStack.top.maybeSuppressLine or not self.outputBufferStack.top.suppressibleTagFound:
            for text in self.outputBufferStack.top.lineTextNodes:
                self.outputCharCount += len(text)
                self.outputBufferStack.top.write(text)
        # Whether or not the line was suppressed, reset for the next line.
        self.outputBufferStack.top.maybeSuppressLine = True
        self.outputBufferStack.top.suppressibleTagFound = False
        self.outputBufferStack.top.lineTextNodes.clear()

    def getOutput(self):
        # Only complete lines are eligible for suppression. If we still have nodes then they were not completed. Output them.
        for text in self.outputBufferStack.top.lineTextNodes:
            self.outputCharCount += len(text)
            self.outputBufferStack.top.write(text)
        return self.outputBufferStack.top.getvalue()


# Essentially a character iterator, but we keep track of our position and line
#   number and line position, as well as if the current line has anything other
#   than whitespace and a tag. In that special case, we will attempt to
#   suppress that line. XXX That is kind of tricky here, because we are not
#   particularly line oriented. We may refactor later to allow for this
#   behavior, but for now, we will not try blank line suppression with only
#   tags and whitespace. The complication is that we have to be looking at this
#   during the output, not just the parsing.
# Maybe even use a Universal Line ending io class to read the chars here instead of iter.
class TemplateIterator:
    def __init__(self, template):
        self._template = template
        self._charpos = 0
        self._eol = False
        self._lastTagCharpos = None
        self._lastTagLinenum = None
        self._lastTagLinepos = None
        # Keeping track for rolling back characters and line count/pos
        self._lineLengths = [0]  # (or maybe use a deque if it is more efficient)

    def __iter__(self):
        return self

    @property
    def _linenum(self):
        return len(self._lineLengths) - 1

    @property
    def _linepos(self):
        return self._lineLengths[-1]

    def __next__(self):
        if self._charpos >= len(self._template):
            raise StopIteration()
        char = self._template[self._charpos]
        if self._eol:
            self._lineLengths.append(0)
        if char == "<":
            self._lastTagCharpos = self._charpos
            self._lastTagLinenum = self._linenum
            self._lastTagLinepos = self._linepos
        if self._eol:
            self._eol = False
        else:
            self._lineLengths[-1] += 1
        self._charpos += 1
        if char == "\n":
            # Set this at the end for the next char to be on a new line counter
            self._eol = True
        return char

    def rollback(self, charcount=1):
        if self._charpos < charcount:
            raise IndexError("Tried to reset before start of template")
        while charcount:
            self._charpos -= 1
            self._lineLengths[-1] -= 1
            if self._lineLengths[-1] < 0:
                self._lineLengths.pop()
            charcount -= 1
        # For a convenience short cut, return a reference to self, so we can do
        # an in-place rollback in the process of invoking / referencing the
        # iterator
        return self


class Template:
    tagMap = {
        "if": IfTagContainer.IfTagContainer,
        "elif": ElifTag.ElifTag,
        "else": ElseTag.ElseTag,
        "case": CaseTag.CaseTag,
        "option": OptionTag.OptionTag,
        "loop": LoopTag.LoopTag,
        "namespace": NamespaceTag.NamespaceTag,
        "saveeval": SaveEvalTag.SaveEvalTag,
        "saveraw": SaveRawTag.SaveRawTag,
        "saveoverride": SaveOverrideTag.SaveOverrideTag,
        "super": SuperTag.SuperTag,
    }

    def __init__(self, tagchars, template, is0False=False, doSuppressComments=False, doStrictKeyLookup=False,
                 doEncodeHtml=True):
        self._tagchars = tagchars
        self._templateStr = template
        self.is0False = is0False
        self.doSuppressComments = doSuppressComments
        self.doStrictKeyLookup = doStrictKeyLookup
        self.doEncodeHtml = doEncodeHtml
        currentTextNode = TextNode()

        self._tagStack = TagStack(max_nested_tag_depth)
        self._tagStack.push(RootTag(None, self))
        # Separate stack, just for loops
        if not isinstance(tagchars, str):
            raise TypeError("tagchar value must be string")
        if not isinstance(template, str):
            raise TypeError("template value must be string")
        self.templateIter = TemplateIterator(template)
        lookAheadBuffer = []
        # We *cannot* have nested comments, so we only need to track if we are in an open comment. We can set it back
        #  to None when we hit the close comment -->
        currentComment = None
        for char in self.templateIter:
            lookAheadBuffer = [char]
            try:
                if char == "<":
                    char2 = next(self.templateIter)
                    lookAheadBuffer.append(char2)
                    if char2 in tagchars:
                        # Found a tag. If it is not a keyword, it is a simple tag
                        # The current contents of outbuf need to be wrapped up into a TextNode
                        for line in currentTextNode:
                            self._tagStack.top.addChild(line)
                        currentTextNode = TextNode()
                        # Next figure out what kind of tag it is. This will handle the tagsub comment tag as well.
                        char3 = next(self.templateIter)
                        lookAheadBuffer.append(char3)
                        if char3 == "/":
                            # This is a close tag. It must match the top tag on the
                            # tagStack. If this fails to validate, it will raise an
                            # exception. We should also have details about where it
                            # happened in the Exception.
                            self._tagStack.top.validateCloseTag(char2, self)
                            tag = self._tagStack.pop()
                        elif char3 == "-":
                            self.rollback(1)
                            self._tagStack.top.validateCloseTag(char2, self)
                            tag = self._tagStack.pop()
                        else:
                            self.templateIter.rollback(1)
                            # parseTag can handle the tagsub comment as well
                            tag = self.parseTag(char2)
                            # We need to add it to the enclosing tag immediately, because we need tha parent relationship
                            # for the traceback if we have to report an error.
                            self._tagStack.top.addChild(tag)
                            if tag.isBalancedTag:
                                self._tagStack.push(tag)
                    elif char2 == "!":
                        char3 = next(self.templateIter)
                        lookAheadBuffer.append(char3)
                        char4 = next(self.templateIter)
                        lookAheadBuffer.append(char4)
                        if char3 == "-" and char4 == "-":
                            for line in currentTextNode:
                                self._tagStack.top.addChild(line)
                            # This will be the first child text node of the comment container
                            currentTextNode = TextNode()
                            # We have made CommmentNode a type of Container node. The comment characters will be part
                            # of the first child TextNode. This will let us expand tags in the comment.
                            currentTextNode.addChar(char)
                            currentTextNode.addChar(char2)
                            currentTextNode.addChar(char3)
                            currentTextNode.addChar(char4)
                            node = CommentNode(self)
                            currentComment = node
                            self._tagStack.top.addChild(node)
                            self._tagStack.push(node)
                        else:
                            currentTextNode.addChar(char)
                            currentTextNode.addChar(char2)
                            self.rollback(2)
                    else:
                        currentTextNode.addChar(char)
                        # Since we were not in a tag, char2 needs to be evaluated at the top of the loop independently.
                        self.rollback(1)
                elif currentComment and char == "-":
                    char2 = next(self.templateIter)
                    lookAheadBuffer.append(char2)
                    char3 = next(self.templateIter)
                    lookAheadBuffer.append(char3)
                    if char2 == "-" and char3 == ">":
                        # Validate and Close out the comment
                        if self._tagStack.top != currentComment:
                            raise TagsubTemplateSyntaxError("Unclosed tag inside comment", tag=self._tagStack.top)
                        currentTextNode.addChar(char)
                        currentTextNode.addChar(char2)
                        currentTextNode.addChar(char3)
                        for line in currentTextNode:
                            self._tagStack.top.addChild(line)
                        currentTextNode = TextNode()
                        self._tagStack.pop()
                        currentComment = None
                    else:
                        currentTextNode.addChar(char)
                        currentTextNode.addChar(char2)
                        currentTextNode.addChar(char3)
                else:
                    currentTextNode.addChar(char)
            except StopIteration:
                for char in lookAheadBuffer:
                    currentTextNode.addChar(char)
        if currentTextNode:
            for line in currentTextNode:
                self._tagStack.top.addChild(line)
        # Ensure that we are left with the RootTag object on the tagStack.
        self.rootTag = self._tagStack.pop()
        if not isinstance(self.rootTag, RootTag):
            raise TagsubTemplateSyntaxError("Tag was not closed", tag=self.rootTag)

    def rollback(self, charcount):
        self.templateIter.rollback(charcount)
        return self

    def format(self, pageDictList):
        if isinstance(pageDictList, Sequence):
            if len(pageDictList) == len(self._tagchars):
                # Good situation, so far
                pageDictMapping = {}
                for tagchar, pageDict in zip(self._tagchars, pageDictList):
                    if not isinstance(pageDict, Mapping):
                        raise TypeError("Must provide a sequence of Mappings")
                    pageDictMapping[tagchar] = pageDict
            else:
                raise TagcharSequenceMismatchError("Mismatch of tagchars to Mappings")
        elif isinstance(pageDictList, Mapping):
            pageDictMapping = pageDictList
            if len(self._tagchars) == 1 and self._tagchars not in pageDictMapping:
                # Assume the sort of default case of a single mapping that
                # corresponds to the single tagchar.
                pageDictMapping = {self._tagchars: pageDictMapping}
            else:
                for tagchar in self._tagchars:
                    if tagchar not in pageDictMapping or not isinstance(pageDictMapping[tagchar], Mapping):
                        raise TagcharSequenceMismatchError("Must have a Mapping for each tagchar")
        else:
            raise TypeError("Must provide a Mapping or a Sequence of Mappings or tagchar indexed Mapping of Mappings")

        outputFormatter = OutputFormatter(self._tagchars, pageDictMapping)
        self.rootTag.format(outputFormatter)
        return outputFormatter.getOutput()

    def parseTag(self, tagchar):
        # Parse to first ! isLegalKeyChar(char)
        # - if we have a legal tag type, then instantiate the Tag subclass
        #   and pass iterator along to parse rest of tag. Otherwise, we know it
        #   is a simple tag or illegal.
        # - if ':', Create a LoopVarTag and pass in varname along with Iterator
        #   to keep parsing that tag.
        # - if '>', Create a simple tag (Tag) to parse the rest, rolling the
        #   iterator back before the '>' to let the Tag parse the rest, since
        #   we expect it to find the > char.
        # - Otherwise, we go ahead and parse as a simple tag anyway (likely all
        #   we would have found that would be legal would be whitespace).
        isSimpleTag = None
        try:
            char = next(self.templateIter)
            if char.isspace():
                # Special case. As long as we encounter a legal name, this is a simple tag.
                isSimpleTag = True
                while char.isspace():
                    char = next(self.templateIter)
            if char == ">":
                # Oops. Found nothing but whitespace. This is a Noop tag that essentially drops out with no effect.
                self.templateIter.rollback(1)
                return NullTag(tagchar, self)
            elif char == "!":
                # Only legal thing that can happen now is a tagsub comment
                char2 = next(self.templateIter)
                char3 = next(self.templateIter)
                if char2 != "-" or char3 != "-":
                    raise TagsubTemplateSyntaxError("Illegal tag", template=self)
                return TagsubCommentNode(tagchar, self)
            self.templateIter.rollback(1)
            token = Token(self)

            if (token.tokenstr in self.tagMap and not token.attributeChain and
                    not token.impliedLoopVarName and not isSimpleTag):
                return self.tagMap[token.tokenstr](tagchar, self)
            else:
                # This would be an implicit Simple Tag or a default
                # do not represent a known tag.
                value = Value.createValue(token, self)
                return SimpleTag.SimpleTag(tagchar, value, self)
        except StopIteration:
            raise TagsubTemplateSyntaxError("incomplete tag", template=self)
