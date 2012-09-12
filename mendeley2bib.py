# -*- coding: utf-8 *-*
import os
import sys
import sqlite3
import unicodedata
import latex
import logging
from copy import copy
from textwrap import dedent
from string import Template
from bibtemplates import bibtemplates
from argparse import ArgumentParser

log = logging.getLogger(__name__)

class Mendeley2Bib:
    databases = None
    mendeleyFolder = None

    def __init__(self):
        self.mendeleyFolder = self.getMendeleyFolder()
        self.openDatabase.mendeleyFolder = self.mendeleyFolder

    def getMendeleyFolder(self):
        import platform
        if platform.system() == 'Windows':
            from win32com.shell import shellcon, shell
            hdir = shell.SHGetFolderPath(0, shellcon.CSIDL_LOCAL_APPDATA, 0, 0)
            return os.path.join(hdir, 'Mendeley Ltd', 'Mendeley Desktop')
        else:
            # TODO mac support
            hdir = os.path.expanduser("~")
            hdir = os.path.join(hdir, '.local', 'share', 'data')
            return os.path.join(hdir, 'Mendeley Ltd.', 'Mendeley Desktop')

    def getDatabases(self):
        if not self.databases:
            files = os.listdir(self.mendeleyFolder)
            self.databases = [f[:-24] for f in files if f.endswith('@www.mendeley.com.sqlite')]
        return self.databases

    class openDatabase:
        def __init__(self, db):
            self.db = db

        def __enter__(self):
            self.conn = sqlite3.connect(os.path.join(self.mendeleyFolder, '%s@www.mendeley.com.sqlite' % self.db))
            def dict_factory(cursor, row):
                d = {}
                for idx, col in enumerate(cursor.description):
                    d[col[0]] = row[idx]
                return d
            self.conn.row_factory=dict_factory
            return self

        def __exit__(self, type, value, traceback):
            self.conn.close()

        def fetchEntries(self):
            return self.conn.execute('SELECT * FROM Documents WHERE deletionPending = \'false\';').fetchall()

        def getDocumentContributors(self, entry, type, concat=True):
            authors = self.conn.execute('SELECT * FROM DocumentContributors WHERE contribution=? AND documentId=?', [type, entry['id']]).fetchall()
            return ' and '.join(['%s, %s' % (e['lastName'], e['firstNames']) for e in authors]) if concat else authors

        def convertEntry(self, origEntry, converter):
            entry = copy(origEntry)
            entrytype = entry['type']
        
            authors = self.getDocumentContributors(entry, 'DocumentAuthor', concat=False)
            if not entry['citationKey']:
                if authors and entry['year']:
                    entry['citationKey'] = '%s%s' % (authors[0]['lastName'], entry['year'])
                    if args.writeback_keys:
                        self.conn.execute('UPDATE Documents SET citationKey=? WHERE id=?', [entry['citationKey'], entry['id']])
                        self.conn.commit()
                        log.info('%s entry \'%s\' lacks a citation key, generated as \'%s\' and written to Mendeley db' % (entrytype, entry['title'], entry['citationKey']))
                    else:
                        log.warning('%s entry \'%s\' lacks a citation key, but it has been generated to be \'%s\'. Be careful, as changing the author/year changes this generated key. It\'s probably a good idea to set one in Mendeley Desktop, or use the -k argument.' % (entrytype, entry['title'], entry['citationKey']))
                else:
                    log.warning('%s entry \'%s\' lacks a citation key, and none could be generated because it lacks authors and/or a year! It will be excluded from the .bib file as there is no way to reference it.' % (entrytype, entry['title']))
                    return None
            log.debug('Processing entry \'%s\'' % entry['citationKey'])
            if entrytype in converter:
                entry['authors'] = self.getDocumentContributors(entry, 'DocumentAuthor')
                entry['editors'] = self.getDocumentContributors(entry, 'DocumentEditor')
                kws = self.conn.execute('SELECT * FROM DocumentKeywords WHERE documentId=?', [entry['id']]).fetchall()
                entry['keywords'] = ','.join([kw['keyword'] for kw in kws])
                tags = self.conn.execute('SELECT * FROM DocumentTags WHERE documentId=?', [entry['id']]).fetchall()
                entry['tags'] = ','.join([tag['tag'] for tag in tags])
                url = self.conn.execute('SELECT * FROM DocumentUrls WHERE documentId=? LIMIT 1', [entry['id']]).fetchone()
                entry['url'] = url['url'] if url else ''
                entry['month'] = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'][int(entry['month']-1)] if entry['month'] else '{}'
                entry['pages'] = entry['pages'].replace('-', '--') if entry['pages'] else ''
                if entrytype == 'Thesis' and not entry['userType']:
                    log.warning('Entry \'%s\' is of type \'Thesis\', but requires a field \'type\' not set automatically by Mendeley. Please use the \'Type\' field to specify the type of thesis, e.g. \'Master\'s Thesis\' or \'PhD Thesis\'!' % entry['citationKey'])
                for key in entry:
                    if type(entry[key]) == bytes:
                        entry[key] = entry[key].decode('UTF-8')
                    entry[key] = str(entry[key]).encode('latex').decode('ASCII') if entry[key] else ''
                    
                return Template(converter[entrytype]).substitute(entry)
            else:
                log.warning('No conversion template available for entry type \'%s\'! Entry \'%s\' will not be available in your .bib file.' % (entry['type'], entry['citationKey']))
                return None

if __name__=='__main__':
    if sys.version_info < (3, 0):
        print('This ain\'t gonna work out I\'m afraid; better install Python 3.x!')
        sys.exit(-1)

    m2b = Mendeley2Bib()
    defaultDB = m2b.getDatabases()[0] if len(m2b.getDatabases()) is 1 else None

    argparser = ArgumentParser(description='Convert Mendeley entries to a Biblatex-compatible bib file')
    argparser.add_argument('-d', '--dbfile', metavar='NAME', help='The database to load. Use -l to list all available databases. Required when more than one database is available.', default=defaultDB)
    argparser.add_argument('-l', '--list', dest='list', action='store_const', const=True, default=False, help='In stead of processing a database, list available databases.')
    argparser.add_argument('-k', '--write-keys', dest='writeback_keys', action='store_const', const=True, default=False, help='When an absent citation key is generated, write it back to the Mendeley database. NOTE: this only works when Mendeley Desktop is not running, since it locks its database')
    argparser.add_argument('-v', '--verbose', dest='loglevel', action='store_const', const=logging.DEBUG, default=logging.INFO, help='Set debug level to DEBUG in stead of INFO')
    args = argparser.parse_args()
    
    logging.basicConfig(level=args.loglevel, format='%(levelname)s: %(message)s')

    if args.list:
        print('Available databases:')
        choices = 0
        for db in m2b.getDatabases():
            print('- %s' % db)
            choices += 1
        if choices is 0:
            print('None! Please connect to a Mendeley account first using Mendeley Desktop')
        sys.exit(0)

    if not args.dbfile:
        print('Please specify the database file to use. Choices are:')
        choices = 0
        for db in m2b.getDatabases():
            print('- %s' % db)
            choices += 1
        if choices is 0:
            print('None! Please connect to a Mendeley account first using Mendeley Desktop')
        sys.exit(-1)

    latex.register()

    numConverted = 0

    with m2b.openDatabase(args.dbfile) as db:
        for entry in db.fetchEntries():
            converted = db.convertEntry(entry, bibtemplates)
            if converted:
                print(dedent(converted))
                numConverted += 1

    log.info('Successfully converted %d Mendeley Desktop entries from database %s' % (numConverted, args.dbfile))