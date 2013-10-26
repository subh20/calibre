#!/usr/bin/env python
# vim:fileencoding=utf-8
from __future__ import (unicode_literals, division, absolute_import,
                        print_function)

__license__ = 'GPL v3'
__copyright__ = '2013, Kovid Goyal <kovid at kovidgoyal.net>'

from lxml import etree
from html5lib.constants import cdataElements, rcdataElements

from calibre.ebooks.oeb.polish.tests.base import BaseTest
from calibre.ebooks.oeb.polish.parsing import parse
from calibre.ebooks.oeb.base import XPath, XHTML_NS, SVG_NS, XLINK_NS
from calibre.ebooks.oeb.parse_utils import html5_parse

def nonvoid_cdata_elements(test, parse_function):
    ''' If self closed version of non-void cdata elements like <title/> are
    present, the HTML5 parsing algorithm treats all following data as CDATA '''
    markup = '''
    <html> <head><{0}/></head> <body id="test"> </html>
    '''
    for tag in cdataElements | rcdataElements:
        for x in (tag, tag.upper(), '\n' + tag, tag + ' id="xxx" '):
            root = parse_function(markup.format(x))
            test.assertEqual(
                len(XPath('//h:body[@id="test"]')(root)), 1,
                'Incorrect parsing for <%s/>, parsed markup:\n' % x + etree.tostring(root))

def namespaces(test, parse_function):
    ae = test.assertEqual
    def match_and_prefix(root, xpath, prefix, err=''):
        matches = XPath(xpath)(root)
        ae(len(matches), 1, err)
        ae(matches[0].prefix, prefix)

    markup = ''' <html xmlns="{xhtml}"><head><body id="test"></html> '''.format(xhtml=XHTML_NS)
    root = parse_function(markup)
    ae(
        len(XPath('//h:body[@id="test"]')(root)), 1,
        'Incorrect parsing, parsed markup:\n' + etree.tostring(root))
    match_and_prefix(root, '//h:body[@id="test"]', None)

    markup = '''
    <html xmlns="{xhtml}"><head><body id="test">
    <svg:svg xmlns:svg="{svg}"><svg:image xmlns:xlink="{xlink}" xlink:href="xxx"/></svg:svg>
    '''.format(xhtml=XHTML_NS, svg=SVG_NS, xlink=XLINK_NS)
    root = parse_function(markup)
    err = 'Incorrect parsing, parsed markup:\n' + etree.tostring(root)
    match_and_prefix(root, '//h:body[@id="test"]', None, err)
    match_and_prefix(root, '//svg:svg', None if parse_function is parse else 'svg', err)
    match_and_prefix(root, '//svg:image[@xl:href]', None if parse_function is parse else 'svg', err)

    markup = '''
    <html xmlns="{xhtml}"><head><body id="test">
    <svg xmlns="{svg}" xmlns:xlink="{xlink}" ><image xlink:href="xxx"/></svg>
    '''.format(xhtml=XHTML_NS, svg=SVG_NS, xlink=XLINK_NS)
    root = parse_function(markup)
    err = 'Incorrect parsing, parsed markup:\n' + etree.tostring(root)
    match_and_prefix(root, '//h:body[@id="test"]', None, err)
    match_and_prefix(root, '//svg:svg', None if parse_function is parse else 'svg', err)
    match_and_prefix(root, '//svg:image[@xl:href]', None if parse_function is parse else 'svg', err)

    markup = '<html><body><svg><image xlink:href="xxx"></svg>'
    root = parse_function(markup)
    err = 'Namespaces not created, parsed markup:\n' + etree.tostring(root)
    match_and_prefix(root, '//svg:svg', None if parse_function is parse else 'svg', err)
    match_and_prefix(root, '//svg:image[@xl:href]', None if parse_function is parse else 'svg', err)
    if parse_function is parse:
        image = XPath('//svg:image')(root)[0]
        ae(image.nsmap, {'xlink':XLINK_NS, None:SVG_NS})

    root = parse_function('<html id="a"><p><html xmlns:x="y" lang="en"><p>')
    err = 'Multiple HTML tags not handled, parsed markup:\n' + etree.tostring(root)
    match_and_prefix(root, '//h:html', None, err)
    match_and_prefix(root, '//h:html[@lang]', None, err)
    match_and_prefix(root, '//h:html[@id]', None, err)

    if parse_function is not html5_parse:
        markup = '<html:html xmlns:html="{html}" id="a"><html:body><html:p></html:p></html:body></html>'.format(html=XHTML_NS)
        root = parse_function(markup)
        err = 'HTML namespace prefixed, parsed markup:\n' + etree.tostring(root)
        match_and_prefix(root, '//h:html', None, err)

    markup = '<html><body><ns1:tag1 xmlns:ns1="NS"><ns2:tag2 xmlns:ns2="NS" ns1:id="test"/><ns1:tag3 xmlns:ns1="NS2" ns1:id="test"/></ns1:tag1>'
    root = parse_function(markup)
    err = 'Arbitrary namespaces not preserved, parsed markup:\n' + etree.tostring(root)
    def xpath(expr):
        return etree.XPath(expr, namespaces={'ns1':'NS', 'ns2':'NS2'})(root)
    ae(len(xpath('//ns1:tag1')), 1, err)
    ae(len(xpath('//ns1:tag2')), 1, err)
    ae(len(xpath('//ns2:tag3')), 1, err)
    ae(len(xpath('//ns1:tag2[@ns1:id="test"]')), 1, err)
    ae(len(xpath('//ns2:tag3[@ns2:id="test"]')), 1, err)
    for tag in root.iter():
        if 'NS' in tag.tag:
            ae('ns1', tag.prefix)

    markup = '<html xml:lang="en"><body><p lang="de"><p xml:lang="es"><p lang="en" xml:lang="de">'
    root = parse_function(markup)
    err = 'xml:lang not converted to lang, parsed markup:\n' + etree.tostring(root)
    ae(len(root.xpath('//*[@lang="en"]')), 2, err)
    ae(len(root.xpath('//*[@lang="de"]')), 1, err)
    ae(len(root.xpath('//*[@lang="es"]')), 1, err)
    ae(len(XPath('//*[@xml:lang]')(root)), 0, err)

