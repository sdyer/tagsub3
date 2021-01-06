
"""
# The limits for the recursion overflow erors above. May no longer be relevant.
MAX_RECURSION 20
MAX_LOOP_DEPTH 8
MAX_TEMPLATE_RECURSION 10
MAX_EXPRESSION_DEPTH 8
MAX_SAVEEVAL_RECURSION 4
"""

# Define these with the same values as the C code and add tests to raise
# the appropriate errors if we exceed them. This is important anyway if we want
# to set reasonable limits.
max_nested_tag_depth = 20

max_recursive_template_depth = 10
max_saveeval_depth = 4
max_expression_depth = 8
