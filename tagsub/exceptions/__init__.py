# Define here because the dynamic part also needs it.
def buildStaticTracebackString(tag, template):
	# We are not really doing recursive substitution, so, we really only
	# have position, and if we have an outputFormatter, then we need to
	# find the indexes to any loop tags (which we can see stepping up the
	# NamespaceStack).

	# Compile time error
	if tag:
		err_abspos = tag.charpos + 1
		err_lineno = tag.linenum + 1
		err_linepos = tag.linepos + 1
	elif template:
		err_abspos = template.templateIter._lastTagCharpos + 1
		err_lineno = template.templateIter._lastTagLinenum + 1
		err_linepos = template.templateIter._lastTagLinepos + 1
	else:
		return ""
	return " %s(%s,%s)" % (err_abspos, err_lineno, err_linepos)


def buildDynamicTracebackString(tag, template, outputFormatter):
	# The NamespaceStack does not really indicate whether or not the
	# Mapping is for a loop tag os a namespace tag. We need to walk up the
	# chain of parent tags looking for loop tags.
	tracebackElements = []
	currentTag = tag
	while True:
		if currentTag.tag is None:
			# Found the top level RootTag. Finished.
			break
		elif currentTag.tag == "loop" and outputFormatter:
			# This is a loop tag. We need to include the formatting for it, but only at format time. Otherwise it
			# is just an ordinary tag.
			tbElement = f"{currentTag._charpos+1}({currentTag._linenum+1},{currentTag._linepos+1})"
			loopTagData = outputFormatter.loopTagData.get(currentTag.loopId)
			if loopTagData:
				tracebackElements.insert(0, f"{tbElement}[{loopTagData['index']}]")
			else:
				tracebackElements.insert(0, tbElement)
		# else, Normal tag. Skip over it.
		currentTag = currentTag.parent
	return ':'.join(tracebackElements)


def buildNonTagsubException(excClass, msg, tag, template, outputFormatter=None):
	dynamic = buildDynamicTracebackString(tag, template, outputFormatter)
	if dynamic:
		tb = f"{buildStaticTracebackString(tag, template)}:{dynamic}"
	else:
		tb = buildStaticTracebackString(tag, template)
	return excClass(f"{msg} {tb}")


# TODO Determine if RuntimeError is the appropriate base to use.
class TagsubBaseException(RuntimeError):
	pass


class TagsubProcessingError(TagsubBaseException):
	def __init__(self, msg, *args, **kwargs):
		# One of template or tag should be set (maybe both?).
		self.template = kwargs.get('template')
		# If a tag is involved, we may include it here. That will aid building
		# up the tagsub traceback
		self.tag = kwargs.get("tag")
		# If the error occurs during output formatting, this will help us get
		# the loop iteration numbers.
		self.outputFormatter = kwargs.get("outputFormatter")

		tagsub_tb = self.buildTagsubTracebackString(self.tag, self.template, self.outputFormatter)
		super().__init__(msg+tagsub_tb, *args)

	def buildTagsubTracebackString(self, tag, template, outputFormatter):
		return buildStaticTracebackString(tag, template)


# Used when the tagchar sequence and the sequence of mappings (or callables)
# are not the same length
class TagcharSequenceMismatchError(TagsubProcessingError):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)


class TagsubRuntimeError(TagsubProcessingError):
	def buildTagsubTracebackString(self, tag, template, outputFormatter):
		# The NamespaceStack does not really indicate whether or not the
		# Mapping is for a loop tag os a namespace tag. We need to walk up the
		# chain of parent tags looking for loop tags.
		dynamic = buildDynamicTracebackString(tag, template, outputFormatter)
		if dynamic:
			return f"{buildStaticTracebackString(tag, template)}:{dynamic}"
		else:
			return buildStaticTracebackString(tag, template)


class TagsubCompileTimeError(TagsubProcessingError):
	# outputFormatter will be None in subclasses of this.
	def buildTagsubTracebackString(self, tag, template, outputFormatter):
		return buildStaticTracebackString(tag, template)


class TagsubEofParsingTokenError(TagsubCompileTimeError):
	pass


class TagsubTypeError(TagsubRuntimeError, TypeError):
	pass


class TagsubValueError(TagsubRuntimeError, ValueError):
	pass


# These overflow errors may go away since we are making this pure Python,
# Except to avoid failing existing tests, we will honor the limits. Eventually
# we may bump them a bit higher, but we don't want it to be unlimited.
class TagStackOverflowError(TagsubRuntimeError):
	pass


class LoopStackOverflowError(TagsubRuntimeError):
	pass


class RecursiveSubstitutionOverflowError(TagsubRuntimeError):
	pass


class RecursiveSaveEvalOverflowError(TagsubRuntimeError):
	pass


