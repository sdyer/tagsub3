from .Template import Template

__version__ = "V1.68 Python3"

from .constants import max_nested_tag_depth, \
    max_recursive_template_depth, max_saveeval_depth, \
    max_expression_depth


# TODO Also define all the C Exception classes, probably in their own package.
# Then import them here so they will be available where other code expects to
# find them. Then make sure all the underlying code is raising the correct
# exceptions.
# TODO And a tagsub traceback formatter to get the correct location within the
# template for an exception. Maybe some utility functions for raising
# exceptions.

def substitute(tagchars, template, pageDictList, is0False=False, doSuppressComments=False, doStrictKeyLookup=False,
               doEncodeHtml=False):
    # Also allow pageDictList to be a mapping of mappings keyed on each tagchar
    # Compile the template
    template = Template(tagchars, template, is0False=is0False, doSuppressComments=doSuppressComments,
                        doStrictKeyLookup=doStrictKeyLookup, doEncodeHtml=doEncodeHtml)
    # Return the formatted output
    return template.format(pageDictList)


class rawstr(str):
    pass
