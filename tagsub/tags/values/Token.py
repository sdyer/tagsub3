from io import StringIO
from ...exceptions import InvalidTagKeyName


class Token:
    @classmethod
    def isLegalKeyChar(cls, char):
        return ('A' <= char <= 'Z' or 'a' <= char <= 'z' or
                '0' <= char <= '9' or char == '_')

    def __init__(self, template, isOptionValue=False, consumeWhitespace=True):
        self._template = template
        self._isOptionValue = isOptionValue
        self.isOptionLookup = False
        self._consumeWhitespace = consumeWhitespace
        # Assign an initial value to avoid warnings
        self.tokenstr = None
        self.impliedLoopVarName = None
        self.attributeChain = None
        # This sets self.tokenstr, self.attributeChain and
        # self.impliedLoopVarName
        self.parseToken()

    def parseToken(self):
        # Step through the characters in template.templateIter.
        # We must start with a non-legalKeyChar. While the separator character
        #   (the first char in this case) is a ".", continue parsing tokens and
        #   add to the attributeChain list that we will pass in to the
        #   constructor. If we get a ":" separator, then we have an implied
        #   LoopVar.

        # FIXME For performance, consider making this a deque??
        nextChar = None
        attributeChain = []
        if self._consumeWhitespace:
            nextChar = next(self._template.templateIter)
            while nextChar.isspace():
                nextChar = next(self._template.templateIter)

        if self._isOptionValue and nextChar == "=":
            # We have a lookup option tag. Parse the rest of the tag like normal. Only valid in an option tag
            self.isOptionLookup = True
            nextChar = next(self._template.templateIter)
        if self._isOptionValue and nextChar == '"':
            # We have a quoted option string. Parse this separately. Only valid in an option tag
            self.parseQuotedOption()
            return

        self._template.rollback(1)
        while True:
            token = StringIO()
            nextChar = next(self._template.templateIter)
            while self.isLegalKeyChar(nextChar):
                token.write(nextChar)
                nextChar = next(self._template.templateIter)
            tokenstr = token.getvalue()
            if not tokenstr:
                # Probably illegal, but might be an anonymous implied loop variable
                break
            attributeChain.append(tokenstr)
            if nextChar != ".":
                break

        if nextChar == ":":
            # Parse off implied Loop Var.
            token = StringIO()
            nextChar = next(self._template.templateIter)
            while self.isLegalKeyChar(nextChar):
                token.write(nextChar)
                nextChar = next(self._template.templateIter)
            tokenstr = token.getvalue()
            if not tokenstr:
                raise InvalidTagKeyName("Invalid implied loop variable", template=self._template)
            impliedLoopVarName = tokenstr
        else:
            impliedLoopVarName = None

        if attributeChain:
            self.tokenstr = attributeChain[0]
            del attributeChain[0]
        else:
            self.tokenstr = None
            if not impliedLoopVarName:
                raise InvalidTagKeyName("Null tag key", template=self._template)

        self.attributeChain = None if not attributeChain else attributeChain
        self.impliedLoopVarName = impliedLoopVarName

        # We don't care what the final separator char is, just that we found
        # the end of this value. And we need to roll that character back,
        # because the calling tag is what knows what is valid next.
        self._template.rollback(1)

    def parseQuotedOption(self):
        # The first quote is already parsed off of the iterator. Go to the last quote.
        token = StringIO()
        finished = False
        while not finished:
            # FIXME We may need to break these apart to catch a StopIteration
            # condition and make it an InvalidTag of some sort instead
            # (although that may be handled at a higher level)
            nextChar = next(self._template.templateIter)
            while nextChar != '"':
                token.write(nextChar)
                nextChar = next(self._template.templateIter)
            nextChar = next(self._template.templateIter)
            if nextChar == '"':
                # We had double double quotes ("") which escapes the quote in a
                # quoted string, so we put one quote in the output token and
                # keep parsing
                token.write(nextChar)
            else:
                finished = True
        # We had to look one character past to determine for sure that the option
        # value was finished. Now, we need to put that character back for the
        # OptionTag itself to parse.
        self._template.rollback(1)
        self.tokenstr = token.getvalue()
        # Not sure anything would be expecting these, but give them a
        # reasonable value in this case.
        self.attributeChain = None
        self.impliedLoopVarName = None
