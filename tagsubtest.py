import unittest
import collections.abc
import operator

import tagsub
from tagsub.Template import NamespaceStack, TemplateIterator
from tagsub.exceptions import TagStackOverflowError, InvalidTagKeyName, ExpressionError, ExpressionStackOverflowError
from tagsub.exceptions import TagsubTemplateSyntaxError, TagcharSequenceMismatchError


## TODO Test actually hitting EOF while in a tag. Does it properly detect an error? especially if it has INCREFed a string.
##      Do all references get properly released?

## TODO Try the above variations for each and every tag.

## TODO Overflow tags and whitespace variations and overflow saveeval stack for saveeval tags.

# function for testing reference_counts before and after tagsub.substitute
# XXX We have eliminated this since we are now Pure Python
from tagsub.tags.values.Operator import Operator
from tagsub.util.Stack import Stack


def substitute(tagchars, template, seq_dict, **kwargs):
    result = tagsub.substitute(tagchars, template, seq_dict, **kwargs)
    return result


class tagsub_TestCase(unittest.TestCase):
    def assertRaisesAndMatchesTraceback(self, excClass, excTokenText, callableObj, *args, **kwargs):
        try:
            callableObj(*args, **kwargs)
        except excClass as e:
            tb = e.args[0].split()[-1]
            if tb == excTokenText:
                return
            else:
                raise self.failureException('traceback: "%s" != "%s"' % (tb, excTokenText))
        except:
            if hasattr(excClass, '__name__'):
                excName = excClass.__name__
            else:
                excName = str(excClass)
            raise self.failureException(excName)


class tagsubTestSimple(tagsub_TestCase):
    def test_tag_simple0(self):
        # This is an important case that we never tested until 1.57
        self.assertEqual('', substitute('@', '', {}))

    def test_tag_simple0a(self):
        self.assertEqual('abc', substitute('@', 'abc', {}))

    def test_tag_simple1(self):
        # Simple case of substitution
        d = {'tag1': 'value1', 'tag2': 'value2'}
        result = substitute('@', '<@tag1> <@ tag2>', d)
        self.assertEqual(result, 'value1 value2')
        result = substitute('@', 'x<@tag1> <@ tag2>x', d)
        self.assertEqual(result, 'xvalue1 value2x')
        result = substitute('@', 'x<@ \ttag1\n > <@\ttag2  \n>x', d)
        self.assertEqual('xvalue1 value2x', result)

    def test_tag_simple2(self):
        # test that a missing key substitutes as an empty string
        result = substitute('@', '<@tag>', [{}])
        self.assertEqual('', result)
        result = substitute('@', 'x<@tag>x', [{}])
        self.assertEqual('xx', result)
        result = substitute('@', 'x<@tag >x', [{}])
        self.assertEqual('xx', result)
        # but test that if fails when strict lookups are enabled
        self.assertRaisesAndMatchesTraceback(KeyError,
                                             '1(1,1)',
                                             substitute, '@',
                                             '<@tag>', [{}], doStrictKeyLookup=True)
        self.assertRaisesAndMatchesTraceback(KeyError,
                                             '2(1,2)',
                                             substitute, '@',
                                             'x<@tag>x', [{}], doStrictKeyLookup=True)

    def test_tag_simple3(self):
        # Test that None is substituted as an empty string
        result = substitute('@', 'x<@tag>x', [{'tag': None}])
        self.assertEqual(result, 'xx')
        result = substitute('@', '<@tag>', [{'tag': None}])
        self.assertEqual('', result)

    def test_tag_simple4(self):
        # Test a false start on a tag
        result = substitute('@', '<<@tag>', {})
        self.assertEqual('<', result)

    def test_tag_simple_multiple_tagchars(self):
        result = substitute(
            '@#',
            'x<@tag> <#tag>x',
            [{'tag': 'value @'}, {'tag': 'value #'}]
        )
        self.assertEqual('xvalue @ value #x', result)
        result = substitute(
            '@#',
            '<@tag> <#tag>',
            [{'tag': 'value @'}, {'tag': 'value #'}]
        )
        self.assertEqual('value @ value #', result)

    # Try an empty tagchar string, and an empty list of mappings. It should result in the template unchanged.
    #   Also try with doSuppressComments=True to see comments suppressed out.
    def test_tag_simple5(self):
        result = substitute('', '<@test> <!-- test comment \n and newline -->', [])
        self.assertEqual('<@test> <!-- test comment \n and newline -->', result)

    def test_tag_simple6(self):
        result = substitute('', '<@test> <!-- test comment \n and newline -->x', [], doSuppressComments=True)
        self.assertEqual('<@test> x', result)


class tagsubTestMultipleTagchars(tagsub_TestCase):
    def setUp(self):
        self.tagchars = '@#'
        self.dicts = [
            {
                'test': 'global @ value',
                'loop': [
                    {'test': 'loop @ value 1'},
                    {'test': 'loop @ value 2'},
                ],
            },
            {
                'test': 'global # value',
                'loop': [
                    {'test': 'loop # value 1'},
                    {'test': 'loop # value 2'},
                ],
            },
        ]

    def test_nested_loop1(self):
        # test should skip the inner loop dict and get its value from the outer
        result = substitute(self.tagchars,
                            '<@loop loop><#loop loop><@test><#/loop><@/loop>',
                            self.dicts
                            )
        self.assertEqual(result, 'loop @ value 1' * 2 + 'loop @ value 2' * 2)

    def test_nested_loop1a(self):
        # test should skip the inner loop dict and get its value from the outer
        result = substitute(self.tagchars,
                            '<@loop loop ><#loop\tloop\n><@test><#/loop><@/loop>',
                            self.dicts
                            )
        self.assertEqual(result, 'loop @ value 1' * 2 + 'loop @ value 2' * 2)

    def test_nested_loop1b(self):
        # In this case both looks should be evaluated in scan mode to just syntax check them but not evaluate
        result = substitute(self.tagchars,
                            '<@if true><@loop loop><#loop loop><@test><#/loop><@/loop><@else>false<@/if>',
                            self.dicts
                            )
        self.assertEqual(result, 'false')

    def test_nested_loop2(self):
        # test should get its value from the inner loop dict
        result = substitute(self.tagchars,
                            '<@loop loop><#loop loop><#test><#/loop><@/loop>',
                            self.dicts
                            )
        self.assertEqual(result, 'loop # value 1loop # value 2' * 2)

    def test_nested_loop3(self):
        # Repeat test_nested_loop1 and test_nested_loop2 in the same
        #   function. This originally helped to manifest reference counting
        #   bugs.
        result = substitute(self.tagchars,
                            '<@loop loop><#loop loop><@test><#/loop><@/loop>',
                            self.dicts
                            )
        self.assertEqual(result, 'loop @ value 1' * 2 + 'loop @ value 2' * 2)
        result = substitute(self.tagchars,
                            '<@loop loop><#loop loop><#test><#/loop><@/loop>',
                            self.dicts
                            )
        self.assertEqual(result, 'loop # value 1loop # value 2' * 2)

    def test_mismatched_tagtypes1(self):
        self.assertRaisesAndMatchesTraceback(TagsubTemplateSyntaxError,
                                             '15(1,15)',
                                             substitute, '@#',
                                             '<@if test>test<#elif test2>test2<@/if>', [{'test': 0}, {'test2': 1}])

    def test_mismatched_tagtypes2(self):
        self.assertRaisesAndMatchesTraceback(TagsubTemplateSyntaxError,
                                             '15(1,15)',
                                             substitute, '@#',
                                             '<@if test>test<#else>test2<@/if>', [{'test': 0}, {}])

    def test_mismatched_tagtypes3(self):
        self.assertRaisesAndMatchesTraceback(TagsubTemplateSyntaxError,
                                             '27(1,27)',
                                             substitute, '@#',
                                             '<@if test>test<@else>test2<#/if>', [{'test': 0}, {}])

    def test_mismatched_tagtypes4(self):
        self.assertRaisesAndMatchesTraceback(TagsubTemplateSyntaxError,
                                             '15(1,15)',
                                             substitute, '@#',
                                             '<@if test>test<#/if>', [{'test': 0}, {}])

    def test_mismatched_tagtypes5(self):
        self.assertRaisesAndMatchesTraceback(TagsubTemplateSyntaxError,
                                             '13(1,13)',
                                             substitute, '@#',
                                             '<@case test><#option "0">test<@/case>', [{'test': 0}, {}])

    def test_mismatched_tagtypes6(self):
        self.assertRaisesAndMatchesTraceback(TagsubTemplateSyntaxError,
                                             '30(1,30)',
                                             substitute, '@#',
                                             '<@case test><@option "0">test<#else>none<@/case>', [{'test': 0}, {}])

    def test_mismatched_tagtypes7(self):
        self.assertRaisesAndMatchesTraceback(TagsubTemplateSyntaxError,
                                             '41(1,41)',
                                             substitute, '@#',
                                             '<@case test><@option "0">test<@else>none<#/case>', [{'test': 0}, {}])

    def test_mismatched_tagtypes8(self):
        self.assertRaisesAndMatchesTraceback(TagsubTemplateSyntaxError,
                                             '41(1,41)',
                                             substitute, '@#',
                                             '<@case test><@option "0">test<@else>none<#/case>', [{}, {}])

    def test_mismatched_tagtypes9(self):
        self.assertRaisesAndMatchesTraceback(TagsubTemplateSyntaxError,
                                             '17(1,17)',
                                             substitute, '@#',
                                             '<@loop test>test<#/loop>', [{'test': [{}, {}]}, {}])

    def test_mismatched_tagtypes10(self):
        self.assertRaisesAndMatchesTraceback(TagsubTemplateSyntaxError,
                                             '20(1,20)',
                                             substitute, '@#',
                                             '<@saveraw test>test<#/saveraw>', [{}, {}])

    def test_mismatched_tagtypes11(self):
        self.assertRaisesAndMatchesTraceback(TagsubTemplateSyntaxError,
                                             '21(1,21)',
                                             substitute, '@#',
                                             '<@saveeval test>test<#/saveeval>', [{}, {}])

    def test_mismatched_tagtypes12(self):
        self.assertRaisesAndMatchesTraceback(TagsubTemplateSyntaxError,
                                             '26(1,26)',
                                             substitute, '@#',
                                             '<@saveeval test> <@test> <#/saveeval>', [{}, {}])

    def test_mismatched_tagtypes13(self):
        self.assertRaisesAndMatchesTraceback(TagsubTemplateSyntaxError,
                                             '22(1,22)',
                                             substitute, '@#',
                                             '<@namespace test>test<#/namespace>', [{'test': {}}, {}])

    def test_mismatched_tagtypes14(self):
        self.assertRaisesAndMatchesTraceback(TagsubTemplateSyntaxError,
                                             '27(1,27)',
                                             substitute, '@#',
                                             '<@namespace test> <@test> <#/namespace>', [{'test': {}}, {}])


class tagsubTestTypeErrors(tagsub_TestCase):
    def test_tag_insufficient_arguments(self):
        self.assertRaises(TypeError, substitute, '@', '')

    def test_tag_bad_keyword_arg(self):
        self.assertRaises(TypeError, substitute, '@', '', {}, badKeywordArg=0)

    def test_tag_simple_Mismatch1(self):
        # Multiple tagchars for a single mapping
        self.assertRaises(TagcharSequenceMismatchError, substitute, '@#', '', {})

    def test_tag_simple_Mismatch2(self):
        # Longer tagchars than sequence
        self.assertRaises(TagcharSequenceMismatchError, substitute, '@#', '', [{}])

    def test_tag_simple_Mismatch2a(self):
        # No tagchars with sequence
        self.assertRaises(TagcharSequenceMismatchError, substitute, '', '', [{}])

    def test_tag_simple_Mismatch3(self):
        # Longer sequence than tagchars
        self.assertRaises(TagcharSequenceMismatchError, substitute, '@', '', [{}, {}])

    def test_tag_simple_Mismatch3a(self):
        # No sequence with tagchars
        self.assertRaises(TagcharSequenceMismatchError, substitute, '@', '', [])

    def test_tag_simple_Mismatch4(self):
        # All mappings in the list must actually be mappings
        self.assertRaises(TypeError, substitute, '@#', '', [None, {}])

    def test_tag_simple_Mismatch5(self):
        # All mappings in the list must actually be mappings
        self.assertRaises(TypeError, substitute, '@#', '', [{}, None])

    def test_tag_simple_TypeError1(self):
        # Not a string tagchar
        self.assertRaises(TypeError, substitute, None, '', [{}, {}])

    def test_tag_simple_TypeError2(self):
        # Not a string template
        self.assertRaises(TypeError, substitute, '', None, [{}, {}])

    def test_tag_simple_TypeError3(self):
        # Not a Mapping or Sequence data argument
        self.assertRaises(TypeError, substitute, '@', '', None)

    def test_tag_loop_sequence(self):
        # A loop's value must be a sequence
        self.assertRaisesAndMatchesTraceback(TypeError,
                                             '1(1,1)',
                                             substitute,
                                             '@', '<@loop list><@/loop>', {'list': 9})

    def test_tag_loop_sequence1a(self):
        # Do a test on an empty list. Should never execute the loop
        result = substitute('@', '<@loop list>text<@/loop>', {'list': []})
        self.assertEqual(result, '')

    def test_tag_loop_sequence2(self):
        # A loop's value must be a sequence, but elements that
        #   test as false (or are missing) are equivalent to
        #   an empty list.
        result = substitute('@', '<@loop list>text<@/loop>', {'list': None})
        self.assertEqual(result, '')

    def test_tag_loop_sequence3(self):
        # A loop's value must be a sequence, but elements that
        #   test as false (or are missing) are equivalent to
        #   an empty list.
        result = substitute('@', '<@loop list>text<@/loop>', {'list': 0})
        self.assertEqual(result, '')

    def test_tag_loop_sequence4(self):
        # A loop's value must be a sequence of dicts
        # Check the first element
        self.assertRaisesAndMatchesTraceback(TypeError,
                                             '1(1,1)',
                                             substitute,
                                             '@', '<@loop list><@/loop>', {'list': [None, {}]})

    def test_tag_loop_sequence5(self):
        # A loop's value must be a sequence of dicts
        # Check a later element this covers different
        #  code than the test above.
        self.assertRaisesAndMatchesTraceback(TypeError,
                                             '1(1,1)[2]:',
                                             substitute,
                                             '@', '<@loop list><@/loop>', {'list': [{}, None]})

    def test_tag_namespace_mapping1(self):
        # A namespace's value must be a mapping
        self.assertRaisesAndMatchesTraceback(TypeError,
                                             '1(1,1)',
                                             substitute,
                                             '@', '<@namespace dict><@/namespace>', {'dict': 9})

    def test_tag_namespace_mapping2(self):
        # A namespace's value must be a mapping
        self.assertRaisesAndMatchesTraceback(TypeError,
                                             '1(1,1)',
                                             substitute,
                                             '@', '<@namespace dict><@/namespace>', {'dict': []})

    def test_tag_namespace_mapping3(self):
        # A namespace's value must be a mapping
        self.assertRaisesAndMatchesTraceback(TypeError,
                                             '1(1,1)',
                                             substitute,
                                             '@', '<@namespace dict><@/namespace>', {'dict': None})


