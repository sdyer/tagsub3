from .Token import Token
from .Value import Value
from .NotOperator import NotOperator
from .OrOperator import OrOperator
from .AndOperator import AndOperator
from .Operator import Operator
from ...exceptions import ExpressionError
from ...exceptions import InvalidTagKeyName
from ...util.Stack import Stack

stateRequiresOperator, stateRequiresOperand = range(2)


class OperatorStack(Stack):
    def __init__(self):
        super().__init__(lambda operator: len(operator) == 1 and operator in "!(&|,>")


class OperandStack(Stack):
    def __init__(self):
        super().__init__(lambda operand: isinstance(operand, (Value, Operator)))


precedence = {
    '(': 4,
    ')': 4,
    '!': 1,
    '&': 2,
    '|': 3,
    ',': 3,
}


# This may be the workhorse class for parsing out name references and/or
# logical expressions of name references. If it is all in one location, then it
# will be simpler to manage general template settings, like whether a missing
# name should return an empty string or be a KeyError.
class ExpressionParser:
    def __init__(self, template, tag):
        self._expression = None
        self._template = template
        self.tag = tag

        # This is only valid in if/elif.
        self._operatorStack = OperatorStack()
        self._operandStack = OperandStack()
        self._state = stateRequiresOperand
        while True:
            char = self.nextNonSpace()
            if self._state == stateRequiresOperand:
                if char in "!(":
                    # Push the operator
                    self._operatorStack.push(char)
                else:
                    # Parse another token. Should fail if not a valid operand.
                    try:
                        token = Token(template.rollback(1))
                    except InvalidTagKeyName:
                        if not self._operandStack and not self._operatorStack:
                            # If it is just an empty if or elif tag, we just reraise the InvalidTagKeyName
                            raise
                        else:
                            # We have already parsed some expression elements, so now we tell them the expression is bad
                            raise ExpressionError("Missing/Bad operand in expression", tag=self.tag)
                    value = Value.createValue(token, self._template, tag=self.tag)
                    # Push the operand
                    self._operandStack.push(value)
                    self._state = stateRequiresOperator
            elif self._state == stateRequiresOperator:
                if char == '>':
                    # Process the rest of the operator stack.
                    while self._operatorStack:
                        operator = self._operatorStack.pop()
                        self.processOperator(operator)
                    self._expression = self._operandStack.pop()
                    # I am not sure it is possible to force something to be left to test this condition.
                    # TODO Research this
                    #if self._operandStack:
                    #    raise ExpressionError("Error in expression in tag", tag=self.tag, template=template)
                    # Finished parsing the expression
                    break
                elif char == ')':
                    # Process the operator stack until we get to a '(' operator. Of course fail if stack underflow.
                    while True:
                        operator = self._operatorStack.pop()
                        if not operator:
                            raise ExpressionError("Error in expression in tag", tag=self.tag, template=template)
                        elif operator == '(':
                            break
                        self.processOperator(operator)
                elif char in '&|,':
                    # Process all the higher order operators on the stack already encountered
                    while self._operatorStack and precedence[self._operatorStack.top] <= precedence[char]:
                        operator = self._operatorStack.pop()
                        self.processOperator(operator)
                    # Push this operator on the operator stack now to get its other operand
                    self._operatorStack.push(char)
                    self._state = stateRequiresOperand
                else:
                    raise ExpressionError("Error in expression in tag", tag=self.tag, template=template)

    def nextNonSpace(self):
        char = next(self._template.templateIter)
        while char.isspace():
            char = next(self._template.templateIter)
        return char

    def processOperator(self, operator):
        if operator == '!':
            self._operandStack.push(NotOperator(self._operandStack.pop()))
        elif operator in ',|':
            rightOperand = self._operandStack.pop()
            leftOperand = self._operandStack.pop()
            self._operandStack.push(OrOperator(leftOperand, rightOperand))
        elif operator == '&':
            rightOperand = self._operandStack.pop()
            leftOperand = self._operandStack.pop()
            self._operandStack.push(AndOperator(leftOperand, rightOperand))

    @property
    def expression(self):
        return self._expression

    # I don't think we ever need these
    #@property
    #def isSimpleValue(self):
    #    return isinstance(self._expression, Value)

    #@property
    #def isLogicalExpression(self):
    #    return isinstance(self._expression, Operator)
