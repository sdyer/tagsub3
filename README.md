# tagsub3
Yet another templating language library.

# tagsub for Python3

substitute(tagchars, template, dicts [,is0False=False] [,doSuppressComments=False] [,doStrictKeyLookup=False], [doEncodeHtml=True]) -- Return a string obtained from substituting dict values into template.

tagchar is a character or string of characters that identify special tags that will be processed by this routine. dict is a mapping or a sequence of mappings that correspond to each tagchar. There are five basic groups of tags. First is the simple substitution tags. Assume for this explanation that tagchar is '@'. A simple tag would be formed as <@ name> where name is the name of the key to substitute if found in dict. If name is not found, the tag would simply disappear. If a simple tag contains other tags, they are scanned recursively and processed the same as the original template. 

The second group is composed if <@if name>, <@elif name>, <@else>, <@/if>. The elif and else tags are optional in this construct. If the value of name in the dict tests as true, then the text between the if (or elif) and else (or the next elif) will appear in the output (if no else, then the text between the if and /if tag will appear). If the value tests as false, or the key is not present in the dict, then the text between the else and /if tags will appear (if no else, then no text will be displayed for the if tag). Multiple values may be combined in an if (or elif) tag by using '|' (or ',') as a logical or operator, '&' as a logical and, and '!' as a logical not. Parentheses may be used to alter normal precedence rules.

The third group is composed of the <@loop name> and <@/loop> tags. For this tag, the value of name should be a list of dictionaries. All text between loop and /loop will appear once for each member of the list. Also, for the text in the loop body, keys will be searched first in the dictionary for that pass through the list before going to the next enclosing loop dictionary or to the top level dictionary passed in.

The fourth group is composed of <@case name>, <@option value>, <@else>, <@/case>. In this group, name is evaluated when the case tag is found. The string representation of the value is then compared to the value for each option. When one matches, the text following that option up to the next option, else, or /case tag will be displayed. If no option tags match, the text between the else and /case tag will be displayed. If no else tag is present, and no option tags match, then no text will appear in the output for that case tag. An option value may be any of three types or a combination. The first type is a normal legal keyname as described below. The second is text inside of double quotes. There is currently no way to escape a double quote in the string, however any other characters may appear within the double quotes. The third type is a variable value that will be looked up from the dictionary namespace. A variable value is indicated by prefixing the keyname with an equal sign '='. Multiple values may be specified in an option by separating them with commas.

The fifth group is composed of the <@saveraw name> and <@/saveraw> tags. When a saveraw tag is encountered, all text between the opening and closing saveraw tags is updated into the corresponding dictionary, with no output appearing for that tag. No tags between the opening and closing saveraw tags are evaluated, the text is stored as is, and evaluated when it is substituted later. The saved value in the dictionary can be used later on in the template, or possibly even later beyond the boundaries of the function call.

The sixth and final group is the <@saveeval name> and <@/saveeval> tags. They function almost exactly like the saveraw tags, with one critical difference. All tags withing a saveeval tag body will be evaluated. as it is scanned. The result will be stored in the dictionary, just as with the saveraw tag.

There is now a sixth group, also in the save genre, composed of <@saveoverride name>, <@super>, and <@/saveoverride>. They act basically like the saveraw group, but they preserve any reference to the same keyname already in the dict, and cause any <@super> tags inside the saveoverride body to reference the overridden value. This gives us a primitive form of inheritance. A <@super> tag has absolutely no meaning outside of a saveoverride tag body.

While parsing inside loops, We have some implied loop variables available. When inside of the loop, keys of the form loopname:isFirst may be used. If no loopname is specified, then the most recently enclosing loop is used. The implied keys available are: isFirst, isLast, isOdd, isEven, index, index0, rindex, rindex0, and length. The index variables represent a 0 and 1-based index and a reversed version of both, as well.

Another feature is that arbitrary whitespace may be included in tags (except for the close tags which can have no whitespace). As a consequence, all values in tags must only consist of upper and lowercase letters, numbers, and the underscore character (with the exception of the option tag as described above.

There are several compiled in constants that are visible as int objects in the module. If they are assigned to, it will have no effect. The integers are max_nested_tag_depth, max_nested_loop_depth, max_recursive_template_depth, max_expression_depth, and max_saveeval_depth. These are mostly used for testing to know what the compiled in limits are.

substitute(tagchars, template, dicts [,is0False=False] [,doSuppressComments=False] [,doStrictKeyLookup=False]) -- Return a string obtained from substituting dict values into template.

tagchars is a sequence of characters identifying the tags to use.
template is the template we are substituting into.
dicts is a single dict (if only one tagchar) or a sequence of dicts of the same length as tagcharss, containing the data to substitute into template.
is0False controls whether to treat the character 0 as False in an if tag.
doSuppressComments controls whether to suppress regular html comments.
doStrictKeyLookup controls whether to raise an exception when a key is not found. The default is to treat it as False or an empty string.