class TagsubTemplateSyntaxError(TagsubCompileTimeError):
	pass


class InvalidTagName(TagsubCompileTimeError):
	pass


class ExpressionStackOverflowError(TagsubCompileTimeError):
	pass


class ExpressionError(TagsubCompileTimeError):
	pass


class InvalidTagKeyName(TagsubCompileTimeError):
	pass


"""
	for (i=0; i < template_stack->top; i++) {
		for (j=0; j <= template_stack->stack[i].loop_tag_stack.top; j++) {
			err_abspos = (int) (template_stack->stack[i].loop_tag_stack.stack[j].index_ptr
				- PyBytes_AsString(template_stack->stack[i].template))+1;
			err_lineno = template_stack->stack[i].loop_tag_stack.stack[j].line_counter;
			err_linepos = template_stack->stack[i].loop_tag_stack.stack[j].index_ptr
				- template_stack->stack[i].loop_tag_stack.stack[j].line_start+1;
			temp_str = PyBytes_FromFormat("%d(%d,%d)[%d]:",
				err_abspos, err_lineno, err_linepos,
				template_stack->stack[i].loop_tag_stack.stack[j].loop_counter+1);
			if (temp_str==NULL) {
				PyErr_Clear();
				PyErr_SetString(exc_type, err_text);
			}
			PyBytes_ConcatAndDel(&error_str, temp_str);
			if (error_str==NULL) {
				PyErr_Clear();
				PyErr_SetString(exc_type, err_text);
			}
		}
		err_abspos = (int) (template_stack->stack[i].tagstart
			- PyBytes_AsString(template_stack->stack[i].template))+1;
		err_lineno = template_stack->stack[i].line_count_for_current_tag;
		err_linepos = template_stack->stack[i].tagstart
			- template_stack->stack[i].start_of_line_for_current_tag+1;
		temp_str = PyBytes_FromFormat("%d(%d,%d)/",err_abspos,
			err_lineno, err_linepos);
		if (temp_str==NULL) {
			PyErr_Clear();
			PyErr_SetString(exc_type, err_text);
		}
		PyBytes_ConcatAndDel(&error_str, temp_str);
		if (error_str==NULL) {
			PyErr_Clear();
			PyErr_SetString(exc_type, err_text);
		}
	}
	for (j=0; j <= template_stack->stack[i].loop_tag_stack.top; j++) {
		err_abspos = (int) (template_stack->stack[i].loop_tag_stack.stack[j].index_ptr
			- PyBytes_AsString(template_stack->stack[i].template))+1;
		err_lineno = template_stack->stack[i].loop_tag_stack.stack[j].line_counter;
		err_linepos = template_stack->stack[i].loop_tag_stack.stack[j].index_ptr
			- template_stack->stack[i].loop_tag_stack.stack[j].line_start+1;
		temp_str = PyBytes_FromFormat("%d(%d,%d)[%d]:",
			err_abspos, err_lineno, err_linepos,
			template_stack->stack[i].loop_tag_stack.stack[j].loop_counter+1);
		if (temp_str==NULL) {
			PyErr_Clear();
			PyErr_SetString(exc_type, err_text);
		}
		PyBytes_ConcatAndDel(&error_str, temp_str);
		if (error_str==NULL) {
			PyErr_Clear();
			PyErr_SetString(exc_type, err_text);
		}
	}
	if (exception_type!=et_loop_type_error) {\
		if (exception_type==et_tag_not_closed) {
			err_abspos = (int) (TOP(TOP(*template_stack).tag_stack).index_ptr
				- PyBytes_AsString(TOP(*template_stack).template))+1;
			err_lineno = TOP(TOP(*template_stack).tag_stack).line_counter;
			err_linepos = TOP(TOP(*template_stack).tag_stack).index_ptr
				- TOP(TOP(*template_stack).tag_stack).line_start+1;
		}
		else {
			err_abspos = (int) (template_stack->stack[i].tagstart
				- PyBytes_AsString(template_stack->stack[i].template))+1;
			err_lineno = template_stack->stack[i].line_count_for_current_tag;
			err_linepos = template_stack->stack[i].tagstart
				- template_stack->stack[i].start_of_line_for_current_tag+1;
		}
		temp_str = PyBytes_FromFormat("%d(%d,%d)",err_abspos,
			err_lineno, err_linepos);
		if (temp_str==NULL) {
			PyErr_Clear();
			PyErr_SetString(exc_type, err_text);
		}
		PyBytes_ConcatAndDel(&error_str, temp_str);
		if (error_str==NULL) {
			PyErr_Clear();
			PyErr_SetString(exc_type, err_text);
		}
	}
	PyErr_SetObject(exc_type, error_str);
"""