class tagsubTestLegalKeyNames(tagsub_TestCase):
    def test_empty_key1(self):
        # We do not allow an empty key name
        self.assertRaisesAndMatchesTraceback(InvalidTagKeyName,
                                             '1(1,1)',
                                             substitute,
                                             '@', '<@>', {})

    def test_empty_key2(self):
        # We do not allow an empty key name
        self.assertRaisesAndMatchesTraceback(InvalidTagKeyName,
                                             '1(1,1)',
                                             substitute,
                                             '@', '<@ >', {})

    def test_empty_key3(self):
        # We do not allow an empty key name
        self.assertRaisesAndMatchesTraceback(InvalidTagKeyName,
                                             '1(1,1)',
                                             substitute,
                                             '@', '<@if ><@/if>', {})

    def test_empty_key3a(self):
        # We do not allow an empty key name
        self.assertRaisesAndMatchesTraceback(InvalidTagKeyName,
                                             '1(1,1)',
                                             substitute,
                                             '@', '<@if><@/if>', {})

    def test_empty_key4(self):
        # We do not allow an empty key name
        self.assertRaisesAndMatchesTraceback(InvalidTagKeyName,
                                             '1(1,1)',
                                             substitute,
                                             '@', '<@case ><@/case>', {})

    def test_empty_key4a(self):
        # We do not allow an empty key name
        self.assertRaisesAndMatchesTraceback(InvalidTagKeyName,
                                             '1(1,1)',
                                             substitute,
                                             '@', '<@case><@/case>', {})

    def test_empty_key5(self):
        # We do not allow an empty key name
        self.assertRaisesAndMatchesTraceback(InvalidTagKeyName,
                                             '1(1,1)',
                                             substitute,
                                             '@', '<@saveraw ><@/saveraw>', {})

    def test_empty_key5a(self):
        # We do not allow an empty key name
        self.assertRaisesAndMatchesTraceback(InvalidTagKeyName,
                                             '1(1,1)',
                                             substitute,
                                             '@', '<@saveraw><@/saveraw>', {})

    def test_empty_key6(self):
        # We do not allow an empty key name
        self.assertRaisesAndMatchesTraceback(InvalidTagKeyName,
                                             '1(1,1)',
                                             substitute,
                                             '@', '<@loop ><@/loop>', {})

    def test_empty_key6a(self):
        # We do not allow an empty key name
        self.assertRaisesAndMatchesTraceback(InvalidTagKeyName,
                                             '1(1,1)',
                                             substitute,
                                             '@', '<@loop><@/loop>', {})

    def test_empty_key7(self):
        # We do not allow an empty key name
        self.assertRaisesAndMatchesTraceback(InvalidTagKeyName,
                                             '1(1,1)',
                                             substitute,
                                             '@', '<@saveeval ><@/saveeval>', {})

    def test_empty_key7a(self):
        # We do not allow an empty key name
        self.assertRaisesAndMatchesTraceback(InvalidTagKeyName,
                                             '1(1,1)',
                                             substitute,
                                             '@', '<@saveeval><@/saveeval>', {})

    def test_empty_key8(self):
        # We do not allow an empty key name
        self.assertRaisesAndMatchesTraceback(InvalidTagKeyName,
                                             '1(1,1)',
                                             substitute,
                                             '@', '<@namespace ><@/namespace>', {})

    def test_empty_key8a(self):
        # We do not allow an empty key name
        self.assertRaisesAndMatchesTraceback(InvalidTagKeyName,
                                             '1(1,1)',
                                             substitute,
                                             '@', '<@namespace><@/namespace>', {})

    def test_empty_key9(self):
        # We do not allow an empty key name
        self.assertRaisesAndMatchesTraceback(InvalidTagKeyName,
                                             '1(1,1)',
                                             substitute,
                                             '@', '<@saveoverride ><@/saveoverride>', {})

    def test_empty_key9a(self):
        # We do not allow an empty key name
        self.assertRaisesAndMatchesTraceback(InvalidTagKeyName,
                                             '1(1,1)',
                                             substitute,
                                             '@', '<@saveoverride><@/saveoverride>', {})


class tagsubTestOverflows(tagsub_TestCase):
    def setUp(self):
        self.nestedTagTemplate = ''.join(map(lambda i: '<@if %d>' % i, range(1, tagsub.max_nested_tag_depth + 1)))
        self.nestedTagPos = len(self.nestedTagTemplate) + 1

    def test_LoopStackOverflowError3(self):
        # This will not overflow, but with the bad structure
        # should get a SyntaxError instead
        tag = '<@loop test>'
        template = ''
        for i in range(tagsub.max_nested_tag_depth):
            template = '%s%s' % (tag, template)
        tb = '%d(1,%d)' % ((len(tag) * (tagsub.max_nested_tag_depth - 1) + 1,) * 2)
        self.assertRaisesAndMatchesTraceback(TagsubTemplateSyntaxError,
                                             tb,
                                             substitute, '@',
                                             template,
                                             {'test': [{}]}
                                             )

    def test_LoopStackOverflowError3a(self):
        # This is like the one above, but has proper syntax
        template = ''
        for i in range(tagsub.max_nested_tag_depth):
            template = '<@loop test>%s<@/loop>' % template
        result = substitute('@', template, {'test': [{}]})
        self.assertEqual(result, '')

    def test_LoopStackOverflowError4(self):
        # No matter what the tagchar, they share the same stack
        tagsubCharList = '@#$%^&*+='
        tag = '<%sloop test>'
        template = ''
        for i in range(tagsub.max_nested_tag_depth + 1):
            template = '%s%s' % (tag % tagsubCharList[i % 9], template)
        tb = '%d(1,%d)' % ((len(tag % '@') * tagsub.max_nested_tag_depth + 1,) * 2)
        self.assertRaisesAndMatchesTraceback(TagStackOverflowError,
                                             tb,
                                             substitute, tagsubCharList,
                                             template,
                                             [{'test': [{}]}, ] * len(tagsubCharList)
                                             )

    def test_LoopStackOverflowError5(self):
        tag1 = '<@loop test>'
        tag2 = '<@namespace test2>'
        tb = '%d(1,%d)' % ((len(tag1) * (tagsub.max_nested_tag_depth - 1) + len(tag2) + 1,) * 2)
        self.assertRaisesAndMatchesTraceback(TagStackOverflowError,
                                             tb,
                                             substitute, '@',
                                             tag1 * (tagsub.max_nested_tag_depth - 1) + tag2 * 2,
                                             {'test': [{}], 'test2': {}}
                                             )

    def test_LoopStackOverflowError6(self):
        # This will not overflow, but with the bad structure
        # should get a SyntaxError instead
        tag1 = '<@loop test>'
        tag2 = '<@namespace test2>'
        tb = '%d(1,%d)' % ((len(tag1) * (tagsub.max_nested_tag_depth - 2) + len(tag2) + 1,) * 2)
        self.assertRaisesAndMatchesTraceback(TagsubTemplateSyntaxError,
                                             tb,
                                             substitute, '@',
                                             tag1 * (tagsub.max_nested_tag_depth - 2) + tag2 * 2,
                                             {'test': [{}], 'test2': {}}
                                             )

    def test_LoopStackOverflowError7(self):
        # No matter what the tagchar, they share the same stack
        tagsubCharList = '@#$%^&*+='
        tag = '<%snamespace test>'
        template = ''
        for i in range(tagsub.max_nested_tag_depth + 1):
            template = '%s%s' % (tag % tagsubCharList[i % 9], template)
        tb = '%d(1,%d)' % ((len(tag % '@') * tagsub.max_nested_tag_depth + 1,) * 2)
        self.assertRaisesAndMatchesTraceback(TagStackOverflowError,
                                             tb,
                                             substitute, tagsubCharList,
                                             template,
                                             [{'test': {}}, ] * len(tagsubCharList)
                                             )

    ## Try the overflows with each nestable tag, since the testing for
    ##    overflow happens independently for each tag group.
    def test_nestedTagOverflow1(self):
        template = self.nestedTagTemplate + '<@if %d>' % (tagsub.max_nested_tag_depth + 1)
        self.assertRaisesAndMatchesTraceback(TagStackOverflowError,
                                             '%d(1,%d)' % (self.nestedTagPos, self.nestedTagPos),
                                             substitute, '@',
                                             template,
                                             {})

    def test_nestedTagOverflow2(self):
        pos = self.nestedTagPos - (len('<@if >') + len(str(tagsub.max_nested_tag_depth)))
        self.assertRaisesAndMatchesTraceback(TagsubTemplateSyntaxError,
                                             '%d(1,%d)' % (pos, pos),
                                             substitute, '@',
                                             self.nestedTagTemplate,
                                             {})

    def test_nestedTagOverflow3(self):
        # Like the loop tag stack, multiple tagchars share the same stack
        template = self.nestedTagTemplate + '<#if %d>' % (tagsub.max_nested_tag_depth + 1)
        self.assertRaisesAndMatchesTraceback(TagStackOverflowError,
                                             '%d(1,%d)' % (self.nestedTagPos, self.nestedTagPos),
                                             substitute, '@#',
                                             template,
                                             [{}, {}])

    # Test variations with each tag
    def test_nestedTagOverflow4(self):
        template = self.nestedTagTemplate + '<@case %d>' % (tagsub.max_nested_tag_depth + 1)
        self.assertRaisesAndMatchesTraceback(TagStackOverflowError,
                                             '%d(1,%d)' % (self.nestedTagPos, self.nestedTagPos),
                                             substitute, '@',
                                             template,
                                             {})

    def test_nestedTagOverflow5(self):
        template = self.nestedTagTemplate + '<@loop %d>' % (tagsub.max_nested_tag_depth + 1)
        self.assertRaisesAndMatchesTraceback(TagStackOverflowError,
                                             '%d(1,%d)' % (self.nestedTagPos, self.nestedTagPos),
                                             substitute, '@',
                                             template,
                                             {})

    def test_nestedTagOverflow6(self):
        template = self.nestedTagTemplate + '<@saveraw %d>' % (tagsub.max_nested_tag_depth + 1)
        self.assertRaisesAndMatchesTraceback(TagStackOverflowError,
                                             '%d(1,%d)' % (self.nestedTagPos, self.nestedTagPos),
                                             substitute, '@',
                                             template,
                                             {})

    def test_nestedTagOverflow7(self):
        template = self.nestedTagTemplate + '<@saveeval %d>' % (tagsub.max_nested_tag_depth + 1)
        self.assertRaisesAndMatchesTraceback(TagStackOverflowError,
                                             '%d(1,%d)' % (self.nestedTagPos, self.nestedTagPos),
                                             substitute, '@',
                                             template,
                                             {})

    def test_nestedTagOverflow8(self):
        template = self.nestedTagTemplate + '<@namespace %d>' % (tagsub.max_nested_tag_depth + 1)
        self.assertRaisesAndMatchesTraceback(TagStackOverflowError,
                                             '%d(1,%d)' % (self.nestedTagPos, self.nestedTagPos),
                                             substitute, '@',
                                             template,
                                             {})

    def test_nestedTagOverflow9(self):
        template = self.nestedTagTemplate + '<@saveoverride %d>' % (tagsub.max_nested_tag_depth + 1)
        self.assertRaisesAndMatchesTraceback(TagStackOverflowError,
                                             '%d(1,%d)' % (self.nestedTagPos, self.nestedTagPos),
                                             substitute, '@',
                                             template,
                                             {})

    def test_nestedSaveEvalOverflow2(self):
        # The current max_depth is 4, but the top level result takes one.
        self.assertEqual(tagsub.max_saveeval_depth, 4)
        self.assertRaisesAndMatchesTraceback(TagsubTemplateSyntaxError,
                                             '29(1,29)',
                                             substitute, '@',
                                             '<@saveeval t1><@saveeval t2><@saveeval t3>', {})


