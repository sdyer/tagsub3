" :vim: et ts=2 sw=2:
" Not worrying about redefining at this point...
" tagsub tag matching code
"
" Key Mappings:
"   t[<tagchar>    Move to the prev tag in the current group
"   t]<tagchar>    Move to the next tag in the current group
"   t0<tagchar>    Move to the first tag in the current group
"   t$<tagchar>    Move to the last tag in the current group
"   t{<tagchar>    Move to the prev tag group
"   t}<tagchar>    Move to the next tag group
"   th<tagchar>    Highlight the tags in the current tag group
"   t?<tagchar>    Highlight all error tags (unclosed groups or non-opening
"                  group tags missing the opening tag)
"   thh            Hide all tag highlighting (possibly a bad choice since it
"                  precludes highlighting a group with a tagchar of h, which
"                  is possible, though unlikely)
"   t<Up><tagchar> Move to the parent tag group (if any)
"
" Likely, this file would be sourced in after/ftplugin/html.vim
"   (or possibly just in ftplugin/html.vim)

highlight TagSubGroup ctermbg=blue guibg=blue
highlight TagSubErrorGroup ctermbg=red guibg=red

function! FindNextTagsubTag()
  echo "Tagsub tag character"
  let c=nr2char(getchar())
  call MainTagFunction("moveToNextGroupTag", c)
endfunction
nnoremap <silent> <buffer> t] :call FindNextTagsubTag()<CR>

function! FindPrevTagsubTag()
  echo "Tagsub tag character"
  let c=nr2char(getchar())
  call MainTagFunction("moveToPrevGroupTag", c)
endfunction
nnoremap <silent> <buffer> t[ :call FindPrevTagsubTag()<CR>

function! FindLastTagsubTag()
  echo "Tagsub tag character"
  let c=nr2char(getchar())
  call MainTagFunction("moveToLastGroupTag", c)
endfunction
nnoremap <silent> <buffer> t$ :call FindLastTagsubTag()<CR>

function! FindFirstTagsubTag()
  echo "Tagsub tag character"
  let c=nr2char(getchar())
  call MainTagFunction("moveToFirstGroupTag", c)
endfunction
nnoremap <silent> <buffer> t0 :call FindFirstTagsubTag()<CR>

function! FindParentTagsubGroup()
  echo "Tagsub tag character"
  let c=nr2char(getchar())
  call MainTagFunction("moveToParentGroup", c)
endfunction
nnoremap <silent> <buffer> t<Up> :call FindParentTagsubGroup()<CR>

function! FindNextTagsubGroup()
  echo "Tagsub tag character"
  let c=nr2char(getchar())
  call MainTagFunction("moveToNextGroup", c)
endfunction
nnoremap <silent> <buffer> t} :call FindNextTagsubGroup()<CR>

function! FindPrevTagsubGroup()
  echo "Tagsub tag character"
  let c=nr2char(getchar())
  call MainTagFunction("moveToPrevGroup", c)
