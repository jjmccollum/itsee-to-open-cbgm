import argparse
import re
from lxml import etree as et

"""
XML namespaces
"""
xml_ns = 'http://www.w3.org/XML/1998/namespace'
tei_ns = 'http://www.tei-c.org/ns/1.0'

"""
Book index to SBL book abbreviation Dictionary
"""
books_by_n = {
    'B01': 'Matt',
    'B02': 'Mark',
    'B03': 'Luke',
    'B04': 'John', 
    'B05': 'Acts',
    'B06': 'Rom',
    'B07': '1 Cor',
    'B08': '2 Cor', 
    'B09': 'Gal',
    'B10': 'Eph',
    'B11': 'Phil',
    'B12': 'Col',
    'B13': '1 Thess',
    'B14': '2 Thess',
    'B15': '1 Tim',
    'B16': '2 Tim',
    'B17': 'Titus',
    'B18': 'Phlm',
    'B19': 'Heb',
    'B20': 'Jas', 
    'B21': '1 Pet',
    'B22': '2 Pet', 
    'B23': '1 John',
    'B24': '2 John', 
    'B25': '3 John', 
    'B26': 'Jude',
    'B27': 'Rev'
}

"""
Strips the input XML of every <app> element without "from" and "to" elements 
(i.e, superfluous apparatus elements used to describe which witnesses are lacunose for entire verses).
"""
def strip_unitless_apps(xml):
    for app in xml.xpath('//tei:app[not(@from) and not(@to)]', namespaces={'tei': tei_ns}):
        app.getparent().remove(app)
    return
        
"""
Strips the input XML of all <wit> elements.
(These elements are not needed, as the "wit" attribute of their parent <rdg> element 
contains the same information.)
"""
def strip_wit_subelements(xml):
    for wit in xml.xpath('//tei:wit', namespaces={'tei': tei_ns}):
        wit.getparent().remove(wit)
    return

"""
Converts escaped Unicode character codes for combining underdots to the corresponding characters.
"""
def unescape_underdots(xml):
    for rdg in xml.xpath('//tei:lem|//tei:rdg', namespaces={'tei': tei_ns}):
        if rdg.text is not None and '&#803;' in rdg.text:
            rdg.text = rdg.text.replace('&#803;', '\u0323')
    return

"""
Strips the text from all <lem> and <rdg> elements in the input XML that have type="om".
"""
def strip_om_text(xml):
    for rdg in xml.xpath('//tei:lem[@type="om"]|//tei:rdg[@type="om"]', namespaces={'tei': tei_ns}):
        rdg.text = None
    return

"""
Replaces <app> elements having only one reading in the input XML with <seg> elements containing that reading.
"""
def sub_segs_for_apps(xml):
    for app in xml.xpath('//tei:app', namespaces={'tei': tei_ns}):
        rdgs = app.xpath('tei:rdg', namespaces={'tei': tei_ns})
        if len(rdgs) == 1:
            seg = et.Element('seg', nsmap={None: tei_ns, 'xml': xml_ns})
            seg.text = rdgs[0].text
            app.getparent().replace(app, seg)
    return

"""
Under each <app> element in the input XML, 
adds a <note> element containing a variation unit label, 
a default connectivity value, and a local stemma without edges.
"""
def add_app_notes(xml):
    for app in xml.xpath('//tei:app', namespaces={'tei': tei_ns}):
        #First, get the "n", "from", and "to" attributes of this apparatus:
        app_n = app.get('n')
        app_from = app.get('from')
        app_to = app.get('to')
        #Then get a List of its reading numbers:
        rdg_ids = []
        for rdg in app.xpath('tei:rdg', namespaces={'tei': tei_ns}):
            if rdg.get('n') is not None:
                rdg_ids.append(rdg.get('n'))
        #Add a <note> element as the last child of the <app> element:
        note = et.Element('note', nsmap={None: tei_ns, 'xml': xml_ns})
        app.append(note)
        #Then add a <label> element under the note, if one can be constructed from the attributes of the apparatus:
        match = re.match('(B\d+)(K\d+)(V\d+)', app_n)
        if match is not None:
            book_n = match.groups()[0]
            chapter_n = match.groups()[1]
            verse_n = match.groups()[2]
            label_text = books_by_n[book_n] + ' ' + chapter_n[1:] + ':' + verse_n[1:] 
            if app_from is not None:
                label_text += '/' + app_from
            if app_to is not None and app_to != app_from:
                label_text += '-' + app_to
            label = et.Element('label', nsmap={None: tei_ns, 'xml': xml_ns})
            label.text = label_text
            note.append(label)
        #Then add a <fs> element under the note:
        fs = et.Element('fs', nsmap={None: tei_ns, 'xml': xml_ns})
        note.append(fs)
        #Then add an <f> element for the "connectivity" feature under the feature set:
        f = et.Element('f', nsmap={None: tei_ns, 'xml': xml_ns})
        f.set('name', 'connectivity')
        fs.append(f)
        #Then add a <numeric> element under the feature with the default connectivity value:
        numeric = et.Element('numeric', nsmap={None: tei_ns, 'xml': xml_ns})
        numeric.set('value', '10')
        f.append(numeric)
        #Then add a <graph> element under the note:
        graph = et.Element('graph', nsmap={None: tei_ns, 'xml': xml_ns})
        graph.set('type', 'directed')
        note.append(graph)
        #Then, add a <node> element for each reading under the graph:
        for rdg_id in rdg_ids:
            node = et.Element('node', nsmap={None: tei_ns, 'xml': xml_ns})
            node.set('n', rdg_id)
            graph.append(node)
    return