def space_characters(test, parse_function):
    markup = '<html><p>\u000c</p>'
    root = parse_function(markup)
    err = 'form feed character not converted, parsed markup:\n' + etree.tostring(root)
    test.assertNotIn('\u000c', root.xpath('//*[local-name()="p"]')[0].text, err)
    markup = '<html><p>a\u000b\u000c</p>'
    root = parse_function(markup)  # Should strip non XML safe control code \u000b
    test.assertNotIn('\u000b', root.xpath('//*[local-name()="p"]')[0].text, err)
    test.assertNotIn('\u000c', root.xpath('//*[local-name()="p"]')[0].text, err)

def case_insensitive_element_names(test, parse_function):
    markup = '<HTML><P> </p>'
    root = parse_function(markup)
    err = 'case sensitive parsing, parsed markup:\n' + etree.tostring(root)
    test.assertEqual(len(XPath('//h:p')(root)), 1, err)

def entities(test, parse_function):
    markup = '<html><p>&nbsp;&apos;</p>'
    root = parse_function(markup)
    err = 'Entities not handled, parsed markup:\n' + etree.tostring(root)
    test.assertEqual('\xa0\'', root.xpath('//*[local-name()="p"]')[0].text, err)

basic_checks = (nonvoid_cdata_elements, namespaces, space_characters, case_insensitive_element_names, entities)

class ParsingTests(BaseTest):

    def test_conversion_parser(self):
        ' Test parsing with the HTML5 parser used for conversion '
        for test in basic_checks:
            test(self, html5_parse)

    def test_polish_parser(self):
        ' Test parsing with the HTML5 parser used for polishing '
        for test in basic_checks:
            test(self, parse)

        root = parse('<html><p><svg><image /><b></svg>&nbsp;\n<b>xxx', discard_namespaces=True)
        self.assertFalse(root.xpath('//svg/b'), 'The <b> was not moved out of <svg>')