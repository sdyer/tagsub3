from io import StringIO


class Line:
    def __init__(self, line, isCompleteLine=True):
        self._isCompleteLine = bool(isCompleteLine)
        self._line = line

    def __len__(self):
        return len(self._line)

    def __str__(self):
        return str(self._line)

    @property
    def isCompleteLine(self):
        return self._isCompleteLine

    def isspace(self):
        return self._line.isspace()

    def format(self, outputFormatter):
        outputFormatter.outputString(self)


class TextNode:
    def __init__(self):
        self._lines = []
        self._textBuf = StringIO()
        self.__incomplete = False

    def _addLine(self, lineText):
        # TODO Maybe verify only one line being passed in. Should be all our
        # code, so maybe trust the calling code to have already checked.
        self._lines.append(Line(lineText, lineText.endswith('\n')))

    def addChar(self, char):
        self._textBuf.write(char)
        self.__incomplete = True
        if char == "\n":
            self._addLine(self._textBuf.getvalue())
            self._textBuf = StringIO()
            self.__incomplete = False

    def close(self):
        lastLine = self._textBuf.getvalue()
        if lastLine:
            self._addLine(lastLine)
            self.__incomplete = False
        del self._textBuf

    def __iter__(self):
        if self.__incomplete:
            self.close()
        return iter(self._lines)
