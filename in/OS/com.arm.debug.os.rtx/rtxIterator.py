# Copyright (C) 2018 Arm Limited (or its affiliates). All rights reserved.

class RtxLinkedListIterator:

    def __init__(self, firstElementPtr, nextMemberName, type=None):
        self.currentElement  = firstElementPtr
        self.nextMemberName  = nextMemberName
        self.type            = type

    def __iter__(self):
        return self

    def next(self):
        if ((self.currentElement == None) or (self.currentElement.readAsNumber()==0)):
            raise StopIteration()

        ret = self.currentElement

        if(self.nextMemberName==None or len(self.nextMemberName)==0):
            self.currentElement = None
        else:
            if self.type:
                members = ret.dereferencePointer(self.type).getStructureMembers()
            else:
                members = ret.dereferencePointer().getStructureMembers()

            self.currentElement = members[self.nextMemberName]

        return ret

class RtxArrayIterator:

    def __init__(self, arrayOfPtr):
        self.arrayOfPtr   = filter(lambda ptr: ptr.readAsNumber()!=0, arrayOfPtr)
        self.currentIndex = 0
        self.size = len(self.arrayOfPtr)

    def __iter__(self):
        return self

    def next(self):
        if (self.currentIndex >= self.size):
            raise StopIteration()

        ret = self.arrayOfPtr[self.currentIndex]
        self.currentIndex += 1
        return ret


def toIterator(debugSession, ptrExpr, nextMemberName):
    return pointerToIter(debugSession.evaluateExpression(ptrExpr), nextMemberName)

def pointerToIter(ptr, nextMemberName, type=None):
    return RtxLinkedListIterator(ptr, nextMemberName, type)