class tagsub_if_tests(tagsub_TestCase):
    def test_basic_if_else(self):
        result = substitute('@', '<@if isTrue>true<@else>false<@/if>', {'isTrue': 1})
        self.assertEqual(result, 'true')
        result = substitute('@', '<@if\tisTrue >true<@else>false<@/if>', {'isTrue': 1})
        self.assertEqual(result, 'true')
        result = substitute('@', '<@if isTrue>true<@else>false<@/if>', {'isTrue': 1}, doStrictKeyLookup=True)
        self.assertEqual(result, 'true')

    def test_basic_if_else2(self):
        result = substitute('@', '<@if isTrue>true<@else>false<@/if>', {'isTrue': 0})
        self.assertEqual(result, 'false')
        result = substitute('@', '<@if isTrue>true<@else>false<@/if>', {'isTrue': 0}, doStrictKeyLookup=True)
        self.assertEqual(result, 'false')

    def test_basic_if_else3(self):
        result = substitute('@', '<@if isTrue>true<@else>false<@/if>', {'isTrue': None})
        self.assertEqual(result, 'false')
        result = substitute('@', '<@if isTrue>true<@else>false<@/if>', {'isTrue': None}, doStrictKeyLookup=True)
        self.assertEqual(result, 'false')

    def test_basic_if_else4(self):
        result = substitute('@', '<@if isTrue>true<@else>false<@/if>', {'isTrue': '1'})
        self.assertEqual(result, 'true')
        result = substitute('@', '<@if isTrue>true<@else>false<@/if>', {'isTrue': '1'}, doStrictKeyLookup=True)
        self.assertEqual(result, 'true')

    def test_basic_if_else5(self):
        result = substitute('@', '<@if isTrue>true<@else>false<@/if>', {'isTrue': ''})
        self.assertEqual(result, 'false')
        result = substitute('@', '<@if isTrue>true<@else>false<@/if>', {'isTrue': ''}, doStrictKeyLookup=True)
        self.assertEqual(result, 'false')

    def test_basic_if_else6(self):
        result = substitute('@', '<@if isTrue>true<@else>false<@/if>', {'isTrue': '0'}, is0False=True)
        self.assertEqual(result, 'false')
        result = substitute('@', '<@if isTrue>true<@else>false<@/if>', {'isTrue': '0'},
                            is0False=True, doStrictKeyLookup=True)
        self.assertEqual(result, 'false')

    def test_basic_if_else6a(self):
        result = substitute('@', '<@if isTrue>true<@else>false<@/if>', {'isTrue': '0'}, is0False=False)
        self.assertEqual(result, 'true')
        result = substitute('@', '<@if isTrue>true<@else>false<@/if>', {'isTrue': '0'},
                            is0False=False, doStrictKeyLookup=True)
        self.assertEqual(result, 'true')

    def test_basic_if_else7(self):
        result = substitute('@', '<@if isTrue>true<@else>false<@/if>', {'isTrue': []})
        self.assertEqual(result, 'false')
        result = substitute('@', '<@if isTrue>true<@else>false<@/if>', {'isTrue': []}, doStrictKeyLookup=True)
        self.assertEqual(result, 'false')

    def test_basic_if_else8(self):
        result = substitute('@', '<@if isTrue>true<@else>false<@/if>', {'isTrue': {}}, doStrictKeyLookup=True)
        self.assertEqual(result, 'false')

    def test_basic_if_else9(self):
        result = substitute('@', '<@if isTrue>true<@else>false<@/if>', {})
        self.assertEqual(result, 'false')
        self.assertRaisesAndMatchesTraceback(KeyError,
                                             '1(1,1)',
                                             substitute, '@',
                                             '<@if isTrue>true<@else>false<@/if>', {}, doStrictKeyLookup=True)

    ## The next eight test all combinations of truth of three values
    def test_basic_if_else10(self):
        result = substitute('@',
                            '<@if isOne>one<@elif isTwo>two<@elif isThree>three<@else>none<@/if>',
                            {'isOne': 0, 'isTwo': 0, 'isThree': 0}
                            )
        self.assertEqual(result, 'none')
        result = substitute('@',
                            '<@if isOne >one<@elif\tisTwo\n>two<@elif isThree\n>three<@else>none<@/if>',
                            {'isOne': 0, 'isTwo': 0, 'isThree': 0}
                            )
        self.assertEqual(result, 'none')

    def test_basic_if_else11(self):
        result = substitute('@',
                            '<@if isOne>one<@elif isTwo>two<@elif isThree>three<@else>none<@/if>',
                            {'isOne': 0, 'isTwo': 0, 'isThree': 1}
                            )
        self.assertEqual(result, 'three')
        result = substitute('@',
                            '<@if isOne >one<@elif\tisTwo\n>two<@elif isThree\n>three<@else>none<@/if>',
                            {'isOne': 0, 'isTwo': 0, 'isThree': 1}
                            )
        self.assertEqual(result, 'three')

    def test_basic_if_else12(self):
        result = substitute('@',
                            '<@if isOne>one<@elif isTwo>two<@elif isThree>three<@else>none<@/if>',
                            {'isOne': 0, 'isTwo': 1, 'isThree': 0}
                            )
        self.assertEqual(result, 'two')
        result = substitute('@',
                            '<@if isOne >one<@elif\tisTwo\n>two<@elif isThree\n>three<@else>none<@/if>',
                            {'isOne': 0, 'isTwo': 1, 'isThree': 0}
                            )
        self.assertEqual(result, 'two')

    def test_basic_if_else13(self):
        result = substitute('@',
                            '<@if isOne>one<@elif isTwo>two<@elif isThree>three<@else>none<@/if>',
                            {'isOne': 0, 'isTwo': 1, 'isThree': 1}
                            )
        self.assertEqual(result, 'two')
        result = substitute('@',
                            '<@if isOne >one<@elif\tisTwo\n>two<@elif isThree\n>three<@else>none<@/if>',
                            {'isOne': 0, 'isTwo': 1, 'isThree': 1}
                            )
        self.assertEqual(result, 'two')

    def test_basic_if_else14(self):
        result = substitute('@',
                            '<@if isOne>one<@elif isTwo>two<@elif isThree>three<@else>none<@/if>',
                            {'isOne': 1, 'isTwo': 0, 'isThree': 0}
                            )
        self.assertEqual(result, 'one')
        result = substitute('@',
                            '<@if isOne >one<@elif\tisTwo\n>two<@elif isThree\n>three<@else>none<@/if>',
                            {'isOne': 1, 'isTwo': 0, 'isThree': 0}
                            )
        self.assertEqual(result, 'one')

    def test_basic_if_else15(self):
        result = substitute('@',
                            '<@if isOne>one<@elif isTwo>two<@elif isThree>three<@else>none<@/if>',
                            {'isOne': 1, 'isTwo': 0, 'isThree': 1}
                            )
        self.assertEqual(result, 'one')
        result = substitute('@',
                            '<@if isOne >one<@elif\tisTwo\n>two<@elif isThree\n>three<@else>none<@/if>',
                            {'isOne': 1, 'isTwo': 0, 'isThree': 1}
                            )
        self.assertEqual(result, 'one')

    def test_basic_if_else16(self):
        result = substitute('@',
                            '<@if isOne>one<@elif isTwo>two<@elif isThree>three<@else>none<@/if>',
                            {'isOne': 1, 'isTwo': 1, 'isThree': 0}
                            )
        self.assertEqual(result, 'one')
        result = substitute('@',
                            '<@if isOne >one<@elif\tisTwo\n>two<@elif isThree\n>three<@else>none<@/if>',
                            {'isOne': 1, 'isTwo': 1, 'isThree': 0}
                            )
        self.assertEqual(result, 'one')

    def test_basic_if_else17(self):
        result = substitute('@',
                            '<@if isOne>one<@elif isTwo>two<@elif isThree>three<@else>none<@/if>',
                            {'isOne': 1, 'isTwo': 1, 'isThree': 1}
                            )
        self.assertEqual(result, 'one')
        result = substitute('@',
                            '<@if isOne >one<@elif\tisTwo\n>two<@elif isThree\n>three<@else>none<@/if>',
                            {'isOne': 1, 'isTwo': 1, 'isThree': 1}
                            )
        self.assertEqual(result, 'one')

    ## The next eight test all combinations of truth of three values
    def test_basic_if_else18(self):
        result = substitute('@',
                            '<@if !isOne>one<@elif !isTwo>two<@elif !isThree>three<@else>none<@/if>',
                            {'isOne': 0, 'isTwo': 0, 'isThree': 0}
                            )
        self.assertEqual(result, 'one')
        result = substitute('@',
                            '<@if !isOne >one<@elif ! isTwo\t>two<@elif !\tisThree\n>three<@else>none<@/if>',
                            {'isOne': 0, 'isTwo': 0, 'isThree': 0}
                            )
        self.assertEqual(result, 'one')

    def test_basic_if_else19(self):
        result = substitute('@',
                            '<@if !isOne>one<@elif !isTwo>two<@elif !isThree>three<@else>none<@/if>',
                            {'isOne': 0, 'isTwo': 0, 'isThree': 1}
                            )
        self.assertEqual(result, 'one')
        result = substitute('@',
                            '<@if !isOne >one<@elif ! isTwo\t>two<@elif !\tisThree\n>three<@else>none<@/if>',
                            {'isOne': 0, 'isTwo': 0, 'isThree': 1}
                            )
        self.assertEqual(result, 'one')

    def test_basic_if_else20(self):
        result = substitute('@',
                            '<@if !isOne>one<@elif !isTwo>two<@elif !isThree>three<@else>none<@/if>',
                            {'isOne': 0, 'isTwo': 1, 'isThree': 0}
                            )
        self.assertEqual(result, 'one')
        result = substitute('@',
                            '<@if !isOne >one<@elif ! isTwo\t>two<@elif !\tisThree\n>three<@else>none<@/if>',
                            {'isOne': 0, 'isTwo': 1, 'isThree': 0}
                            )
        self.assertEqual(result, 'one')

    def test_basic_if_else21(self):
        result = substitute('@',
                            '<@if !isOne>one<@elif !isTwo>two<@elif !isThree>three<@else>none<@/if>',
                            {'isOne': 0, 'isTwo': 1, 'isThree': 1}
                            )
        self.assertEqual(result, 'one')
        result = substitute('@',
                            '<@if !isOne >one<@elif ! isTwo\t>two<@elif !\tisThree\n>three<@else>none<@/if>',
                            {'isOne': 0, 'isTwo': 1, 'isThree': 1}
                            )
        self.assertEqual(result, 'one')

    def test_basic_if_else22(self):
        result = substitute('@',
                            '<@if !isOne>one<@elif !isTwo>two<@elif !isThree>three<@else>none<@/if>',
                            {'isOne': 1, 'isTwo': 0, 'isThree': 0}
                            )
        self.assertEqual(result, 'two')
        result = substitute('@',
                            '<@if !isOne >one<@elif ! isTwo\t>two<@elif !\tisThree\n>three<@else>none<@/if>',
                            {'isOne': 1, 'isTwo': 0, 'isThree': 0}
                            )
        self.assertEqual(result, 'two')

    def test_basic_if_else23(self):
        result = substitute('@',
                            '<@if !isOne>one<@elif !isTwo>two<@elif !isThree>three<@else>none<@/if>',
                            {'isOne': 1, 'isTwo': 0, 'isThree': 1}
                            )
        self.assertEqual(result, 'two')
        result = substitute('@',
                            '<@if !isOne >one<@elif ! isTwo\t>two<@elif !\tisThree\n>three<@else>none<@/if>',
                            {'isOne': 1, 'isTwo': 0, 'isThree': 1}
                            )
        self.assertEqual(result, 'two')

    def test_basic_if_else24(self):
        result = substitute('@',
                            '<@if !isOne>one<@elif !isTwo>two<@elif !isThree>three<@else>none<@/if>',
                            {'isOne': 1, 'isTwo': 1, 'isThree': 0}
                            )
        self.assertEqual(result, 'three')
        result = substitute('@',
                            '<@if !isOne >one<@elif ! isTwo\t>two<@elif !\tisThree\n>three<@else>none<@/if>',
                            {'isOne': 1, 'isTwo': 1, 'isThree': 0}
                            )
        self.assertEqual(result, 'three')

    def test_basic_if_else25(self):
        result = substitute('@',
                            '<@if !isOne>one<@elif !isTwo>two<@elif !isThree>three<@else>none<@/if>',
                            {'isOne': 1, 'isTwo': 1, 'isThree': 1}
                            )
        self.assertEqual(result, 'none')
        result = substitute('@',
                            '<@if !isOne >one<@elif ! isTwo\t>two<@elif !\tisThree\n>three<@else>none<@/if>',
                            {'isOne': 1, 'isTwo': 1, 'isThree': 1}
                            )
        self.assertEqual(result, 'none')

    ## A series of tests using the or function in the if tag
    def test_basic_if_else26(self):
        result = substitute('@',
                            '<@if isOne,isThree,isFive>odd<@elif isTwo,isFour,isSix>even<@/if>',
                            {'isOne': 1, }
                            )
        self.assertEqual(result, 'odd')
        result = substitute('@',
                            '<@if isOne ,\tisThree,\nisFive >odd<@elif\tisTwo ,\tisFour\n, isSix >even<@/if>',
                            {'isOne': 1, }
                            )
        self.assertEqual(result, 'odd')

    def test_basic_if_else27(self):
        result = substitute('@',
                            '<@if isOne,isThree,isFive>odd<@elif isTwo,isFour,isSix>even<@/if>',
                            {'isThree': 1, }
                            )
        self.assertEqual(result, 'odd')
        result = substitute('@',
                            '<@if isOne ,\tisThree,\nisFive >odd<@elif\tisTwo ,\tisFour\n, isSix >even<@/if>',
                            {'isThree': 1, }
                            )
        self.assertEqual(result, 'odd')

    def test_basic_if_else28(self):
        result = substitute('@',
                            '<@if isOne,isThree,isFive>odd<@elif isTwo,isFour,isSix>even<@/if>',
                            {'isFive': 1, }
                            )
        self.assertEqual(result, 'odd')
        result = substitute('@',
                            '<@if isOne ,\tisThree,\nisFive >odd<@elif\tisTwo ,\tisFour\n, isSix >even<@/if>',
                            {'isFive': 1, }
                            )
        self.assertEqual(result, 'odd')

    def test_basic_if_else29(self):
        result = substitute('@',
                            '<@if isOne,isThree,isFive>odd<@elif isTwo,isFour,isSix>even<@/if>',
                            {'isTwo': 1, }
                            )
        self.assertEqual(result, 'even')
        result = substitute('@',
                            '<@if isOne ,\tisThree,\nisFive >odd<@elif\tisTwo ,\tisFour\n, isSix >even<@/if>',
                            {'isTwo': 1, }
                            )
        self.assertEqual(result, 'even')

    def test_basic_if_else30(self):
        result = substitute('@',
                            '<@if isOne,isThree,isFive>odd<@elif isTwo,isFour,isSix>even<@/if>',
                            {'isFour': 1, }
                            )
        self.assertEqual(result, 'even')
        result = substitute('@',
                            '<@if isOne ,\tisThree,\nisFive >odd<@elif\tisTwo ,\tisFour\n, isSix >even<@/if>',
                            {'isFour': 1, }
                            )
        self.assertEqual(result, 'even')

    def test_basic_if_else31(self):
        result = substitute('@',
                            '<@if isOne,isThree,isFive>odd<@elif isTwo,isFour,isSix>even<@/if>',
                            {'isSix': 1, }
                            )
        self.assertEqual(result, 'even')
        result = substitute('@',
                            '<@if isOne ,\tisThree,\nisFive >odd<@elif\tisTwo ,\tisFour\n, isSix >even<@/if>',
                            {'isSix': 1, }
                            )
        self.assertEqual(result, 'even')

    def test_basic_if_else32(self):
        # This one caused an error in V1.19 and earlier. Some of the elif tags
        #   that tested true would display, even though an earlier if was already
        #   true
        html = "<@if !isLast>solid-nobottom<@elif !isConsentAsked>solid<@elif isConsentYes>solid-nobottom<@else>solid<@/if>"
        d = dict = {'isConsentAsked': 1, 'isConsentYes': 1}
        result = substitute('@', html, d)
        self.assertEqual(result, 'solid-nobottom')

    def test_basic_if_else33(self):
        # Need to ask with regular html tags in both sides of an if/else
        #   to ensure some areas of the code are covered...
        result = substitute('@', '<@if isTrue><html1><@else><html2><@/if>', {'isTrue': 0}, doStrictKeyLookup=True)
        self.assertEqual(result, '<html2>')


class tagsub_if_case_equivalence_tests(tagsub_TestCase):
    def setUp(self):
        self.case_template1 = '<@case isTrue><@option 1>true<@else>false<@/case>'
        self.if_template1 = '<@if isTrue>true<@else>false<@/if>'

        self.case_template2 = '<@case isTrue><@option 0>true<@else>false<@/case>'
        self.if_template2 = '<@if ! isTrue>true<@else>false<@/if>'

    def test_if_case_1a(self):
        # Verify eqivalence with case constructs and is0False option
        d = {'isTrue': '0'}
        self.assertEqual(
            substitute('@', self.if_template1, d, is0False=True),
            substitute('@', self.case_template1, d, is0False=True)
        )

    def test_if_case_1b(self):
        # Verify eqivalence with case constructs and is0False option
        d = {'isTrue': '1'}
        self.assertEqual(
            substitute('@', self.if_template1, d, is0False=True),
            substitute('@', self.case_template1, d, is0False=True)
        )

    def test_if_case_1c(self):
        ## Verify eqivalence with case constructs and is0False option
        d = {'isTrue': 0}
        self.assertEqual(
            substitute('@', self.if_template1, d, is0False=True),
            substitute('@', self.case_template1, d, is0False=True)
        )

    def test_if_case_1d(self):
        ## Verify eqivalence with case constructs and is0False option
        d = {'isTrue': 1}
        self.assertEqual(
            substitute('@', self.if_template1, d, is0False=True),
            substitute('@', self.case_template1, d, is0False=True)
        )

    def test_if_case_2a(self):
        ## Verify eqivalence with case constructs and is0False option
        d = {'isTrue': '0'}
        self.assertEqual(
            substitute('@', self.if_template2, d, is0False=True),
            substitute('@', self.case_template2, d, is0False=True)
        )

    def test_if_case_2b(self):
        ## Verify eqivalence with case constructs and is0False option
        d = {'isTrue': '1'}
        self.assertEqual(
            substitute('@', self.if_template2, d, is0False=True),
            substitute('@', self.case_template2, d, is0False=True)
        )

    def test_if_case_2c(self):
        ## Verify eqivalence with case constructs and is0False option
        d = {'isTrue': 0}
        self.assertEqual(
            substitute('@', self.if_template2, d, is0False=True),
            substitute('@', self.case_template2, d, is0False=True)
        )

    def test_if_case_2d(self):
        ## Verify eqivalence with case constructs and is0False option
        d = {'isTrue': 1}
        self.assertEqual(
            substitute('@', self.if_template2, d, is0False=True),
            substitute('@', self.case_template2, d, is0False=True)
        )


