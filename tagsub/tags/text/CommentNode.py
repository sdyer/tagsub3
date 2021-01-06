from io import StringIO


# TODO CommentNode questions - Do we need to keep track of lines line we do for TextNodes? Possibly yes, because if
#  we are doing blank line suppression and comment suppression (less common), we might want to suppress lines that
#  only had the comment. and whitespace. Have to keep track of what is on the line where the comment ends,
#  as well. Possibly independently, since the comment might be multiline.

# FIXME Comments can have tags inside and need to be expanded when they are encountered. Perhaps treat a comment as a
#  TagContainer type node with the comment text being child text nodes inside and any regular tags being expanded
#  like normal. The only complication would be out at the Template level while parsing, we would have to track state
#  that we were in a comment. On the other hand, perhaps we should just eliminate comment suppression. That could
#  help eliminate the situation where comments and tags might be intrinsically not structured well hierarchically
#  together. The counter argument being that it could be a security cleanup help to suppress all comments in
#  production.
# XXX I think we have dealt with the above (comments can be nested). Add some more unit tests to test various behaviors.
from ..TagContainer import TagContainer


class CommentNode(TagContainer):
    def __init__(self, template):
        super().__init__("", template)
        # In template parsing, we already parsed the "<!--" chars. They are assumed to be present already.

    def format(self, outputFormatter):
        # Conditionally put this out, depending on comment suppression, possibly suppress any incomplete blank line
        # preceding the comment if the comment is suppressed.
        if self._template.doSuppressComments:
            outputFormatter.markLineSuppressible()
        else:
            # Let the TagContainer write out the children
            super().format(outputFormatter)