"""
Updates the "n" attribute of all <app> elements in the input XML to reflect its "from" and "to" unit indices
and removes the "from" and "to" unit indices.
"""
def update_app_n(xml):
    for app in xml.xpath('//tei:app', namespaces={'tei': tei_ns}):
        #First, get the "n", "from", and "to" attributes of this apparatus:
        app_n = app.get('n')
        app_from = app.get('from')
        app_to = app.get('to')
        #Then update the "n" attribute:
        new_app_n = app_n + 'U' + app_from
        if app_to != app_from:
            new_app_n += '-' + app_to
        app.set('n', new_app_n)
        #Then remove the "from" and "to" attributes:
        app.attrib.pop('from')
        app.attrib.pop('to')
    return

"""
Returns a List of all witness IDs encountered in the input XML tree.
"""
def get_wits(xml):
    wits = []
    distinct_wits = set()
    for rdg in xml.xpath('//tei:rdg', namespaces={'tei': tei_ns}):
        for wit in rdg.get('wit').split():
            #Strip any trailing asterisks or "V"s (for et videtur):
            wit_str = str(wit)
            if wit_str.endswith('*') or wit_str.endswith('V'):
                wit_str = wit_str[:-1]
            if wit_str not in distinct_wits:
                distinct_wits.add(wit_str)
                wits.append(wit_str)
    return wits

"""
Adds a <teiHeader> with appropriate subelements as the first child of the input XML's <TEI> element.
The <listWit> element in particular is needed for the open-cbgm library.
"""
def add_tei_header(xml):
    #Get a List of witness sigla first:
    wits = get_wits(xml)
    #Get the <TEI> element:
    TEI = xml.xpath('//tei:TEI', namespaces={'tei': tei_ns})[0]
    #Append a <teiHeader> element to it:
    teiHeader = et.Element('teiHeader', nsmap={None: tei_ns, 'xml': xml_ns})
    TEI.insert(0, teiHeader)
    #Append a <sourceDesc> element to the teiHeader:
    sourceDesc = et.Element('sourceDesc', nsmap={None: tei_ns, 'xml': xml_ns})
    teiHeader.append(sourceDesc)
    #Append a <listWit> element to the sourceDesc:
    listWit = et.Element('listWit', nsmap={None: tei_ns, 'xml': xml_ns})
    sourceDesc.append(listWit)
    #Append a <witness> element for each witness we have to the listWit:
    for wit in wits:
        witness = et.Element('witness', nsmap={None: tei_ns, 'xml': xml_ns})
        witness.set('n', wit)
        listWit.append(witness)
    return

"""
Main entry point to the script. Parses command-line arguments and calls the core functions.
"""
def main():
    parser = argparse.ArgumentParser(description='''
    Convert TEI XML generated by the ITSEE Collation Editor 
    to TEI XML that can be consumed by the open-cbgm library.
    Essentially, this adds a TEI header with a witness list, 
    removes unnecessary notation for omissions and superfluous <wit> elements,
    and adds local stemmata without edges.
    ''')
    parser.add_argument('-o', metavar='output', type=str, help='Output file address (the default will be the input file base, suffixed with _opencbgm).')
    parser.add_argument('input', type=str, help='TEI XML input file to convert.')
    args = parser.parse_args()
    #Parse the I/O arguments:
    input_addr = args.input
    output_addr = args.o if args.o is not None else input_addr.replace('.xml', '_opencbgm.xml')
    #Read and modify the XML:
    xml = et.parse(input_addr)
    strip_unitless_apps(xml)
    strip_wit_subelements(xml)
    unescape_underdots(xml)
    strip_om_text(xml)
    sub_segs_for_apps(xml)
    add_app_notes(xml)
    update_app_n(xml)
    add_tei_header(xml)
    #Then write it to the output address:
    xml.write(output_addr, encoding='utf-8', xml_declaration=True, pretty_print=True)
    exit(0)

if __name__=="__main__":
    main()