class tagsub_case_tests(tagsub_TestCase):
    def test_basic_case1(self):
        result = substitute('@',
                            '<@case test>ignored text<@option 1>one<@option 2>two<@option 3>three<@else>none<@/case>',
                            {'test': 1}
                            )
        self.assertEqual('one', result)
        result = substitute('@',
                            '<@case test >ignored text<@option   1 >one<@option 2 >two<@option\t3\n>three<@else>none<@/case>',
                            {'test': 1}
                            )
        self.assertEqual('one', result)

    def test_basic_case2(self):
        result = substitute('@',
                            '<@case test>ignored text<@option 1>one<@option 2>two<@option 3>three<@else>none<@/case>',
                            {'test': 2}
                            )
        self.assertEqual('two', result)

    def test_basic_case3(self):
        result = substitute('@',
                            '<@case test>ignored text<@option 1>one<@option 2>two<@option 3>three<@else>none<@/case>',
                            {'test': 3}
                            )
        self.assertEqual('three', result)
        result = substitute('@',
                            '<@case test>ignored text<@option 1>one<@option 2>two<@option 3>three<@else>none<@/case>',
                            {'test': '3'}
                            )
        self.assertEqual('three', result)

    def test_basic_case4(self):
        result = substitute('@',
                            '<@case test>ignored text<@option 1>one<@option 2>two<@option 3>three<@else>none<@/case>',
                            {'test': '4'}
                            )
        self.assertEqual('none', result)
        # If we use the numeric value 4, we were getting a reference count mismatch.
        # If we use some other value (see test_basic_case5 and test_basic_case7),
        #   we do not. I must assume that this is some odd issue with Python itself,
        #   that I can do nothing about and is hopefully not a memory leak.
        # Actually, in retrospect, with 4 being a common referenced value, I am assuming
        #   that somewhere else in Python someone else got a reference to 4 between invocations.
        # XXX VERION NOTE: The above prob was in Python 2.4. With Python 2.7, we
        #   do not get e ref count mismatch on 4, but if we use 5, we do get a
        #   mismatch. Changed back to 4 for case5 and case7
        result = substitute('@',
                            '<@case test>ignored text<@option 1>one<@option 2>two<@option 3>three<@else>none<@/case>',
                            {'test': 999}
                            )
        self.assertEqual('none', result)

    def test_basic_case5(self):
        # Save as test_basic_case4, but without an else clause
        result = substitute('@',
                            '<@case test>ignored text<@option 1>one<@option 2>two<@option 3>three<@/case>',
                            {'test': '4'}
                            )
        self.assertEqual('', result)
        ## See note above in test_basic_case4 regarding using the numeric
        ##   value 4 in the dict.
        result = substitute('@',
                            '<@case test>ignored text<@option 1>one<@option 2>two<@option 3>three<@/case>',
                            {'test': 4}
                            )
        self.assertEqual('', result)

    def test_basic_case6(self):
        result = substitute('@',
                            '<@case test>ignored text<@option 1>one<@option 2>two<@option 3>three<@else>none<@/case>',
                            {}
                            )
        self.assertEqual('none', result)

    def test_basic_case7(self):
        # test with case in scan mode
        result = substitute('@',
                            '<@if true><@case test>ignored text<@option 1>one<@option 2>two<@option 3>three<@/case><@else>false<@/if>',
                            {'test': '4'}
                            )
        self.assertEqual('false', result)
        ## See note above in test_basic_case4 regarding using the numeric
        ##   value 4 in the dict.
        result = substitute('@',
                            '<@if true><@case test>ignored text<@option 1>one<@option 2>two<@option 3>three<@/case><@else>false<@/if>',
                            {'test': 4}
                            )
        self.assertEqual('false', result)

    def test_nooption_case_tag(self):
        # This may not be an error, but it won't result in anything interesting
        result = substitute('@', '<@case test><@else>1<@/case>', {})
        self.assertEqual('1', result)

    # tests for quoted strings in an option tag for the match value
    #      to eliminate whitespace sensitivity.
    # without quotes, an option must be a valid key
    def test_quoted_option1(self):
        result = substitute('@',
                            '<@case\ttest > <@option   "option 1" >option one<@else>no options<@/case>',
                            {'test': 'option 1'})
        self.assertEqual('option one', result)

    def test_quoted_option1a(self):
        # Doubled double quote escapes it in option tag
        result = substitute('@',
                            '<@case\ttest > <@option   "option ""1""" >option one<@else>no options<@/case>',
                            {'test': 'option "1"'})
        self.assertEqual('option one', result)

    def test_quoted_option2(self):
        result = substitute('@',
                            '<@case\ttest > <@option   "option\n 1" >option one<@else>no options<@/case>',
                            {'test': 'option\n 1'})
        self.assertEqual('option one', result)

    def test_quoted_option_errors1(self):
        ## Same as test_quoted_option2, but without quotes on option value
        self.assertRaisesAndMatchesTraceback(InvalidTagKeyName,
                                             '15(1,15)',
                                             substitute, '@',
                                             '<@case\ttest > <@option   option\n 1 >option one<@else>no options<@/case>',
                                             {'test': 'option\n 1'})

    def test_quoted_option_errors2(self):
        ## Same as test_quoted_option2, but without quotes on option value
        self.assertRaisesAndMatchesTraceback(InvalidTagKeyName,
                                             '15(1,15)',
                                             substitute, '@',
                                             '<@case\ttest > <@option   x"option\n 1" >option one<@else>no options<@/case>',
                                             {'test': 'option\n 1'})

    def test_quoted_option_errors3(self):
        ## Same as test_quoted_option2, but without quotes on option value
        self.assertRaisesAndMatchesTraceback(InvalidTagKeyName,
                                             '15(1,15)',
                                             substitute, '@',
                                             '<@case\ttest > <@option   "option\n 1"x >option one<@else>no options<@/case>',
                                             {'test': 'option\n 1'})

    def test_quoted_option_errors4(self):
        self.assertRaisesAndMatchesTraceback(TagsubTemplateSyntaxError,
                                             '14(1,14)',
                                             substitute, '@',
                                             '<@case test> <@option   "',
                                             {'test': 'option 1'})

    def test_quoted_option_errors5(self):
        self.assertRaisesAndMatchesTraceback(TagsubTemplateSyntaxError,
                                             '14(1,14)',
                                             substitute, '@',
                                             '<@case test> <@option   "option 1',
                                             {'test': 'option 1'})

    def test_quoted_option_errors6(self):
        self.assertRaisesAndMatchesTraceback(TagsubTemplateSyntaxError,
                                             '14(1,14)',
                                             substitute, '@',
                                             '<@case test> <@option   "option 1"',
                                             {'test': 'option 1'})

    def test_variable_option1(self):
        # This one must match. It uses the same variable in the case and the option
        result = substitute('@', '<@case test><@option  =test>True<@/case>',
                            {'test': 'arbitrary value'})
        self.assertEqual('True', result)

    def test_variable_option2(self):
        result = substitute('@', '<@case test><@option  =value>match<@else>no match<@/case>',
                            {'test': 'value'})
        self.assertEqual('no match', result)

    def test_variable_option3(self):
        result = substitute('@', '<@case test><@option  =value>match<@else>no match<@/case>',
                            {'test': 'value', 'value': 'value'})
        self.assertEqual('match', result)

    def test_variable_option4(self):
        result = substitute('@',
                            '<@saveeval value><@test><@/saveeval><@case test><@option  =value>match<@else>no match<@/case>',
                            {'test': 'value', 'value': 'non-matching value'})
        self.assertEqual('match', result)

    def test_variable_option5(self):
        # This now behaves slightly differently from the old C code. Now, value gets evaluated when referenced. In
        # the old C code it only got evaluated recursively when being substituted into the output.
        result = substitute('@',
                            '<@saveraw value><@test><@/saveraw><@case test><@option  =value>match<@else>no match<@/case>',
                            {'test': 'value', 'value': 'non-matching value'})
        self.assertEqual('match', result)

    def test_variable_option6(self):
        # We should properly recognize implied loop variables
        result = substitute('@',
                            '<@loop list><@case value><@option =:index><@:rindex>match<@/case><@/loop>',
                            {'value': '3', 'list': [{}, {}, {}, {}]})
        self.assertEqual('2match', result)

    def test_variable_option7(self):
        # We should properly recognize implied loop variables
        result = substitute('@',
                            '<@loop list><@case value><@option =:index><@:rindex>match<@/case><@/loop>',
                            {'value': 2, 'list': [{}, {}, {}, {}]})
        self.assertEqual('3match', result)

    def test_variable_option8(self):
        result = substitute('@',
                            '<@case test><@option ="variable with spaces">match<@else>no match<@/case>',
                            {'test': 'value', 'variable with spaces': 'value'})
        self.assertEqual('match', result)

    def test_variable_option9(self):
        result = substitute('@',
                            '<@case test><@option =var>match<@else>no match<@/case>',
                            {'test': None, 'var': None})
        self.assertEqual('match', result)

    def test_variable_option9a(self):
        result = substitute('@',
                            '<@case test><@option =var>match<@else>no match<@/case>',
                            {'test': None, })
        self.assertEqual('match', result)

    def test_variable_option9b(self):
        result = substitute('@',
                            '<@case test><@option =var>match<@else>no match<@/case>',
                            {'test': None, 'var': ''})
        self.assertEqual('match', result)

    def test_variable_option10(self):
        result = substitute('@',
                            '<@case test><@option =var>match<@else>no match<@/case>',
                            {})
        self.assertEqual('match', result)

    def test_variable_option10a(self):
        result = substitute('@',
                            '<@case test><@option =var>match<@else>no match<@/case>',
                            {'var': None})
        self.assertEqual('match', result)

    def test_variable_option10b(self):
        result = substitute('@',
                            '<@case test><@option =var>match<@else>no match<@/case>',
                            {'var': ''})
        self.assertEqual('match', result)

    def test_variable_option11(self):
        result = substitute('@',
                            '<@case test><@option =var>match<@else>no match<@/case>',
                            {'test': '', 'var': None})
        self.assertEqual('match', result)

    def test_variable_option11a(self):
        result = substitute('@',
                            '<@case test><@option =var>match<@else>no match<@/case>',
                            {'test': '', })
        self.assertEqual('match', result)

    def test_variable_option11b(self):
        result = substitute('@',
                            '<@case test><@option =var>match<@else>no match<@/case>',
                            {'test': '', 'var': ''})
        self.assertEqual('match', result)

    def test_variable_option12(self):
        # It is probably good to test attribute variable options like we do here,
        #   but this example helped illustrate a problem in 1.63. We were not
        #   resetting the isVariableOption flag, so all subsequent options were
        #   being looked up as variable options. The problem was resolved after
        #   version 1.63.
        class c(object): pass

        i = c()
        i.attr1 = 'bob'
        i.attr2 = 'fred'
        result = tagsub.substitute('@',
                                   '<@case name><@option =i.attr1>attr1<@option =i.attr2>attr2<@/case> <@case case_val><@option val1>val1<@option val2>val2<@option val3>val3<@option val4>val4<@else>none<@/case>',
                                   {'i': i, 'case_val': 'val3', 'name': 'fred'})
        self.assertEqual('attr2 val3', result)

    def test_variable_option13(self):
        result = tagsub.substitute(
            '@',
            '<@case test><@option =varname,val>True<@/case>',
            {'test': 'val', 'varname': 'otherval'}
        )
        self.assertEqual('True', result)

    def test_variable_option_error1(self):
        self.assertRaisesAndMatchesTraceback(InvalidTagKeyName,
                                             '13(1,13)',
                                             substitute, '@',
                                             '<@case test><@option x=value>match<@else>no match<@/case>',
                                             {'test': 'value', 'value': 'value'})

    def test_variable_option_error2(self):
        self.assertRaisesAndMatchesTraceback(InvalidTagKeyName,
                                             '13(1,13)',
                                             substitute, '@',
                                             '<@case test><@option =value"x">match<@else>no match<@/case>',
                                             {'test': 'value', 'value': 'value'})

    def test_variable_option_error3(self):
        self.assertRaisesAndMatchesTraceback(InvalidTagKeyName,
                                             '13(1,13)',
                                             substitute, '@',
                                             '<@case test><@option =value "x">match<@else>no match<@/case>',
                                             {'test': 'value', 'value': 'value'})

    def test_composite_option1(self):
        result = substitute('@',
                            '<@case value><@option T,F>checked<@else>unchecked<@/case>',
                            {})
        self.assertEqual('unchecked', result)

    def test_composite_option1a(self):
        result = substitute('@',
                            '<@case value><@option T,F>checked<@else>unchecked<@/case>',
                            {'value': ''})
        self.assertEqual('unchecked', result)

    def test_composite_option1b(self):
        result = substitute('@',
                            '<@case value><@option T,F>checked<@else>unchecked<@/case>',
                            {'value': None})
        self.assertEqual('unchecked', result)

    def test_composite_option1c(self):
        result = substitute('@',
                            '<@case value><@option T,F>checked<@else>unchecked<@/case>',
                            {'value': 'T'})
        self.assertEqual('checked', result)

    def test_composite_option1d(self):
        result = substitute('@',
                            '<@case value><@option T,F>checked<@else>unchecked<@/case>',
                            {'value': 'F'})
        self.assertEqual('checked', result)

    def test_composite_option2(self):
        result = substitute('@',
                            '<@case letter><@option a,e,i,o,u>vowel<@else>consonant<@/case>',
                            {'letter': 'a'})
        self.assertEqual('vowel', result)

    def test_composite_option2a(self):
        result = substitute('@',
                            '<@case letter><@option a,e,i,o,u>vowel<@else>consonant<@/case>',
                            {'letter': 'b'})
        self.assertEqual('consonant', result)

    def test_composite_option2b(self):
        result = substitute('@',
                            '<@case letter><@option a,e,i,o,u>vowel<@else>consonant<@/case>',
                            {'letter': 'e'})
        self.assertEqual('vowel', result)

    def test_composite_option2c(self):
        result = substitute('@',
                            '<@case letter><@option a,e,i,o,u>vowel<@else>consonant<@/case>',
                            {'letter': 'i'})
        self.assertEqual('vowel', result)

    def test_composite_option2d(self):
        result = substitute('@',
                            '<@case letter><@option a,e,i,o,u>vowel<@else>consonant<@/case>',
                            {'letter': 'o'})
        self.assertEqual('vowel', result)

    def test_composite_option2e(self):
        result = substitute('@',
                            '<@case letter><@option a,e,i,o,u>vowel<@else>consonant<@/case>',
                            {'letter': 'u'})
        self.assertEqual('vowel', result)

    def test_composite_option3(self):
        result = substitute('@',
                            '<@case letter><@option a,e,i,=l,o,u>match<@else>no match<@/case>',
                            {'letter': 'i', 'l': 'q'})
        self.assertEqual('match', result)

    def test_composite_option3a(self):
        result = substitute('@',
                            '<@case letter><@option a,e,i,=l,o,u>match<@else>no match<@/case>',
                            {'letter': 'p', 'l': 'q'})
        self.assertEqual('no match', result)

    def test_composite_option3b(self):
        result = substitute('@',
                            '<@case letter><@option a,e,i,=l,o,u>match<@else>no match<@/case>',
                            {'letter': 'q', 'l': 'q'})
        self.assertEqual('match', result)

    def test_composite_option3c(self):
        result = substitute('@',
                            '<@case letter><@option a,"",i,=l,o,u>match<@else>no match<@/case>',
                            {'letter': None, 'l': 'q'})
        self.assertEqual('match', result)

    def test_composite_option4(self):
        result = substitute('@',
                            '<@case test><@option 1,2,3>match<@else>no match<@/case>',
                            {'test': 2})
        self.assertEqual('match', result)

    def test_composite_option5(self):
        result = substitute('@',
                            '<@case test><@option "1","2","3">match<@else>no match<@/case>',
                            {'test': 2})
        self.assertEqual('match', result)

    def test_composite_option6(self):
        result = substitute('@',
                            '<@case test><@option =1,="2",=3>match<@else>no match<@/case>',
                            {'test': 'value', '1': 'v1', '2': 'value'})
        self.assertEqual('match', result)

    def test_composite_option6a(self):
        self.assertRaisesAndMatchesTraceback(KeyError, '13(1,13)',
                                             substitute, '@',
                                             '<@case test><@option =1,="2",=3>match<@else>no match<@/case>',
                                             {'test': 'value', '1': 'v1', '2': 'value'}, doStrictKeyLookup=True)


class tagsub_if_tag_children(tagsub_TestCase):
    def test_multiple_else_tags(self):
        self.assertRaisesAndMatchesTraceback(
            TagsubTemplateSyntaxError,
            '30(1,30)',
            substitute, '@',
            "<@if test>Test<@else>testElse<@else>Bad Else<@/if>",
            {"test":True}
        )

    def test_elif_after_else_tags(self):
        self.assertRaisesAndMatchesTraceback(
            TagsubTemplateSyntaxError,
            '30(1,30)',
            substitute, '@',
            "<@if test>Test<@else>testElse<@elif test2>Bad Else<@/if>",
            {"test":True}
        )


class tagsub_case_tag_children(tagsub_TestCase):
    def test_multiple_else_tags(self):
        self.assertRaisesAndMatchesTraceback(
            TagsubTemplateSyntaxError,
            '32(1,32)',
            substitute, '@',
            "<@case test>Test<@else>testElse<@else>Bad Else<@/case>",
            {"test":True}
        )

    def test_option_after_else_tags(self):
        self.assertRaisesAndMatchesTraceback(
            TagsubTemplateSyntaxError,
            '32(1,32)',
            substitute, '@',
            "<@case test>Test<@else>testElse<@option test2>Bad Else<@/case>",
            {"test":True}
        )

    def test_other_tag_after_else_tags(self):
        self.assertRaisesAndMatchesTraceback(
            TagsubTemplateSyntaxError,
            '13(1,13)',
            substitute, '@',
            "<@case test><@test>Test<@else>testElse<@ test2>Bad Else<@/case>",
            {"test":True}
        )


