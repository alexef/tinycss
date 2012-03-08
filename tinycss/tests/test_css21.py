# coding: utf8
"""
    Tests for the CSS 2.1 parser
    ----------------------------

    :copyright: (c) 2010 by Simon Sapin.
    :license: BSD, see LICENSE for more details.
"""


from __future__ import unicode_literals
import pytest

from tinycss.css21 import CSS21Parser

from .test_tokenizer import jsonify


@pytest.mark.parametrize(('css_source', 'expected_rules', 'expected_errors'), [
    (' /* hey */\n', [], []),
    ('@import "foo.css";', [('foo.css', ['all'])], []),
    ('@import url(foo.css);', [('foo.css', ['all'])], []),
    ('@import "foo.css" screen, print;',
        [('foo.css', ['screen', 'print'])], []),
    ('@charset "ascii"; @import "foo.css"; @import "bar.css";',
        [('foo.css', ['all']), ('bar.css', ['all'])], []),
    ('foo {} @import "foo.css";',
        [], ['@import rule not allowed after a ruleset']),
    ('@page {} @import "foo.css";',
        [], ['@import rule not allowed after an @page rule']),
    ('@import ;',
        [], ['expected URI or STRING for @import rule']),
    ('@import foo.css;',
        [], ['expected URI or STRING for @import rule, got IDENT']),
    ('@import "foo.css" {}',
        [], ["expected ';', got a block"]),
])
def test_at_import(css_source, expected_rules, expected_errors):
    stylesheet = CSS21Parser().parse_stylesheet(css_source)
    assert len(stylesheet.errors) == len(expected_errors)
    for error, expected in zip(stylesheet.errors, expected_errors):
        assert expected in error.message

    result = [
        (rule.uri, rule.media)
        for rule in stylesheet.statements
        if rule.at_keyword == '@import'
    ]
    assert result == expected_rules


@pytest.mark.parametrize(('css_source', 'expected_rules', 'expected_errors'), [
    (' /* hey */\n', [], []),
    ('@page {}', [(None, [])], []),
    ('@page:first {}', [('first', [])], []),
    ('@page :left{}', [('left', [])], []),
    ('@page\t\n:right {}', [('right', [])], []),
    ('@page :last {}', [], ['invalid @page selector']),
    ('@page : right {}', [], ['invalid @page selector']),
    ('@page table:left {}', [], ['invalid @page selector']),

    ('@page;', [], ['invalid @page rule: missing block']),
    ('@page { a:1; ; b: 2 }',
        [(None, [('a', [('INTEGER', 1)]), ('b', [('INTEGER', 2)])])],
        []),
    ('@page { a:1; c: ; b: 2 }',
        [(None, [('a', [('INTEGER', 1)]), ('b', [('INTEGER', 2)])])],
        ['expected a property value']),
    ('@page { a:1; @top-left {} b: 2 }',
        [(None, [('a', [('INTEGER', 1)]), ('b', [('INTEGER', 2)])])],
        ['unknown at-rule in @page context: @top-left']),
    ('@page { a:1; @top-left {}; b: 2 }',
        [(None, [('a', [('INTEGER', 1)]), ('b', [('INTEGER', 2)])])],
        ['unknown at-rule in @page context: @top-left']),
])
def test_at_page(css_source, expected_rules, expected_errors):
    stylesheet = CSS21Parser().parse_stylesheet(css_source)
    assert len(stylesheet.errors) == len(expected_errors)
    for error, expected in zip(stylesheet.errors, expected_errors):
        assert expected in error.message

    for rule in stylesheet.statements:
        assert rule.at_keyword == '@page'
        assert rule.at_rules == []  # in CSS 2.1
    result = [
        (rule.selector, [
            (decl.name, list(jsonify(decl.value.content)))
            for decl in rule.declarations])
        for rule in stylesheet.statements
    ]
    assert result == expected_rules


@pytest.mark.parametrize(('css_source', 'expected_rules', 'expected_errors'), [
    (' /* hey */\n', [], []),
    ('@media all {}', [(['all'], [])], []),
    ('@media screen, print {}', [(['screen', 'print'], [])], []),
    ('@media all;', [], ['invalid @media rule: missing block']),
    ('@media  {}', [], ['expected media types for @media']),
    ('@media 4 {}', [], ['expected a media type, got INTEGER']),
    ('@media , screen {}', [], ['expected a media type, got DELIM']),
    ('@media screen, {}', [], ['expected a media type']),
    ('@media screen print {}', [], ['expected a comma, got S']),

    ('@media all { @page { a: 1 } @media; @import; foo { a: 1 } }',
        [(['all'], [('foo ', [('a', [('INTEGER', 1)])])])],
        ['@page rule not allowed in @media',
         '@media rule not allowed in @media',
         '@import rule not allowed in @media']),

])
def test_at_media(css_source, expected_rules, expected_errors):
    stylesheet = CSS21Parser().parse_stylesheet(css_source)
    assert len(stylesheet.errors) == len(expected_errors)
    for error, expected in zip(stylesheet.errors, expected_errors):
        assert expected in error.message

    for rule in stylesheet.statements:
        assert rule.at_keyword == '@media'
    result = [
        (rule.media, [
            (sub_rule.selector.as_css, [
                (decl.name, list(jsonify(decl.value.content)))
                for decl in sub_rule.declarations])
            for sub_rule in rule.statements
        ])
        for rule in stylesheet.statements
    ]
    assert result == expected_rules


@pytest.mark.parametrize(('css_source', 'expected_declarations',
                          'expected_errors'), [
    (' /* hey */\n', [], []),

    ('a:1; b:2',
        [('a', [('INTEGER', 1)], None), ('b', [('INTEGER', 2)], None)], []),

    ('a:1 important; b: important',
        [('a', [('INTEGER', 1), ('S', ' '), ('IDENT', 'important')], None),
            ('b', [('IDENT', 'important')], None)],
        []),

    ('a:1 !important; b:2',
        [('a', [('INTEGER', 1)], 'important'), ('b', [('INTEGER', 2)], None)],
        []),

    ('a:1!\t important; b:2',
        [('a', [('INTEGER', 1)], 'important'), ('b', [('INTEGER', 2)], None)],
        []),

    ('a: !important; b:2',
        [('b', [('INTEGER', 2)], None)],
        ['expected a value before !important']),

])
def test_important(css_source, expected_declarations, expected_errors):
    declarations, errors = CSS21Parser().parse_style_attr(css_source)
    assert len(errors) == len(expected_errors)
    for error, expected in zip(errors, expected_errors):
        assert expected in error.message
    result = [(decl.name, list(jsonify(decl.value.content)), decl.priority)
              for decl in declarations]
    assert result == expected_declarations