endfunction
nnoremap <silent> <buffer> t{ :call FindPrevTagsubGroup()<CR>

function! HighlightTagsubGroup()
  echo "Tagsub tag character"
  let c=nr2char(getchar())
  call MainTagFunction("highlightGroup", c)
endfunction
nnoremap <silent> <buffer> th :call HighlightTagsubGroup()<CR>

nnoremap <silent> <buffer> thh :2match<CR>

function! TagsubSyntaxCheck()
  echo "Tagsub tag character"
  let c=nr2char(getchar())
  call MainTagFunction("syntaxCheck", c)
endfunction
nnoremap <silent> <buffer> t? :call TagsubSyntaxCheck()<CR>

function MainTagFunction(subFunction, tagchar)
python <<EOF
import vim
subFunction = vim.eval("a:subFunction")
assert subFunction in ("moveToNextGroupTag", "moveToPrevGroupTag",
  "moveToNextGroup", "moveToPrevGroup", "highlightGroup", "moveToParentGroup",
  "syntaxCheck", "moveToFirstGroupTag", "moveToLastGroupTag")
tagchar = vim.eval("a:tagchar")
assert len(tagchar)==1
# Code to work with subFunction will be below the next two function def's

def parseTags(tagchar):
  state="normal"
  curTagContents = ""
  for lineindex, line in enumerate(vim.current.buffer):
    for charindex, char in enumerate(line):
      if state=="normal":
        if char=="<":
          state = "inTag"
          startTag = (lineindex+1, charindex)
      elif state=="inTag":
        if char==tagchar:
          state = "tagsubTag"
          curTagContents = ""
        else:
          state = "normal"
      elif state=="tagsubTag":
        if char==">":
          state = "normal"
          endTag = (lineindex+1, charindex)
          yield (startTag, endTag, curTagContents)
        else:
          curTagContents += char
    # Only matters if we hit a tag that crosses a line boundary.
    curTagContents += '\n'
  raise StopIteration()

blockTags = set(['if', 'elif', 'else', '/if', 'loop', '/loop', 'case',
    'option', '/case', 'saveraw', '/saveraw', 'saveeval', '/saveeval',
    'saveoverride', '/saveoverride' ])
openingTags = set(['if','loop', 'case', 'saveraw', 'saveeval', 'saveoverride'])
closingTags = set([t for t in blockTags if t.startswith('/')])
nonOpeningTags = blockTags-openingTags
nonClosingTags = blockTags-closingTags
# Based on direction
allowedTagSequences = {
  (None, None): set(),
  ('if', None): set(['elif','else','/if']),
  ('if','elif'): set(['elif','else','/if']),
  ('if','else'): set(['/if']),
  ('loop', None): set(['/loop']),
  ('case', None): set(['option', 'else', '/case']),
  ('case', 'option'): set(['option', 'else', '/case']),
  ('case', 'else'): set(['/case']),
  ('saveraw', None): set(['/saveraw']),
  ('saveeval', None): set(['/saveeval']),
  ('saveoverride', None): set(['/saveoverride']),
}
def buildTagGroups(tagIterator):
  curLine, curCol = vim.current.window.cursor
  curTagIndex = None
  # A null entry to contain the top level tag groups.
  tagStack = [{'root':True, 'baseTag': None, 'curGroupTag': None, 'childGroups':[]}]
  tagIndex = 0
  for ((taglineindex, tagcharindex), (endtaglineindex, endtagcharindex), tagContents) in tagIterator:
    # Associate the tag with a tag group (if it is a grouped tag)
    baseTag = tagContents.split()[0]
    if baseTag not in blockTags:
      # We are only interested in block tags. Pretend any simple substitute
      #   tags do not exists for our purposes. And do not increment tagIndex.
      continue
    currentTagRec = {'baseTag': baseTag, 'tagIndex': tagIndex,
      'taglineindex':taglineindex, 'tagcharindex': tagcharindex,
      'endtaglineindex': endtaglineindex, 'endtagcharindex': endtagcharindex,
      'tagContents': tagContents}
    if baseTag in openingTags:
      # Push a new group on the tagStack
      tagGroupRec = {'baseTag': baseTag, 'curGroupTag': None, 'tags':[currentTagRec],
        'beginRegion': (taglineindex, tagcharindex), 'endRegion': None,
        'childGroups':[], 'parentGroup': tagStack[-1]}
      currentTagRec['tagGroup'] = tagGroupRec
      tagStack[-1]['childGroups'].append(tagGroupRec)
      tagStack.append(tagGroupRec)
    elif baseTag in allowedTagSequences[(tagStack[-1]['baseTag'], tagStack[-1]['curGroupTag'])]:
      tagStack[-1]['curGroupTag'] = currentTagRec['baseTag']
      tagStack[-1]['tags'].append(currentTagRec)
      if baseTag in closingTags:
        tagStack[-1]['endRegion'] = (endtaglineindex, endtagcharindex)
        # We discard finished tags because all will be children of some other
        #  group for finding later.
        tagStack.pop()
    else:
      # Found disallowed tag sequence.
      # Make some king of singleton null group with no baseTag we can use to
      #   show an error here...
      tagGroupRec = {'baseTag': None, 'curGroupTag': baseTag, 'tags':[currentTagRec],
        'beginRegion': (taglineindex, tagcharindex), 'endRegion': (endtaglineindex, endtagcharindex),
        'childGroups':[], 'parentGroup': tagStack[-1]}
      tagStack[-1]['childGroups'].append(tagGroupRec)
  # Discard any unclosed tag groups
  while len(tagStack) > 1:
    tagStack.pop()
  return tagStack[-1]['childGroups']

def isCursorPosBeforeRange(cursorPos, startRange):
  cursorLine, cursorCol = cursorPos
  startRangeLine, startRangeCol = startRange
  if cursorLine < startRangeLine:
    return True
  if cursorLine == startRangeLine and cursorCol < startRangeCol:
    return True
  return False

def isCursorPosAfterRange(cursorPos, endRange):
  cursorLine, cursorCol = cursorPos
  if not endRange:
    # Range does not end, so we are automatically not after the range
    return False
  endRangeLine, endRangeCol = endRange
  if cursorLine > endRangeLine:
    return True
  if cursorLine == endRangeLine and cursorCol > endRangeCol:
    return True
  return False

def isCursorPosInRange(cursorPos, startRange, endRange):
  if isCursorPosBeforeRange(cursorPos, startRange):
    return False
  if isCursorPosAfterRange(cursorPos, endRange):
    return False
  return True

def findCurrentGroup(tagGroups):
  cursorPos = vim.current.window.cursor
  for tagGroup in tagGroups:
    if isCursorPosInRange(cursorPos, tagGroup['beginRegion'], tagGroup['endRegion']):
      childGroup = findCurrentGroup(tagGroup['childGroups'])
      if childGroup:
        return childGroup
      else:
        return tagGroup
  else:
    return None

def findNextGroup(currentGroup):
  # May need some work inside a tag with children, but between thye children,
  #   it should probably find the next child?? Instead it finds the next peer
  #   of the containing tag
  if currentGroup:
    groupIndex = currentGroup['parentGroup']['childGroups'].index(currentGroup)
    nextGroupIndex = groupIndex + 1
    if nextGroupIndex < len(currentGroup['parentGroup']['childGroups']):
      return currentGroup['parentGroup']['childGroups'][nextGroupIndex]
    elif 'root' in currentGroup['parentGroup']:
      # No next group. At the top.
      return None
    else:
      return findNextGroup(currentGroup['parentGroup'])
  else:
    # Search the top level for a group
    cursorPos = vim.current.window.cursor
    for tagGroup in tagGroups:
      if isCursorPosBeforeRange(cursorPos, tagGroup['beginRegion']):
        return tagGroup
    else:
      return None

def findPrevGroup(currentGroup):
  # May need some work inside a tag with children, but between thye children,
  #   it should probably find the prev child?? Instead it finds the prev peer
  #   of the containing tag
  if currentGroup:
    groupIndex = currentGroup['parentGroup']['childGroups'].index(currentGroup)
    prevGroupIndex = groupIndex - 1
    if prevGroupIndex >= 0:
      return currentGroup['parentGroup']['childGroups'][prevGroupIndex]
    elif 'root' in currentGroup['parentGroup']:
      # No prev group. At the top.
      return None
    else:
      return findPrevGroup(currentGroup['parentGroup'])
  else:
    # Search the top level for a group
    cursorPos = vim.current.window.cursor
    for tagGroup in reversed(tagGroups):
      if isCursorPosAfterRange(cursorPos, tagGroup['endRegion']):
        return tagGroup
    else:
      return None
  
def highlightTags(tagList):
  tagRegAtoms = []
  for tag in tagList:
    tagStartAtom = r"\%%%dl\%%%dc" % (tag['taglineindex'], tag['tagcharindex']+1)
    tagEndAtom = r"\%%%dl\%%%dc" % (tag['endtaglineindex'], tag['endtagcharindex']+1)
    tagAtom = "%s\_.\{-}%s." % (tagStartAtom, tagEndAtom)
    tagRegAtoms.append(tagAtom)
  matchRegExp = r'\m' + '\|'.join(tagRegAtoms)
  cmd='2match TagSubGroup /%s/' % matchRegExp
  vim.command(cmd)

def highlightErrorTags():
  def getErrorTags(parentTagGroup, errorTagList):
    for childGroup in parentTagGroup['childGroups']:
      if not childGroup['baseTag'] or not childGroup['endRegion']:
        errorTagList.extend(childGroup["tags"])
      getErrorTags(childGroup, errorTagList)
  errorTagList = []
  if tagGroups:
    getErrorTags(tagGroups[0]['parentGroup'], errorTagList)

  if errorTagList:
    tagRegAtoms = []
    for tag in errorTagList:
      tagStartAtom = r"\%%%dl\%%%dc" % (tag['taglineindex'], tag['tagcharindex']+1)
      tagEndAtom = r"\%%%dl\%%%dc" % (tag['endtaglineindex'], tag['endtagcharindex']+1)
      tagAtom = "%s\_.\{-}%s." % (tagStartAtom, tagEndAtom)
      tagRegAtoms.append(tagAtom)
    matchRegExp = r'\m' + '\|'.join(tagRegAtoms)
    cmd='2match TagSubErrorGroup /%s/' % matchRegExp
    vim.command(cmd)
    return errorTagList[0]

# All of our searching functions should look through this list of tag groups
tagGroups = buildTagGroups(parseTags(tagchar))

if subFunction == "moveToNextGroupTag":
  vim.command("2match")
  currentGroup = findCurrentGroup(tagGroups)
  if currentGroup:
    # Find the current tag in the group or next if between tags.
    #   if at end, skip to first
    highlightTags(currentGroup['tags'])
    cursorPos = vim.current.window.cursor
    for tag in currentGroup['tags']:
      if isCursorPosBeforeRange(cursorPos, (tag['taglineindex'], tag['tagcharindex'])):
        # Set the window cursor to that tag pos
        vim.current.window.cursor = (tag['taglineindex'], tag['tagcharindex'])
        break
elif subFunction == "moveToPrevGroupTag":
  vim.command("2match")
  currentGroup = findCurrentGroup(tagGroups)
  if currentGroup:
    highlightTags(currentGroup['tags'])
    cursorPos = vim.current.window.cursor
    for tag in reversed(currentGroup['tags']):
      if isCursorPosAfterRange(cursorPos, (tag['endtaglineindex'], tag['endtagcharindex'])):
        # Set the window cursor to that tag pos
        vim.current.window.cursor = (tag['taglineindex'], tag['tagcharindex'])
        break
elif subFunction == "moveToLastGroupTag":
  vim.command("2match")
  currentGroup = findCurrentGroup(tagGroups)
  if currentGroup:
    highlightTags(currentGroup['tags'])
    lastTag = currentGroup['tags'][-1]
    vim.current.window.cursor = (lastTag['taglineindex'], lastTag['tagcharindex'])
elif subFunction == "moveToFirstGroupTag":
  vim.command("2match")
  currentGroup = findCurrentGroup(tagGroups)
  if currentGroup:
    highlightTags(currentGroup['tags'])
    firstTag = currentGroup['tags'][0]
    vim.current.window.cursor = (firstTag['taglineindex'], firstTag['tagcharindex'])
elif subFunction == "moveToNextGroup":
  currentGroup = findCurrentGroup(tagGroups)
  nextGroup = findNextGroup(currentGroup)
  if nextGroup:
    highlightTags(nextGroup['tags'])
    # Set the window cursor to that tag pos
    vim.current.window.cursor = nextGroup['beginRegion']
elif subFunction == "moveToPrevGroup":
  currentGroup = findCurrentGroup(tagGroups)
  prevGroup = findPrevGroup(currentGroup)
  if prevGroup:
    highlightTags(prevGroup['tags'])
    # Set the window cursor to that tag pos
    vim.current.window.cursor = prevGroup['beginRegion']
elif subFunction == "highlightGroup":
  vim.command("2match")
  currentGroup = findCurrentGroup(tagGroups)
  if currentGroup:
    # highlight all tags in the current group. Do not move cursor
    highlightTags(currentGroup['tags'])
elif subFunction == "moveToParentGroup":
  currentGroup = findCurrentGroup(tagGroups)
  parentGroup = currentGroup['parentGroup']
  if 'root' not in parentGroup:
    highlightTags(parentGroup['tags'])
    vim.current.window.cursor = parentGroup['beginRegion']
elif subFunction == "syntaxCheck":
  vim.command("2match")
  # Walk through and find the first error condition (unclosed group or out of place tag)
  # Output message and move cursor to that location
  firstErrorTag = highlightErrorTags()
  if firstErrorTag:
    vim.current.window.cursor = (firstErrorTag['taglineindex'], firstErrorTag['tagcharindex'])

EOF
endfunction