class tagsub_blank_line_suppression(tagsub_TestCase):
    def test_blank_line_suppression1(self):
        result = substitute('@', ' \t', {})
        self.assertEqual(' \t', result)

    def test_blank_line_suppression2(self):
        result = substitute('@', ' \t\n', {})
        self.assertEqual(' \t\n', result)

    def test_blank_line_suppression3(self):
        result = substitute('@', ' <@test>\t', {})
        self.assertEqual(' \t', result)

    def test_blank_line_suppression4(self):
        result = substitute('@', ' <@test>\t\n', {})
        self.assertEqual('', result)

    def test_blank_line_suppression5(self):
        template = """line 1
<@loop test>
  <@data>
<@/loop>
trailing line"""
        assumed_result = """line 1
  loop 1
  loop 2
  loop 3
trailing line"""
        result = substitute('@', template, {'test': [{'data': 'loop 1'}, {'data': 'loop 2'}, {'data': 'loop 3'}]})
        self.assertEqual(assumed_result, result)

    def test_blank_line_suppression6(self):
        # Also suppress substitution tag lines that have no non-whitespace
        template = """line 1
<@loop test>
  <@data>
  <@empty_tag>
<@/loop>
trailing line"""
        assumed_result = """line 1
  loop 1
  loop 2
  loop 3
trailing line"""
        result = substitute('@', template, {'test': [{'data': 'loop 1'}, {'data': 'loop 2'}, {'data': 'loop 3'}]})
        self.assertEqual(assumed_result, result)

    def test_blank_line_suppression7(self):
        # Suppress the loop tag lines and the supporting if tag family
        template = """line 1
<@loop test>
  <@data>
  <@if empty_tag>
    empty tag text
  <@else>
    no text
  <@/if>
<@/loop>
trailing line"""
        assumed_result = """line 1
  loop 1
    no text
  loop 2
    no text
  loop 3
    no text
trailing line"""
        result = substitute('@', template, {'test': [{'data': 'loop 1'}, {'data': 'loop 2'}, {'data': 'loop 3'}]})
        self.assertEqual(assumed_result, result)

    def test_blank_line_suppression8(self):
        # Don't suppress lines that have non-whitespace characters
        template = """line 1
<@loop test>
  <@data>
  on if line<@if empty_tag>
    empty tag text
  <@else>
    no text
  <@/if>
<@/loop>
trailing line"""
        assumed_result = """line 1
  loop 1
  on if line
    no text
  loop 2
  on if line
    no text
  loop 3
  on if line
    no text
trailing line"""
        result = substitute('@', template, {'test': [{'data': 'loop 1'}, {'data': 'loop 2'}, {'data': 'loop 3'}]})
        self.assertEqual(assumed_result, result)

    def test_blank_line_suppression9(self):
        # Don't suppress lines that have no tags
        template = """line 1
<@loop test>
  <@data>

  <@if empty_tag>
    empty tag text
  <@else>
    no text
  <@/if>
<@/loop>
trailing line"""
        assumed_result = """line 1
  loop 1

    no text
  loop 2

    no text
  loop 3

    no text
trailing line"""
        result = substitute('@', template, {'test': [{'data': 'loop 1'}, {'data': 'loop 2'}, {'data': 'loop 3'}]})
        self.assertEqual(assumed_result, result)

    def test_blank_line_suppression10(self):
        # We had an issue where the line count was not being incremented
        #   when a suppressed comment was immediately followed by a
        #   newline. This tests for that case.
        t = "<@ test>\n<@x"
        self.assertRaisesAndMatchesTraceback(
            TagsubTemplateSyntaxError,
            '10(2,1)',
            substitute, '@', t, {})

    # Tests on if/elif line suppression.....
    def test_blank_line_suppression_if1(self):
        result = substitute('@',
                            '<@if test>\ntest is true\n<@else>\ntest is false\n<@/if>\n',
                            {'test': 1})
        self.assertEqual('test is true\n', result)

    def test_blank_line_suppression_if2(self):
        result = substitute('@',
                            '<@if test>\ntest is true\n<@else>\ntest is false\n<@/if>\n',
                            {'test': 0})
        self.assertEqual('test is false\n', result)

    # Also for case/option line suppression
    def test_blank_line_suppression_case1(self):
        result = substitute('@',
                            '<@case test>\n<@option 1>\none\n<@option 2>\ntwo<@else>\nnone\n<@/case>',
                            {'test': 2})
        self.assertEqual('two', result)

    def test_blank_line_suppression_saveeval1(self):
        ## Borrow the inner evaluated text from test_blank_line_suppression7
        inner_template = """line 1
<@loop test>
  <@data>
  <@if empty_tag>
    empty tag text
  <@else>
    no text
  <@/if>
<@/loop>
trailing line"""
        inner_assumed_result = """line 1
  loop 1
    no text
  loop 2
    no text
  loop 3
    no text
trailing line"""
        template = '\n <@saveeval inner_result>' + inner_template + '<@/saveeval>\n'
        d = {'test': [{'data': 'loop 1'}, {'data': 'loop 2'}, {'data': 'loop 3'}]}
        result = substitute('@', template, d)
        self.assertEqual('\n', result)

        # We are eliminating the ability for the template to write back into the code (e.g. update the dict).
        #self.assertEqual(d['inner_result'], inner_assumed_result)


class test_saveraw(tagsub_TestCase):
    # On saveraw tests, do not use reference counting variation on substitute
    #  because our dictionary is being modified and will show up as an error.
    # tests reusing saved data, updates to dict, and blank line suppression w/ saveraw tags
    def test_saveraw1(self):
        d = {'u': 'water'}
        t = 'text <@v>\n<@v>\n<@saveraw v>repeat <@u><@/saveraw>  \n <@v> <@ v>\n'
        result = tagsub.substitute('@', t, d)
        self.assertEqual(result, 'text \n repeat water repeat water\n')

        # We are eliminating the ability for the template to write back into the code (e.g. update the dict).
        #self.assertEqual(d, {'v': 'repeat <@u>', 'u': 'water'})

        result = tagsub.substitute('@', t, d)
        self.assertEqual(result, 'text repeat water\nrepeat water\n repeat water repeat water\n')

        d['v'] = 'test'
        result = tagsub.substitute('@', t, d)
        self.assertEqual(result, 'text test\ntest\n repeat water repeat water\n')

    # More tests of multiple assignment
    def test_saveraw2(self):
        t = """
<@loop list>
<@if isEven>
even
    <@saveraw isEven><@/saveraw>
<@else>
odd
    <@saveraw isEven>true<@/saveraw>
<@/if>
<@/loop>"""
        result = tagsub.substitute('@', t, {'list': [{}, {}, {}, {}]})
        self.assertEqual(result, '\nodd\neven\nodd\neven\n')

    # Use saved text with a tag in a loop
    def test_saveraw3(self):
        d = {'list': [{'index': 1}, {'index': 2}, {'index': 3}]}
        result = tagsub.substitute('@#',
                                   '<@saveraw field><#index>,<@/saveraw><#loop list><@field><#/loop>', [{}, d])
        self.assertEqual(result, '1,2,3,')

    # FIXME The way we implement implied loop variables now, I am not sure I would expect, or want this to work
    # Same test with an implied loop variable
    #def test_saveraw4(self):
    #    d = {'list': [{}, {}, {}]}
    #    result = tagsub.substitute('@#',
    #                               '<@saveraw field><#:index>,<@/saveraw><#loop list><@field><#/loop>', [{}, d])
    #    self.assertEqual(result, '1,2,3,')

    # We are eliminating the ability for the template to write back into the code (e.g. update the dict).
    #def test_saveraw5(self):
    #    d = {}
    #    result = tagsub.substitute('@', '<@saveraw\tfield\n>text<@/saveraw>', d)
    #    self.assertEqual(d, {'field': 'text'})


class test_saveeval(tagsub_TestCase):
    # tests reusing saved data, updates to dict, and blank line suppression w/ saveeval tags
    def test_saveeval1(self):
        d = {'u': 'water'}
        t = 'text <@v>\n<@v>\n<@saveeval v>repeat <@u><@/saveeval>  \n <@v> <@ v>\n'
        result = tagsub.substitute('@', t, d)
        self.assertEqual('text \n repeat water repeat water\n', result)

        # We are eliminating the ability for the template to write back into the code (e.g. update the dict).
        #self.assertEqual(d, {'v': 'repeat water', 'u': 'water'})

        result = tagsub.substitute('@', t, d)
        self.assertEqual('text repeat water\nrepeat water\n repeat water repeat water\n', result)

        d['v'] = 'test'
        result = tagsub.substitute('@', t, d)
        self.assertEqual('text test\ntest\n repeat water repeat water\n', result)

    # More tests of multiple assignment
    def test_saveeval2(self):
        t = """
<@loop list>
<@if isEven>
even
    <@saveeval isEven><@/saveeval>
<@else>
odd
    <@saveeval isEven>true<@/saveeval>
<@/if>
<@/loop>"""
        result = tagsub.substitute('@', t, {'list': [{}, {}, {}, {}]})
        self.assertEqual('\nodd\neven\nodd\neven\n', result)

    # Use saved text with a tag in a loop
    def test_saveeval3(self):
        d = {'list': [{'index': 1}, {'index': 2}, {'index': 3}]}
        result = tagsub.substitute('@#',
                                   '<@saveeval field><#index>,<@/saveeval><#loop list><@field><#/loop>', [{}, d])
        self.assertEqual(',,,', result)

    # Same test with an implied loop variable
    def test_saveeval4(self):
        ## This call works with saveraw, but fails w/ InvalidTagKeyName
        ##   when used with saveeval.
        d = {'list': [{}, {}, {}]}
        self.assertRaisesAndMatchesTraceback(InvalidTagKeyName,
                                             '18(1,18)',
                                             tagsub.substitute, '@#',
                                             '<@saveeval field><#:index>,<@/saveeval><#loop list><@field><#/loop>',
                                             [{}, d])

    def test_saveeval5(self):
        d = {}
        result = tagsub.substitute('@', '<@saveeval\tfield\n>text<@/saveeval>', d)
        self.assertEqual(d, {'field': 'text'})

    def test_saveeval6(self):
        d = {'list': [{}, {}, {}, {}, {}]}
        result = tagsub.substitute('@', '<@loop list><@if :isLast><@saveeval field><@:index><@/saveeval><@/if><@/loop>',
                                   d)
        self.assertEqual(d['field'], '5')


class test_comment_removal(tagsub_TestCase):
    def test_comment_removal1(self):
        # Should not remove comments by default
        t = ' <!--    --> '
        result = substitute('@', t, {})
        self.assertEqual(t, result)

    def test_comment_removal2(self):
        t = ' <!--    --> '
        result = substitute('@', t, {}, doSuppressComments=True)
        self.assertEqual('  ', result)

    def test_comment_removal2a(self):
        # A suppressed comment must be able to end a string.
        t = ' <!--    -->'
        result = substitute('@', t, {}, doSuppressComments=True)
        self.assertEqual(' ', result)

    def test_comment_removal2b(self):
        # A suppressed comment must be able to begin a string.
        t = '<!--    --> '
        result = substitute('@', t, {}, doSuppressComments=True)
        self.assertEqual(' ', result)

    def test_comment_removal2c(self):
        # A suppressed comment must be able to begin and end a string.
        t = '<!--    -->'
        result = substitute('@', t, {}, doSuppressComments=True)
        self.assertEqual('', result)

    def test_comment_removal3(self):
        # Comments will be subject to blank line suppression like empty tags
        t = ' <!--    --> \nx'
        result = substitute('@', t, {}, doSuppressComments=True)
        self.assertEqual('x', result)

    def test_comment_removal4(self):
        # Comments will be subject to blank line suppression like empty tags
        t = ' <!-- <@debug>   --> \nx'
        result = substitute('@', t, {'debug': 'debug text'}, doSuppressComments=True)
        self.assertEqual('x', result)

    def test_comment_removal5(self):
        # Comments will be subject to blank line suppression like empty tags
        t = ' <!-- <@debug> --> \nx'
        result = substitute('@', t, {'debug': 'debug text'}, doSuppressComments=False)
        self.assertEqual(' <!-- debug text --> \nx', result)

    def test_comment_removal6(self):
        # Comments will be subject to blank line suppression like empty tags
        t = ' <!-- <@debug> --> \nxx'
        result = substitute('@', t, {'debug': 'debug text'})
        self.assertEqual(' <!-- debug text --> \nxx', result)

    def test_comment_removal7(self):
        t = ' <!-- <@loop list> --> \nx'
        self.assertRaisesAndMatchesTraceback(TagsubTemplateSyntaxError,
                                             '7(1,7)',
                                             substitute, '@', t, {}, doSuppressComments=True)

    def test_comment_removal8(self):
        t = ' <!-- <@loop list> --> \nx'
        self.assertRaisesAndMatchesTraceback(TagsubTemplateSyntaxError,
                                             '7(1,7)',
                                             substitute, '@', t, {}, doSuppressComments=False)

    def test_comment_removal9(self):
        # Comments will be subject to blank line suppression like empty tags
        t = ' <@!--> <@debug>   <@--> <!-- --> \nx'
        result = substitute('@', t, {'debug': 'debug text'}, doSuppressComments=True)
        self.assertEqual('x', result)

    def test_comment_removal10(self):
        # Comments will be subject to blank line suppression like empty tags
        t = ' <@!--> <@debug>   <@--> <!-- --> \nx'
        result = substitute('@', t, {'debug': 'debug text'}, doSuppressComments=False)
        self.assertEqual('  <!-- --> \nx', result)

    def test_comment_removal11(self):
        # Comments will be subject to blank line suppression like empty tags
        t = ' <@!--> <@--><!-- <@debug>  --> \nx'
        result = substitute('@', t, {'debug': 'debug text'}, doSuppressComments=False)
        self.assertEqual(' <!-- debug text  --> \nx', result)

    def test_comment_removal12(self):
        # Comments will be subject to blank line suppression like empty tags
        t = ' <^!--> <^--> <@!--> <@--> <!-- --> <$!--> <$-->\nx'
        result = substitute('@', t, {})
        self.assertEqual(' <^!--> <^-->  <!-- --> <$!--> <$-->\nx', result)

    def test_comment_removal13(self):
        # Comments will be subject to blank line suppression like empty tags
        t = '<@!--> <@-->'
        result = substitute('@', t, {})
        self.assertEqual('', result)

    def test_comment_removal14(self):
        # NOTE: Comments are nestable...
        t = ' <@!-->  <!-- --> <@--> '
        result = substitute('@', t, {})
        self.assertEqual('  ', result)

    def test_comment_removal15(self):
        # NOTE: Comments are nestable...
        t = '<!-- <@!--> <@--> --> '
        result = substitute('@', t, {})
        self.assertEqual('<!--  --> ', result)

    def test_comment_removal16(self):
        # NOTE: Comments are nestable...
        t = '<!-- <@!--> <@--> --> '
        result = substitute('@', t, {}, doSuppressComments=True)
        self.assertEqual(' ', result)

    def test_comment_removal17(self):
        # We had an issue where the line count was not being incremented
        #   when a suppressed comment was immediately followed by a
        #   newline. This tests for that case.
        t = "<!-- -->\n<@x"
        self.assertRaisesAndMatchesTraceback(
            TagsubTemplateSyntaxError,
            '10(2,1)',
            substitute, '@', t, {},
            doSuppressComments=True)

    def test_comment_parsing1(self):
        t = "<!- - -->"
        result = substitute('@', t, {})
        self.assertEqual(t, result)

    def test_comment_parsing2(self):
        t = "<!-- - -> -->"
        result = substitute('@', t, {})
        self.assertEqual(t, result)

    def test_comment_parsing3(self):
        t = "<!-- -- > -->"
        result = substitute('@', t, {})
        self.assertEqual(t, result)

    def test_comment_parsing4(self):
        t = "<@!- -> <@-->"
        self.assertRaisesAndMatchesTraceback(
            TagsubTemplateSyntaxError,
            '1(1,1)',
            substitute, '@', t, {})

    def test_comment_parsing5(self):
        t = "<@!--> <^-->"
        self.assertRaisesAndMatchesTraceback(
            TagsubTemplateSyntaxError,
            '8(1,8)',
            substitute, '@^', t, [{},{}])

    def test_comment_parsing6(self):
        t = "<@!--> <@->"
        self.assertRaisesAndMatchesTraceback(
            TagsubTemplateSyntaxError,
            '8(1,8)',
            substitute, '@^', t, [{},{}])

    def test_comment_parsing7(self):
        t = "<@!--  > <@--  >"
        self.assertRaisesAndMatchesTraceback(
            TagsubTemplateSyntaxError,
            '8(1,8)',
            substitute, '@^', t, [{}, {}])

    def test_comment_parsing8(self):
        t = "<@!--> <@-"
        self.assertRaisesAndMatchesTraceback(
            TagsubTemplateSyntaxError,
            '8(1,8)',
            substitute, '@^', t, [{}, {}])

    def test_comment_parsing9(self):
        t = "<@!--> <@---"
        self.assertRaisesAndMatchesTraceback(
            TagsubTemplateSyntaxError,
            '8(1,8)',
            substitute, '@^', t, [{}, {}])

