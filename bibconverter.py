# -*- coding: utf-8 *-*
from mendeley2bib import MendeleyEntryConverter
from textwrap import dedent
import latex
import logging

log = logging.getLogger(__name__)

latex.register()

# A converter that outputs a biblatex-compatible .bib
class BibConverter(MendeleyEntryConverter):
    entryTemplate = dedent("""
        @$entryType{$citationKey,
        $members
        }
    """)
    entryMemberSeparator = ",\n"
    entryMemberTemplate = "    $key = $value"

    def __init__(self, database):
        MendeleyEntryConverter.__init__(self, database)
        # Maps Mendeley types to biblatex entry types
        self.entryTypeMap = {
            "ConferenceProceedings": "inproceedings",
            "JournalArticle": "article",
            "Book": "book",
            "BookSection": "incollection",
            "Patent": "patent",
            "Report": "techreport",
            "Thesis": "thesis",
            "Generic": "misc",
            "WebPage": "misc",
        }
        """ Key-value pairs that will be added to all entries.
            Items may be one of the following:
            - string
                Denotes a column name from the Mendeley database. Output key will be the same as the column name.
            - (string1, string2)
                Maps a Mendeley column name (string2) to an output key (string1)
            - (string, function)
                A function will be called to determine the contents of the output key (string). If the function returns None, it is ommitted from output.
        """
        self.commonEntries = [
            ('author', self.getAuthors),
            'year',
            ('month', self.getMonth),
            ('title', lambda e: '{%s}' % self.processGenericEntry(e['title'])), # title needs an extra pair of {} for some reason
            'isbn',
            'issn',
            'doi',
        ]
        # Type-specific key-value pairs
        self.entryMap = {
            "Book": [
                ('address', 'city'),
                'edition',
                ('editor', self.getEditors),
                'publisher',
                'volume',
                ('url', self.getURL),
            ],
            "BookSection": [
                ('address', 'city'),
                ('booktitle', 'publication'),
                'chapter',
                'edition',
                ('editor', self.getEditors),
                'publisher',
                'volume',
                ('url', self.getURL),
            ],
            "ConferenceProceedings": [
                'abstract',
                'booktitle',
                'keywords',
                ('mendeley-tags', self.getTags),
                ('pages', self.getPages),
                'publisher',
            ],
            "JournalArticle": [
                'abstract',
                ('journal', 'publication'),
                ('keywords', self.getKeywords),
                ('mendeley-tags', 'tags'),
                ('pages', self.getPages),
                'publisher',
                'volume',
            ],
            "Patent": [
                ('holder', 'owner'),
                ('number', 'revisionNumber'),
                'publisher',
            ],
            "Report": [
                'institution',
                ('type', lambda x: self.getUserType('Report', x)),
                ('number', 'seriesNumber'),
                ('address', 'city'),
            ],
            "Thesis": [
                'department',
                ('type', lambda x: self.getUserType('Thesis', x)),
                'institution',
                'publisher',
            ],
            "WebPage": [
                ('howpublished', self.getHowPublishedURL),
            ],
            "Generic": [
                ('type', 'sourceType'),
                ('howpublished', self.getHowPublishedURL),
            ]
        }

    # This function is applied to all string or (string,string) key-value mappings as defined above.
    # NOTE: This function is _NOT_ applied by default to (string,function) mappings!
    def processGenericEntry(self, text):
        return ('{%s}' % str(text).encode('latex').decode('ASCII')) if text else None

    def getConcatDocumentContributors(self, entry, type):
        contributors = self.db.getDocumentContributors(entry, type)
        return ' and '.join(['%s, %s' % (e['lastName'], e['firstNames']) for e in contributors]) if contributors else None

    def getAuthors(self, entry):
        return self.processGenericEntry(self.getConcatDocumentContributors(entry, 'DocumentAuthor'))

    def getEditors(self, entry):
        return self.processGenericEntry(self.getConcatDocumentContributors(entry, 'DocumentEditor'))

    def getMonth(self, entry):
        return ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'][int(entry['month']-1)] if entry['month'] else None

    def getTags(self, entry):
        return self.processGenericEntry(','.join([tag['tag'] for tag in self.db.getTags(entry)]))

    def getPages(self, entry):
        return self.processGenericEntry(entry['pages'].replace('-', '--') if entry['pages'] else None)

    def getKeywords(self, entry):
        return self.processGenericEntry(','.join([kw['keyword'] for kw in self.db.getKeywords(entry)]))

    def getURL(self, entry):
        return self.processGenericEntry(self.db.getURL(entry))

    def getHowPublishedURL(self, entry):
        url = self.db.getURL(entry)
        return ('{\\url{%s}}' % self.processGenericEntry(url)) if url else None

    def getUserType(self, entryType, entry):
        # only defined here to be able to warn the user if it is not present
        if not entry['userType']:
            log.warning('Entry \'%s\' is of type \'%s\', but requires a field \'type\' not set automatically by Mendeley. Please use the \'Type\' field to specify the type of thesis, e.g. \'Master\'s Thesis\' or \'PhD Thesis\'!' % (entry['citationKey'],entryType))
        return self.processGenericEntry(entry['userType'])

