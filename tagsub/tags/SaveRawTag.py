from .TagContainer import TagContainer
from .values.Value import Value
from .values.Token import Token
from ..exceptions import InvalidTagKeyName

class SaveRawTag(TagContainer):
    tag = "saveraw"

    def __init__(self, tagchar, template):
        super().__init__(tagchar, template)

        # Parse the name Token and validate. Must be a simple name, not an object attribute or implied loop var.
        token = Token(template)
        if token.attributeChain or token.impliedLoopVarName:
            raise InvalidTagKeyName("Must only have simple name for save tags", tag=self)
        self.value = Value.createValue(token, template, self)
        self.closeTag()

    def formatAtReference(self, outputFormatter):
        super().format(outputFormatter)

    def format(self, outputFormatter):
        namespace = outputFormatter.rootMapping[self.tagchar]
        # When we hit it, saveraw tag does not get formatted into the output, nor do we walk the children and format
        # them. Instead, we save a reference to the tag. The Value object recognizes that we have a Tag and calls the
        # above formatAtReference to get it formatted into the output with the current NamespaceStack.
        outputFormatter.markLineSuppressible()
        namespace[self.value._name] = self


# TODO For saveraw, it will act much like saveeval (in that we keep the parsed tree here in the Template),
#  except that when we hit this spot in the tree during formatting, we go ahead and call its format method and save
#  the resulting string in the scratch space. This would need to be saved as a rawstr to prevent it from HTML entity
#  char escaping from being applied more than once.

# TODO It will be at run-time that the decisions need to be made and how we differentiate between saveeval and saveraw tags.