class test_alternate_linendings(tagsub_TestCase):
    # Line endings are really only considered for blank line suppression
    def test_mac_lineending1(self):
        result = substitute('@', 'line 1\rline 2\r<\r <@test> \r x <@test>\r <!-- comment --> \r<@test>', {})
        self.assertEqual(result, 'line 1\rline 2\r<\r x \r <!-- comment --> \r')

    def test_mac_lineending2(self):
        result = substitute('@',
                            'line 1\rline 2\r\r <@test> \r x <@test>\r <!-- comment --> \r<@test>',
                            {}, doSuppressComments=True)
        self.assertEqual(result, 'line 1\rline 2\r\r x \r')

    def test_dos_lineending1(self):
        result = substitute('@', 'line 1\r\nline 2\r\n<\r\n <@test> \r\n x <@test>\r\n <!-- comment --> \r\n<@test>',
                            {})
        self.assertEqual(result, 'line 1\r\nline 2\r\n<\r\n x \r\n <!-- comment --> \r\n')

    def test_dos_lineending2(self):
        result = substitute('@',
                            'line 1\r\nline 2\r\n\r\n <@test> \r\n x <@test>\r\n <!-- comment --> \r\n<@test>',
                            {}, doSuppressComments=True)
        self.assertEqual(result, 'line 1\r\nline 2\r\n\r\n x \r\n')

    # We may have mixed linendings in our applications, with a template
    #   edited on unix and text substituted in from Windows or Macs.
    def test_mixed_lineending1(self):
        result = substitute('@', 'line 1\r\nline 2 <\n\r <@test> \r\n x <@test>\r <!-- comment --> \n<@test>',
                            {})
        self.assertEqual(result, 'line 1\r\nline 2 <\n\r x \r <!-- comment --> \n')

    def test_mixed_lineending2(self):
        result = substitute('@',
                            'line 1\r\nline 2\n\r <@test> \r\n x <@test>\r <!-- comment --> \n<@test>',
                            {}, doSuppressComments=True)
        self.assertEqual(result, 'line 1\r\nline 2\n\r x \r')


class test_valid_tagnames(tagsub_TestCase):
    def test_validchars1(self):
        ## Will use the edges of the legal range. Should not fail
        result = substitute('@', '<@AZaz09_>', {})
        self.assertEqual(result, '')

    def test_validchars2(self):
        self.assertRaisesAndMatchesTraceback(InvalidTagKeyName,
                                             '1(1,1)',
                                             substitute, '@', '<@AZaz09_->', {})

    def test_validchars3(self):
        self.assertRaisesAndMatchesTraceback(InvalidTagKeyName,
                                             '1(1,1)',
                                             substitute, '@', '<@@asdf>', {})

    def test_validchars4(self):
        self.assertRaisesAndMatchesTraceback(InvalidTagKeyName,
                                             '1(1,1)',
                                             substitute, '@', '<@ asdf qwerty>', {})

    def test_validchars5(self):
        self.assertRaisesAndMatchesTraceback(ExpressionError,
                                             '1(1,1)',
                                             substitute, '@', '<@if  asdf| qwerty.><@/if>', {})

    def test_validchars6(self):
        self.assertRaisesAndMatchesTraceback(InvalidTagKeyName,
                                             '1(1,1)',
                                             substitute, '@', '<@if isLast|:isFirst><@/if>', {})

    def test_validchars7(self):
        result = substitute('@', '<@loop list ><@if :isFirst >is first<@/if><@/loop>', {'list': [{}]})
        self.assertEqual(result, 'is first')

## TODO Implement more valid tagname tests


class test_boolean_expressions(tagsub_TestCase):
    def test_boolean_expression1(self):
        ## This one just checks to see that we don't fail
        result = substitute('@',
                            '<@if (isEarly|isLate)&isOpen>Needs to close<@/if>', {})
        self.assertEqual(result, '')

    def test_boolean_expression2(self):
        result = substitute('@',
                            '<@if skipVowels & (isA | isE|isI|isO|isU)>skip<@/if>',
                            {'skipVowels': 0, 'isA': 1})
        self.assertEqual(result, '')

    def test_boolean_expression3(self):
        result = substitute('@',
                            '<@if skipVowels & (isA | isE|isI|isO|isU)>skip<@/if>',
                            {'skipVowels': 1, 'isA': 0, 'isU': 1})
        self.assertEqual(result, 'skip')

    def test_boolean_expression4(self):
        result = substitute('@',
                            '<@if skipVowels & (isA | isE|isI|isO|isU)>skip<@/if>',
                            {'skipVowels': 1, 'isA': 0, 'isU': 0})
        self.assertEqual(result, '')

    def test_boolean_expression5(self):
        self.assertRaisesAndMatchesTraceback(ExpressionError,
                                             '1(1,1)',
                                             substitute, '@',
                                             '<@if a | | b><@/if>', {})

    def test_boolean_expression6(self):
        self.assertRaisesAndMatchesTraceback(ExpressionError,
                                             '1(1,1)',
                                             substitute, '@',
                                             '<@if a ! b><@/if>', {})

    def test_boolean_expression7(self):
        result = substitute('@',
                            '<@if a | ! b>test<@/if>', {})
        self.assertEqual(result, 'test')

    def test_boolean_expression8(self):
        self.assertRaisesAndMatchesTraceback(ExpressionError,
                                             '1(1,1)',
                                             substitute, '@',
                                             '<@if a | ! b &><@/if>', {})

    def test_boolean_expression9(self):
        self.assertRaisesAndMatchesTraceback(ExpressionError,
                                             '1(1,1)',
                                             substitute, '@',
                                             '<@if (a | ! b & c><@/if>', {})

    def test_boolean_expression10(self):
        self.assertRaisesAndMatchesTraceback(ExpressionError,
                                             '1(1,1)',
                                             substitute, '@',
                                             '<@if a | ! b & c)><@/if>', {})

    def test_boolean_expression11(self):
        self.assertRaisesAndMatchesTraceback(ExpressionError,
                                             '1(1,1)',
                                             substitute, '@',
                                             '<@if b & )><@/if>', {})

    def test_boolean_expression12(self):
        self.assertRaisesAndMatchesTraceback(TagsubTemplateSyntaxError,
                                             '1(1,1)',
                                             substitute, '@', '<@if test | test2 & ', {})

    def test_boolean_expression13(self):
        self.assertRaisesAndMatchesTraceback(ExpressionError,
                                             '1(1,1)',
                                             substitute, '@',
                                             '<@if ! a  b & c><@/if>', {})

    def test_boolean_expression14(self):
        ## This one just checks to see that we don't fail
        result = substitute('@',
                            '<@if False>False<@elif (isEarly|isLate)&isOpen>Needs to close<@/if>', {})
        self.assertEqual(result, '')

    def test_boolean_expression15(self):
        result = substitute('@',
                            '<@if False><False><@elif skipVowels & (isA | isE|isI|isO|isU)>skip<@/if>',
                            {'skipVowels': 0, 'isA': 1})
        self.assertEqual(result, '')

    def test_boolean_expression16(self):
        result = substitute('@',
                            '<@if False><False><@elif skipVowels & (isA | isE|isI|isO|isU)>skip<@/if>',
                            {'skipVowels': 1, 'isA': 0, 'isU': 1})
        self.assertEqual(result, 'skip')

    def test_boolean_expression17(self):
        result = substitute('@',
                            '<@if False><False><@elif skipVowels & (isA | isE|isI|isO|isU)>skip<@/if>',
                            {'skipVowels': 1, 'isA': 0, 'isU': 0})
        self.assertEqual(result, '')

    def test_boolean_expression18(self):
        self.assertRaisesAndMatchesTraceback(ExpressionError,
                                             '19(1,19)',
                                             substitute, '@',
                                             '<@if False><False><@elif a | | b><@/if>', {})

    def test_boolean_expression19(self):
        self.assertRaisesAndMatchesTraceback(ExpressionError,
                                             '19(1,19)',
                                             substitute, '@',
                                             '<@if False><False><@elif a ! b><@/if>', {})

    def test_boolean_expression20(self):
        result = substitute('@',
                            '<@if False><False><@elif a | ! b>test<@/if>', {})
        self.assertEqual(result, 'test')

    def test_boolean_expression21(self):
        self.assertRaisesAndMatchesTraceback(ExpressionError,
                                             '19(1,19)',
                                             substitute, '@',
                                             '<@if False><False><@elif a | ! b &><@/if>', {})

    def test_boolean_expression22(self):
        self.assertRaisesAndMatchesTraceback(ExpressionError,
                                             '19(1,19)',
                                             substitute, '@',
                                             '<@if False><False><@elif (a | ! b & c><@/if>', {})

    def test_boolean_expression23(self):
        self.assertRaisesAndMatchesTraceback(ExpressionError,
                                             '19(1,19)',
                                             substitute, '@',
                                             '<@if False><False><@elif a | ! b & c)><@/if>', {})

    def test_boolean_expression24(self):
        self.assertRaisesAndMatchesTraceback(ExpressionError,
                                             '19(1,19)',
                                             substitute, '@',
                                             '<@if False><False><@elif b & )><@/if>', {})

    def test_boolean_expression25(self):
        self.assertRaisesAndMatchesTraceback(TagsubTemplateSyntaxError,
                                             '19(1,19)',
                                             substitute, '@', '<@if False><False><@elif test | test2 & ', {})

    def test_boolean_expression26(self):
        self.assertRaisesAndMatchesTraceback(ExpressionError,
                                             '19(1,19)',
                                             substitute, '@',
                                             '<@if False><False><@elif ! a  b & c><@/if>', {})

    def test_boolean_expression27(self):
        self.assertRaisesAndMatchesTraceback(ExpressionError,
                                             '1(1,1)',
                                             substitute, '@',
                                             '<@if ! a + b & c><@/if>', {})

    def test_boolean_expression28(self):
        self.assertRaisesAndMatchesTraceback(ExpressionError,
                                             '1(1,1)',
                                             substitute, '@',
                                             '<@if (!a & ) & c><@/if>', {})

    def test_boolean_expression29(self):
        self.assertRaisesAndMatchesTraceback(ExpressionError,
                                             '2(2,1)',
                                             substitute, '@',
                                             '\n<@if (a ><@/if>', {})

    # TODO More if/elif expression tests with complicated expressions
    #      Try a number of combinations of invalid expressions. Also try expressions in other tags
    #      to see if they fail properly.

    def test_boolean_expression_overflow1(self):
        # operand and operator stacks are both 8 deep
        # each operator and '(' take a place on the stack
        # XXX If we recompile tagsub with different constants, this may
        #  need to be changed along with the following test to properly
        #  test overflow conditions
        self.assertEqual(tagsub.max_expression_depth, 8)
        result = substitute('@',
                            '<@if (a | (b & (c | (d & e))))><@/if>',
                            {})
        self.assertEqual(result, '')

    def test_boolean_expression_overflow2(self):
        # operand and operator stacks are both 8 deep
        # each operator and '(' take a place on the stack
        # XXX If we recompile tagsub with different constants, this may
        #  need to be changed along with the following test to properly
        #  test overflow conditions
        self.assertEqual(tagsub.max_expression_depth, 8)
        self.assertRaisesAndMatchesTraceback(ExpressionStackOverflowError,
                                             '1(1,1)',
                                             substitute, '@',
                                             '<@if (a | (b & (c | (d & (e)))))><@/if>',
                                             {})

    def test_boolean_expression_overflow3(self):
        # XXX If we recompile tagsub with different constants, this may
        #  need to be changed along with the following test to properly
        #  test overflow conditions
        self.assertEqual(tagsub.max_expression_depth, 8)
        result = substitute('@',
                            '<@if (a | (b & (c | (d & e & f))))><@/if>',
                            {})
        self.assertEqual(result, '')

    def test_boolean_expression_overflow4(self):
        # Save as above, but | is lower precedence than & so, must get
        #   pushed on the stack which is already full.
        # XXX If we recompile tagsub with different constants, this may
        #  need to be changed along with the following test to properly
        #  test overflow conditions
        self.assertEqual(tagsub.max_expression_depth, 8)
        self.assertRaisesAndMatchesTraceback(ExpressionStackOverflowError,
                                             '1(1,1)',
                                             substitute, '@',
                                             '<@if (a | (b & (c | (d | e & f))))><@/if>',
                                             {})


