from collections import deque
from collections.abc import Callable


class Stack:
    def __init__(self, isValidEntry=None):
        self.__stack = deque()
        if isValidEntry:
            assert isinstance(isValidEntry, Callable)
        self.__isValidEntry = isValidEntry

    def push(self, entry):
        if self.__isValidEntry and self.__isValidEntry(entry):
            self.__stack.append(entry)
        else:
            raise TypeError("Invalid content for Stack")

    def pop(self):
        if self.__stack:
            return self.__stack.pop()
        else:
            return None

    @property
    def top(self):
        if self.__stack:
            return self.__stack[-1]
        else:
            return None

    def __len__(self):
        return len(self.__stack)

    def __getitem__(self, index):
        # For a stack, we are looking from the end
        if index < 0 or index >= len(self.__stack):
            raise IndexError("Only positive index defined for Stack")
        return self.__stack[len(self.__stack)-1-index]
