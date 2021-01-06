from . import Tag
from .values.Token import Token
from ..exceptions import TagsubTemplateSyntaxError
from collections import deque

# Every TagContainer that will sit on the TagStack, needs a tracking structure to hold what we are keeping track of
# for blank line suppression for its children. So, every time a TextNode is added, if its last line is incomplete (
# which will almost always be true with any kind of indentation happening), Keep the TextNode aside until we see a
# new line at this level. That means hold the TextNode, then the child tag after it is added, then the next TextNode.
# If it is empty or only one line that is incomplete and all whitespace, keep accumulating. If it's first line is
# complete and all whitespace, then build up a BlankLineSuppressionNode that will detect if any output is produced by
# its Tags and if not, suppress the whole block. If the TextNode has a first complete line that has non-whitespace,
# then our whole accumulated collection is not a candidate for blank line suppression, so go ahead and add all the
# accumulated nodes into the children except for the last TextNode, which we use to start all over, looking at the
# last line to see if it is incomplete and whitespace.
class TagContainer(Tag.Tag):
    def __init__(self, tagchar, template):
        super().__init__(tagchar, template)
        self._children = deque()

    def addChild(self, node):
        self._children.append(node)
        node.parent = self

    @property
    def isBalancedTag(self):
        return True

    # Only factored out here so RootTag can override this and ignore
    def markLineSuppressible(self, outputFormatter):
        outputFormatter.markLineSuppressible()

    def format(self, outputFormatter):
        # TODO make a call to outputFormatter indicating the current line should be eligible for suppression
        self.markLineSuppressible(outputFormatter)
        for child in self._children:
            child.format(outputFormatter)
        # TODO make another call to outputFormatter to say the current line is eligible for suppression
        self.markLineSuppressible(outputFormatter)

    def validateCloseTag(self, tagchar, template):
        if tagchar != self._tagchar:
            raise TagsubTemplateSyntaxError("Misplaced close tag", template=template)
        try:
            token = Token(template)

            if (token.tokenstr != self.tag or token.attributeChain or
                    token.impliedLoopVarName):
                raise TagsubTemplateSyntaxError("Misplaced close tag", template=template)

            char = next(template.templateIter)
            while char.isspace():
                char = next(template.templateIter)
        except StopIteration:
            raise TagsubTemplateSyntaxError("Invalid close tag", template=template)
        if char != ">":
            raise TagsubTemplateSyntaxError("Invalid close tag", template=template)