class test_impliedLoopVariables(tagsub_TestCase):
    def test_implied_loop_variables1(self):
        # Fail if we reference a loop that we are not in
        self.assertRaisesAndMatchesTraceback(InvalidTagKeyName,
                                             '1(1,1)',
                                             substitute, '@', '<@list:isFirst>', {})

    def test_implied_loop_variables2(self):
        # Fail if we reference a loop that we are not in
        self.assertRaisesAndMatchesTraceback(InvalidTagKeyName,
                                             '14(1,14)',
                                             substitute, '@', '<@loop list1><@list2:isFirst><@/loop>',
                                             {'list1': [{}, {}]})

    def test_implied_loop_variables3(self):
        # Illegal implied loop variable name "isBig"
        self.assertRaisesAndMatchesTraceback(InvalidTagKeyName,
                                             '14(1,14)',
                                             substitute, '@', '<@loop list1><@:isBig><@/loop>', {'list1': [{}, {}]})

    def test_implied_loop_variables4(self):
        # Only one ":" allowed in an implied loop variable name
        self.assertRaisesAndMatchesTraceback(InvalidTagKeyName,
                                             '14(1,14)',
                                             substitute, '@', '<@loop list1><@list1:isFirst:isLast><@/loop>',
                                             {'list1': [{}, {}]})

    def test_implied_loop_variables4a(self):
        # Special test case if nothing after the  ":"
        self.assertRaisesAndMatchesTraceback(InvalidTagKeyName,
                                             '14(1,14)',
                                             substitute, '@', '<@loop list1><@list1:><@/loop>',
                                             {'list1': [{}, {}]})

    def test_implied_loop_variables5(self):
        # If loop name not specified, use the next outer enclosing loop.
        result = substitute('@', '<@loop list1><@:isFirst> <@/loop>', {'list1': [{}, {}]})
        self.assertEqual('1 0 ', result)

    def test_implied_loop_variables6(self):
        result = substitute('@',
                            '<@loop list1><@list1:isFirst><@list1:isLast><@list1:isOdd><@list1:isEven>'
                            '<@list1:index><@list1:index0><@list1:rindex><@list1:rindex0><@list1:length>'
                            '\n<@/loop>',
                            {'list1': [{}, {}, {}, {}]})
        self.assertEqual('101010434\n000121324\n001032214\n010143104\n', result)

    def test_implied_loop_variables7(self):
        ## We can reference a loop that is nested outside of the loop we are in
        result = substitute('@',
                            '<@loop list1><@loop list2><@list1:isFirst><@list1:isLast><@list1:isOdd><@list1:isEven>'
                            '<@list1:index><@list1:index0><@list1:rindex><@list1:rindex0><@list1:length>'
                            '<@/loop>\n<@/loop>',
                            {'list1': [{}, {}, {}, {}], 'list2': [{}, {}]})
        self.assertEqual('101010434101010434\n000121324000121324\n001032214001032214\n010143104010143104\n', result)

    def test_implied_loop_variables8(self):
        ## Use a default implied variable
        result = substitute('@',
                            '<@loop list1><@:index><@/loop>', {'list1': [{}, {}, {}, {}]})
        self.assertEqual('1234', result)

    def test_implied_loop_variables9(self):
        ## We can reference a loop that is nested outside of the loop we are in
        ## No loop specified means the innermost loop
        result = substitute('@#',
                            """<@loop list1>
<#loop list2>
outer isFirst: <@list1:isFirst>
inner isFirst: <#:isFirst>
outer isLast: <@list1:isLast>
inner isLast: <#:isLast>
outer isOdd: <@list1:isOdd>
inner isOdd: <#:isOdd>
outer isEven: <@list1:isEven>
inner isEven: <#:isEven>
outer index: <@list1:index>
inner index: <#:index>
outer index0: <@list1:index0>
inner index0: <# :index0>
outer rindex: <@list1:rindex>
inner rindex: <#:rindex>
outer rindex0: <@list1:rindex0>
inner rindex0: <#:rindex0>
outer length: <@list1:length>
inner length: <# :length>
<#/loop>
<@/loop>""",
                            [{'list1': [{}, {}]}, {'list2': [{}, {}]}])
        assumed_result = \
            """outer isFirst: 1
inner isFirst: 1
outer isLast: 0
inner isLast: 0
outer isOdd: 1
inner isOdd: 1
outer isEven: 0
inner isEven: 0
outer index: 1
inner index: 1
outer index0: 0
inner index0: 0
outer rindex: 2
inner rindex: 2
outer rindex0: 1
inner rindex0: 1
outer length: 2
inner length: 2
outer isFirst: 1
inner isFirst: 0
outer isLast: 0
inner isLast: 1
outer isOdd: 1
inner isOdd: 0
outer isEven: 0
inner isEven: 1
outer index: 1
inner index: 2
outer index0: 0
inner index0: 1
outer rindex: 2
inner rindex: 1
outer rindex0: 1
inner rindex0: 0
outer length: 2
inner length: 2
outer isFirst: 0
inner isFirst: 1
outer isLast: 1
inner isLast: 0
outer isOdd: 0
inner isOdd: 1
outer isEven: 1
inner isEven: 0
outer index: 2
inner index: 1
outer index0: 1
inner index0: 0
outer rindex: 1
inner rindex: 2
outer rindex0: 0
inner rindex0: 1
outer length: 2
inner length: 2
outer isFirst: 0
inner isFirst: 0
outer isLast: 1
inner isLast: 1
outer isOdd: 0
inner isOdd: 0
outer isEven: 1
inner isEven: 1
outer index: 2
inner index: 2
outer index0: 1
inner index0: 1
outer rindex: 1
inner rindex: 1
outer rindex0: 0
inner rindex0: 0
outer length: 2
inner length: 2
"""
        self.assertEqual(assumed_result, result)


## test tags that look like the beginning of a tag i.e. <@iffy> also <@ifEOF (probably should try for each tag)
class test_badAlmostRealTags(tagsub_TestCase):
    def test_misc_bad_tag1(self):
        # Just to be sure we aren't incorrectly identifying a tag because
        #   of a familiar prefix
        result = substitute('@', '<@iffy>text', {})
        self.assertEqual(result, 'text')

    def test_misc_bad_tag2(self):
        # No spaces allowed in tagname
        self.assertRaisesAndMatchesTraceback(InvalidTagKeyName,
                                             '1(1,1)',
                                             substitute, '@', '<@iffy var>text', {})

    def test_misc_bad_tag3(self):
        self.assertRaisesAndMatchesTraceback(TagsubTemplateSyntaxError,
                                             '1(1,1)',
                                             substitute, '@', '<@if ', {})

    def test_misc_bad_tag3a(self):
        self.assertRaisesAndMatchesTraceback(TagsubTemplateSyntaxError,
                                             '1(1,1)',
                                             substitute, '@', '<@if', {})

    def test_misc_bad_tag4(self):
        self.assertRaisesAndMatchesTraceback(TagsubTemplateSyntaxError,
                                             '11(1,11)',
                                             substitute, '@', '<@if test><@/if', {})

    def test_misc_bad_tag4a(self):
        self.assertRaisesAndMatchesTraceback(TagsubTemplateSyntaxError,
                                             '11(1,11)',
                                             substitute, '@', '<@if test><@/if ', {})

    def test_misc_bad_tag4b(self):
        self.assertRaisesAndMatchesTraceback(TagsubTemplateSyntaxError,
                                             '12(1,12)',
                                             substitute, '@', '<@if !test><@/if', {})

    def test_misc_bad_tag4c(self):
        self.assertRaisesAndMatchesTraceback(TagsubTemplateSyntaxError,
                                             '12(1,12)',
                                             substitute, '@', '<@if !test><@/if ', {})

    def test_misc_bad_tag5(self):
        self.assertRaisesAndMatchesTraceback(TagsubTemplateSyntaxError,
                                             '1(1,1)',
                                             substitute, '@', '<@', {})

    ## Test ending with special characters
    def test_misc_bad_tag6(self):
        result = substitute('@', '<', {})
        self.assertEqual(result, '<')

    def test_misc_bad_tag7(self):
        result = substitute('@', '<\r', {})
        self.assertEqual(result, '<\r')


## Some of these tests appear with the appropriate tag tests elsewhere.
class test_whitespaceVariationsInTags(tagsub_TestCase):
    def test_whitespace1(self):
        result = substitute('@', '<@if\tisTrue \n>true<@/if>', {'isTrue': 1})
        self.assertEqual(result, 'true')

    def test_whitespace2(self):
        result = substitute('@', '<@if\tisTrue \n>true<@/if>', {'isTrue': 0})
        self.assertEqual(result, '')


class test_misplacedTagsFromGroups(tagsub_TestCase):
    def test_unclosed_if_tag(self):
        self.assertRaisesAndMatchesTraceback(TagsubTemplateSyntaxError,
                                             '1(1,1)',
                                             substitute, '@', '<@if test> ', {})

    def test_unclosed_elif_tag(self):
        self.assertRaisesAndMatchesTraceback(TagsubTemplateSyntaxError,
                                             '1(1,1)',
                                             substitute, '@', '<@if test> <@elif test> ', {})

    def test_unclosed_else_tag(self):
        self.assertRaisesAndMatchesTraceback(TagsubTemplateSyntaxError,
                                             '1(1,1)',
                                             substitute, '@', '<@if test> <@else > ', {})

    def test_bad_elif_tag(self):
        self.assertRaisesAndMatchesTraceback(TagsubTemplateSyntaxError,
                                             '1(1,1)',
                                             substitute, '@', '<@elif test><@/if>', {})

    def test_bad_endif_tag(self):
        self.assertRaisesAndMatchesTraceback(TagsubTemplateSyntaxError,
                                             '1(1,1)',
                                             substitute, '@', '<@/if>', {})

    def test_bad_else_tag(self):
        self.assertRaisesAndMatchesTraceback(TagsubTemplateSyntaxError,
                                             '1(1,1)',
                                             substitute, '@', '<@else>', {})

    def test_unclosed_case_tag(self):
        self.assertRaisesAndMatchesTraceback(TagsubTemplateSyntaxError,
                                             '1(1,1)',
                                             substitute, '@', '<@case test>', {})

    def test_unclosed_option_tag(self):
        self.assertRaisesAndMatchesTraceback(TagsubTemplateSyntaxError,
                                             '1(1,1)',
                                             substitute, '@', '<@case test> <@option 1> ', {})

    def test_unclosed_case_else_tag(self):
        self.assertRaisesAndMatchesTraceback(TagsubTemplateSyntaxError,
                                             '1(1,1)',
                                             substitute, '@', '<@case test> <@option 1>1<@else>', {})

    def test_bad_endcase_tag(self):
        self.assertRaisesAndMatchesTraceback(TagsubTemplateSyntaxError,
                                             '1(1,1)',
                                             substitute, '@', '<@/case>', {})

    def test_bad_option_tag(self):
        self.assertRaisesAndMatchesTraceback(TagsubTemplateSyntaxError,
                                             '1(1,1)',
                                             substitute, '@', '<@option 1>', {})

    def test_unclosed_loop_tag(self):
        self.assertRaisesAndMatchesTraceback(TagsubTemplateSyntaxError,
                                             '1(1,1)',
                                             substitute, '@', '<@loop test>', {})

    def test_bad_endloop_tag(self):
        self.assertRaisesAndMatchesTraceback(TagsubTemplateSyntaxError,
                                             '1(1,1)',
                                             substitute, '@', '<@/loop>', {})

    def test_unclosed_saveraw_tag(self):
        self.assertRaisesAndMatchesTraceback(TagsubTemplateSyntaxError,
                                             '1(1,1)',
                                             substitute, '@', '<@saveraw test>', {})

    def test_bad_endsaveraw_tag(self):
        self.assertRaisesAndMatchesTraceback(TagsubTemplateSyntaxError,
                                             '1(1,1)',
                                             substitute, '@', '<@/saveraw>', {})

    def test_unclosed_saveeval(self):
        self.assertRaisesAndMatchesTraceback(TagsubTemplateSyntaxError,
                                             '1(1,1)',
                                             substitute, '@', '<@saveeval test>', {})

    def test_bad_endsaveeval(self):
        self.assertRaisesAndMatchesTraceback(TagsubTemplateSyntaxError,
                                             '1(1,1)',
                                             substitute, '@', '<@/saveeval>', {})

    def test_unclosed_namespace(self):
        ## FIXME This should get cleaned up when we separate namespaces from the loop stack
        self.assertRaisesAndMatchesTraceback(TagsubTemplateSyntaxError,
                                             '1(1,1)',
                                             substitute, '@', '<@namespace test>', {'test': {}})

    def test_bad_endnamespace(self):
        self.assertRaisesAndMatchesTraceback(TagsubTemplateSyntaxError,
                                             '1(1,1)',
                                             substitute, '@', '<@/namespace>', {})

    def test_unclosed_saveoverride_tag(self):
        self.assertRaisesAndMatchesTraceback(TagsubTemplateSyntaxError,
                                             '1(1,1)',
                                             substitute, '@', '<@saveoverride test>', {})

    def test_unclosed_saveoverride_tag2(self):
        self.assertRaisesAndMatchesTraceback(TagsubTemplateSyntaxError,
                                             '1(1,1)',
                                             substitute, '@', '<@saveoverride test><@super>', {})

    def test_bad_endsaveoverride_tag(self):
        self.assertRaisesAndMatchesTraceback(TagsubTemplateSyntaxError,
                                             '1(1,1)',
                                             substitute, '@', '<@/saveoverride>', {})

    def test_bad_endsaveoverride_tag2(self):
        self.assertRaisesAndMatchesTraceback(TagsubTemplateSyntaxError,
                                             '10(1,10)',
                                             substitute, '@', '<@ super><@/saveoverride>', {})

    def test_isolated_super_tag(self):
        self.assertRaisesAndMatchesTraceback(TagsubTemplateSyntaxError,
                                            '1(1,1)',
                                             substitute, '@', '<@super>', {})


# Saving over a list variable in a loop. The internal reference should make it act unix-like and allow
#      us to continue to use the list. Outside of the list, the new saved tag should be usable. Maybe try a nested
#      list with the saveraw in the outer loop after the first pass through the inner loop. (Should get a type error
#      the second pass ?? A string may actually test true as a sequence of mappings...)
class test_loop_save_interactions(tagsub_TestCase):
    # On saveraw tests, do not use reference counting variation on substitute
    #  because our dictionary is being modified and will show up as an error.
    def test_loop_saveraw1(self):
        result = tagsub.substitute('@',
                                   '<@loop list><@list:index><@saveraw list>replace<@/saveraw><@/loop><@list>',
                                   {'list': [{}, {}, {}]})
        self.assertEqual(result, '123replace')

    def test_loop_saveraw2(self):
        self.assertRaisesAndMatchesTraceback(InvalidTagKeyName,
                                             '26(1,26)',
                                             tagsub.substitute, '@',
                                             '<@loop list><@list:index><@saveraw list:index>replace<@/saveraw><@/loop><@list>',
                                             {'list': [{}, {}, {}]})

    def test_loop_saveeval1(self):
        result = tagsub.substitute('@',
                                   '<@loop list><@list:index><@saveeval list>replace<@/saveeval><@/loop><@list>',
                                   {'list': [{}, {}, {}]})
        self.assertEqual(result, '123replace')

    def test_loop_saveeval2(self):
        self.assertRaisesAndMatchesTraceback(InvalidTagKeyName,
                                             '26(1,26)',
                                             tagsub.substitute, '@',
                                             '<@loop list><@list:index><@saveeval list:index>replace<@/saveeval><@/loop><@list>',
                                             {'list': [{}, {}, {}]})


class test_force_reallocate(tagsub_TestCase):
    # Resulting string is 5*5*5*10 bytes long, or 12,500 bytes which will
    #   require several reallocations, since we add 1024 bytes at a time.
    def test_reallocate1(self):
        result = substitute('@',
                            '<@loop list><@loop list><@loop list>1234567890<@/loop><@/loop><@/loop>',
                            {'list': [{}, {}, {}, {}, {}]})
        self.assertEqual(result, '1234567890' * 125)


class test_basic_saveeval(tagsub_TestCase):
    # The save raw will reinitialize temp to a null string, because substitute will invoke
    #  the processing twice.
    def test_basic_saveeval1(self):
        d = {'list': [{}, {}, {}, {}]}
        result = substitute('@',
                            '<@saveraw temp><@/saveraw><@temp><@loop list><@saveeval temp><@temp><@if !:isFirst>,<@/if><@list:rindex><@/saveeval><@/loop><@temp>',
                            d)
        self.assertEqual('4,3,2,1', result)


class test_basic_recursive_substitution(tagsub_TestCase):
    def test_basic_recursive_substitution1(self):
        self.assertRaisesAndMatchesTraceback(TagsubTemplateSyntaxError,
                                             '1(1,1)/3(3,1)/25(2,13)',
                                             substitute, '@',
                                             '<@tag1>',
                                             {
                                                 'tag1': '\n\n<@tag2>',
                                                 'tag2': 'line 1 text\n line 2 text<@tag3',
                                             }
                                             )

    def test_basic_recursive_substitution2(self):
        self.assertRaisesAndMatchesTraceback(InvalidTagKeyName,
                                             '1(1,1)/3(3,1)/25(2,13)',
                                             substitute, '@',
                                             '<@tag1>',
                                             {
                                                 'tag1': '\n\n<@tag2>',
                                                 'tag2': 'line 1 text\n line 2 text<@if :isFirst>',
                                             }
                                             )

    def test_basic_recursive_substitution3(self):
        self.assertRaisesAndMatchesTraceback(TagsubTemplateSyntaxError,
                                             '1(1,1)/3(3,1)/25(2,13)',
                                             substitute, '@',
                                             '<@tag1>',
                                             {
                                                 'tag1': '\n\n<@tag2>',
                                                 'tag2': 'line 1 text\n line 2 text<@if isFirst>',
                                             }
                                             )


class test_basic_namespace(tagsub_TestCase):
    ## TODO Make sure that implied loop variables don't interact badly.

    def test_basic_namespace1(self):
        result = substitute('@', '<@test> <@namespace test_namespace><@test><@/namespace>',
                            {'test': 'test', 'test_namespace': {}})
        self.assertEqual(result, 'test test')

    def test_basic_namespace2(self):
        result = substitute('@', '<@test> <@namespace test_namespace><@test><@/namespace>',
                            {'test': 'test', 'test_namespace': {'test': 'overridden value'}})
        self.assertEqual(result, 'test overridden value')

    ## XXX Also fix when namespace stack separates from the loop tags. We shouldn't indicate a loop
    ##   in the traceback.
    def test_basic_namespace3(self):
        self.assertRaisesAndMatchesTraceback(InvalidTagKeyName,
                                             '28(1,28)',
                                             substitute, '@',
                                             '<@namespace test_namespace><@:invalid><@/namespace>',
                                             {'test_namespace': {}}
                                             )

    def test_basic_namespace4(self):
        self.assertRaisesAndMatchesTraceback(InvalidTagKeyName,
                                             '28(1,28)',
                                             substitute, '@',
                                             '<@namespace test_namespace><@:index><@/namespace>',
                                             {'test_namespace': {}})

    def test_basic_namespace5(self):
        self.assertRaisesAndMatchesTraceback(InvalidTagKeyName,
                                             '28(1,28)',
                                             substitute, '@',
                                             '<@namespace test_namespace><@:length><@/namespace>',
                                             {'test_namespace': {}})

    def test_basic_namespace6(self):
        result = substitute('@', '<@if False><@namespace test_namespace><@test><@/namespace><@/if><@test>',
                            {'test_namespace': {'test': 'override'}, 'test': 'original'})
        self.assertEqual(result, 'original')

    def test_basic_namespace6a(self):
        result = substitute('@', '<@if !False><@namespace test_namespace><@test><@/namespace><@/if><@test>',
                            {'test_namespace': {'test': 'override'}, 'test': 'original'})
        self.assertEqual(result, 'overrideoriginal')


class CustomError(Exception): pass


class simple_class(object):
    def _errorAttr(self):
        raise CustomError("Intentional exception raised")

    errorAttr = property(_errorAttr)


class test_attribute_access(tagsub_TestCase):
    def setUp(self):
        i = simple_class()
        i.isTrue = True
        i.isFalse = False
        i.dictList = [{'test': 'list element one'}, {'test': 'list element two'}]
        i.namespace = {'test': 'namespace text'}
        i.text = 'instance attribute text'
        i.a1 = simple_class()
        i.a1.text = 'deep attribute text'
        i.a1.a2 = simple_class()
        i.a1.a2.a3 = simple_class()
        i.a1.a2.a3.text = 'deeper attribute text'

        self.instance = i

    def test_attribute_access1(self):
        result = substitute("@", "<@if obj.isTrue>true<@/if>", {'obj': self.instance})
        self.assertEqual('true', result)

    def test_attribute_access1a(self):
        result = substitute("@", "<@if (obj.isTrue | obj.isFalse) & obj.a1.a2.a3.text>true<@/if>",
                            {'obj': self.instance})
        self.assertEqual('true', result)

    # FIXME The code needs to handle this case better. We need to be able to treat obj.dictList
    #   in the implied loop variable tag as a simple string, and we must store the simple
    #   string on the loop tag as a name.
    def test_attribute_access2(self):
        result = substitute("@", "<@loop obj.dictList><@obj.dictList:index>: <@test> <@/loop>", {'obj': self.instance})
        self.assertEqual('1: list element one 2: list element two ', result)

    def test_attribute_access2a(self):
        result = substitute("@", "<@loop obj.dictList><@:index>: <@test> <@/loop>", {'obj': self.instance})
        self.assertEqual('1: list element one 2: list element two ', result)

    def test_attribute_access3(self):
        result = substitute("@", "<@obj.text>", {'obj': self.instance})
        self.assertEqual('instance attribute text', result)

    def test_attribute_access4(self):
        result = substitute("@", "<@test> <@namespace obj.namespace><@test><@/namespace>",
                            {'test': 'top text', 'obj': self.instance})
        self.assertEqual('top text namespace text', result)

    def test_attribute_access5(self):
        result = substitute("@", "<@obj.text> <@obj.a1.text> <@obj.a1.a2.a3.text>", {'obj': self.instance})
        self.assertEqual('instance attribute text deep attribute text deeper attribute text', result)

    def test_attribute_access6(self):
        ## FIXME This is a case where the fallback of propogating exceptions from
        ##   the underlying code interferes with showing the tag that failed on an
        ##   AttributeError (via the now missing tagsub traceback string)
        self.assertRaisesAndMatchesTraceback(AttributeError,
                                             '1(1,1)',
                                             substitute,
                                             "@", "<@obj.missingattribute>", {'obj': self.instance})

    def test_attribute_access7(self):
        ## Since object is not found, the whole tag simply disappears
        result = substitute("@", "<@object.missingattribute>", {'obj': self.instance})
        self.assertEqual('', result)

    def test_attribute_access7a(self):
        self.assertRaisesAndMatchesTraceback(KeyError, '1(1,1)',
                                             substitute,
                                             "@", "<@object.missingattribute>",
                                             {'obj': self.instance}, doStrictKeyLookup=True)

    def test_attribute_access7b(self):
        self.assertRaisesAndMatchesTraceback(InvalidTagKeyName, '1(1,1)',
                                             substitute,
                                             "@", "<@object.>",
                                             {'obj': self.instance}, doStrictKeyLookup=True)

    def test_attribute_access8(self):
        self.assertRaises(CustomError,
                          substitute,
                          "@", "<@obj.errorAttr>", {'obj': self.instance})


class test_saveoverride(tagsub_TestCase):
    def test_saveoverride1(self):
        d = {'test': 'original'}
        result = tagsub.substitute('@',
                                   '<@saveoverride test>override of <@super><@/saveoverride><@saveoverride test>>>>> <@super> '
                                   '<<<<<@/saveoverride><@test>', d)
        self.assertEqual('>>>> override of original <<<<', result)

    def test_saveoverride1a(self):
        d = {'test': 'original', 'list':[{},{}]}
        result = tagsub.substitute('@',
                                   '<@saveoverride test>override of<@loop list> <@super><@/loop><@/saveoverride><@saveoverride test>>>>> <@super> '
                                   '<<<<<@/saveoverride><@test>', d)
        self.assertEqual('>>>> override of original original <<<<', result)

    def test_saveoverride2(self):
        d = {}
        result = tagsub.substitute('@',
                                   '<@saveoverride test>override of <@super><@/saveoverride><@saveoverride test>>>>> <@super> '
                                   '<<<<<@/saveoverride><@test>', d)
        self.assertEqual('>>>> override of  <<<<', result)

    def test_saveoverride3(self):
        # Important to get coverage
        d = {'test': 'original'}
        result = tagsub.substitute('@',
                                   '<@if false><@saveoverride test>override of <@super><@/saveoverride><@saveoverride test>>>>> <@super> '
                                   '<<<<<@/saveoverride><@/if><@test>', d)
        self.assertEqual('original', result)

    def test_saveoverride4(self):
        self.assertRaisesAndMatchesTraceback(InvalidTagKeyName,
            '26(1,26)',
            tagsub.substitute,'@',
            '<@loop list><@list:index><@saveoverride list:index>replace<@/saveoverride><@/loop><@list>',
            {'list':[{},{},{}]})

    def test_saveoverride4a(self):
        self.assertRaisesAndMatchesTraceback(InvalidTagKeyName,
            '1(1,1)',
            tagsub.substitute,'@',
            '<@saveoverride name.val>replace<@/saveoverride>',
            {'name':"test"})

    def test_saveoverride5(self):
        self.assertRaisesAndMatchesTraceback(InvalidTagKeyName,
            '26(1,26)',
            tagsub.substitute,'@',
            '<@loop list><@list:index><@saveraw list:index>replace<@/saveraw><@/loop><@list>',
            {'list':[{},{},{}]})

    def test_saveoverride6(self):
        self.assertRaisesAndMatchesTraceback(TagsubTemplateSyntaxError,
            '21(1,21)',
            tagsub.substitute, '@',
            '<@saveoverride test><@super duper><@/saveoverride',
            {})

class test_iterator(tagsub_TestCase):
    def test_iterator1(self):
        def f(n):
            for i in range(n):
                yield {'count':i}
        d = {'list':f(5)}
        result = substitute('@', '<@loop list><@if !:isFirst>,<@/if><@count><@/loop>', d)
        self.assertEqual('0,1,2,3,4', result)

class mapping(collections.abc.Mapping):
    def __getitem__(self, key):
        if key == "error":
            raise CustomError("Error key hit")
        return "Value for %s" % key

    # We must implement __iter__ and __len__ for Mapping. In our case it will give different results than referencing individual items.
    def __iter__(self):
        return iter(["error"])

    def __len__(self):
        return 1


class test_mapping(tagsub_TestCase):
    def test_mapping1(self):
        result = substitute('@', '<@bob> <@if ted>Ted<@/if>', [mapping()])
        self.assertEqual(result, 'Value for bob Ted')

    def test_mapping2(self):
        result = substitute('@', '<@loop name><@bob> <@/loop>', {'name': [mapping(), mapping(), mapping()]})
        self.assertEqual(result, 'Value for bob Value for bob Value for bob ')

    def test_mapping3(self):
        self.assertRaisesAndMatchesTraceback(
            CustomError,
            '8(1,8)',
            substitute,
            '@', '<@bob> <@error>', [mapping()])

    def test_mapping3a(self):
        self.assertRaisesAndMatchesTraceback(
            CustomError,
            '8(1,8)',
            substitute,
            '@', '<@bob> <@error>', [mapping()], doStrictKeyLookup=True)


class test_invalidCloseTags(tagsub_TestCase):
    def test_closeTag1(self):
        self.assertRaisesAndMatchesTraceback(
            TagsubTemplateSyntaxError,
            '11(1,11)',
            substitute,
            '@', '<@if true><@/test>', {}
        )

    def test_closeTag2(self):
        self.assertRaisesAndMatchesTraceback(
            TagsubTemplateSyntaxError,
            '11(1,11)',
            substitute,
            '@', '<@if true><@/if.test>', {}
        )

    def test_closeTag3(self):
        self.assertRaisesAndMatchesTraceback(
            TagsubTemplateSyntaxError,
            '11(1,11)',
            substitute,
            '@', '<@if true><@/if:test>', {}
        )

    def test_closeTag4(self):
        self.assertRaisesAndMatchesTraceback(
            TagsubTemplateSyntaxError,
            '11(1,11)',
            substitute,
            '@', '<@if true><@/if test>', {}
        )


class test_htmlsafe_and_rawstring(tagsub_TestCase):
    def test_htmlsafe1a(self):
        result = substitute(
            '@',
            '<input type="hidden" value="<@value>"/>',
            {'value': '<b>sample text</b>'},
            doEncodeHtml=False
        )
        self.assertEqual('<input type="hidden" value="<b>sample text</b>"/>', result)

    def test_htmlsafe1b(self):
        result = substitute(
            '@',
            '<input type="hidden" value="<@value>"/>',
            {'value': '<b>sample text</b>'},
            doEncodeHtml=True
        )
        self.assertEqual('<input type="hidden" value="&lt;b&gt;sample text&lt;/b&gt;"/>', result)

    def test_htmlsafe1c(self):
        result = substitute(
            '@',
            '<input type="hidden" value="<@value>"/>',
            {'value': '<b><@if bob>sample text<@/if></b>'},
            doEncodeHtml=True
        )
        self.assertEqual('<input type="hidden" value="&lt;b&gt;&lt;@if bob&gt;sample text&lt;@/if&gt;&lt;/b&gt;"/>', result)

    def test_htmlsafe_rawstr1a(self):
        result = substitute(
            '@',
            '<input type="hidden" value="<@value>"/>',
            {'value': tagsub.rawstr('<b><@if bob>sample text<@/if></b>')},
            doEncodeHtml=True
        )
        self.assertEqual('<input type="hidden" value="<b><@if bob>sample text<@/if></b>"/>', result)

    def test_htmlsafe_rawstr1b(self):
        result = substitute(
            '@',
            '<input type="hidden" value="<@value>"/>',
            {'value': tagsub.rawstr('<b><@if bob>sample text<@/if></b>')},
            doEncodeHtml=False
        )
        self.assertEqual('<input type="hidden" value="<b><@if bob>sample text<@/if></b>"/>', result)

    def test_htmlsafe_rawstr2a(self):
        result = substitute(
            '@',
            '<input type="hidden" value="<@value2>"/>',
            {'value2': '<b></b>'},
            doEncodeHtml=True
        )
        self.assertEqual('<input type="hidden" value="&lt;b&gt;&lt;/b&gt;"/>', result)

    def test_htmlsafe_rawstr2b(self):
        result = substitute(
            '@',
            '<input type="hidden" value="<@value2>"/>',
            {'value2': tagsub.rawstr('<b></b>')},
            doEncodeHtml=True
        )
        self.assertEqual('<input type="hidden" value="<b></b>"/>', result)

    def test_rawstr1(self):
        ## Test the class relationship with str
        s = tagsub.rawstr('test')
        self.assertEqual(s, 'test')
        self.assertTrue(isinstance(s, str))
        self.assertTrue(isinstance(s, tagsub.rawstr))
        self.assertTrue(issubclass(tagsub.rawstr, str))

        self.assertFalse(isinstance(str(s), tagsub.rawstr))
        self.assertFalse(isinstance('test', tagsub.rawstr))

class test_util_classes_Stack(tagsub_TestCase):
    def setUp(self) -> None:
        self.intStack = Stack(lambda i: isinstance(i, int))

    def test_Stack1(self):
        # Needed to test some of the Stack error cases.
        self.assertRaises(TypeError, self.intStack.push, 'strValue')

    def test_Stack2(self):
        self.assertEqual(len(self.intStack), 0)
        self.intStack.push(1)
        self.assertEqual(len(self.intStack), 1)
        self.assertEqual(self.intStack.pop(), 1)
        self.assertEqual(self.intStack.pop(), None)
        self.assertEqual(len(self.intStack), 0)

    def test_Stack3(self):
        self.assertRaises(IndexError, operator.getitem, self.intStack, 0)
        self.assertEqual(self.intStack.top, None)
        self.intStack.push(1)
        self.assertEqual(self.intStack.top, 1)
        self.intStack.push(2)
        self.assertEqual(self.intStack.top, 2)
        self.assertRaises(IndexError, operator.getitem, self.intStack, -1)
        self.assertRaises(IndexError, operator.getitem, self.intStack, 2)
        self.assertEqual(self.intStack[0], 2)
        self.assertEqual(self.intStack[1], 1)

class test_util_classes_NamespaceStack(tagsub_TestCase):
    def setUp(self) -> None:
        self.namespace = NamespaceStack({'test': 'base val'})

    def test_NamespaceStack1(self):
        self.assertEqual(self.namespace.get('test'), 'base val')
        self.assertEqual(self.namespace['test'], 'base val')
        self.assertEqual(len(self.namespace), 1)

    def test_NamespaceStack2(self):
        self.namespace.push({'test': 'override val'})
        self.assertEqual(self.namespace.get('test2'), None)
        self.assertEqual(self.namespace['test'], 'override val')
        self.namespace.pop()
        self.assertEqual(self.namespace['test'], 'base val')

# This does not fully exercise TemplateIterator, but does ensure complete code coverage
class test_util_classes_TemplateIterator(tagsub_TestCase):
    def test_TemplateIterator1(self):
        t = TemplateIterator('abc')
        self.assertEqual(next(t), 'a')
        self.assertEqual(next(t), 'b')
        self.assertEqual(next(t), 'c')
        self.assertRaises(StopIteration, next, t)

    def test_TemplateIterator2(self):
        t = TemplateIterator('abc')
        self.assertEqual(next(t), 'a')
        self.assertEqual(next(t), 'b')
        self.assertEqual(next(t.rollback(2)), 'a')
        self.assertRaises(IndexError, t.rollback, 2)

class test_util_classes_AbstractClasses(tagsub_TestCase):
    def test_Operator(self):
        o = Operator()
        self.assertRaises(NotImplementedError, o.getValue, '@', None)


if __name__ == "__main__":
    #print("Testing version:", tagsub.__version__.split()[1])
    #print("Nested tag stack depth:", tagsub.max_nested_tag_depth)
    #print("Nested loop tag stack depth:", tagsub.max_nested_loop_depth)
    #print("Recursive substitution stack depth:", tagsub.max_recursive_template_depth)
    #print("Nested saveeval tag stack depth:", tagsub.max_saveeval_depth)
    #print("Nested expression stack depth:", tagsub.max_expression_depth)
    unittest.main()
