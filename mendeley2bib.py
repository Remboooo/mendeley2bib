# -*- coding: utf-8 *-*
from __future__ import unicode_literals
import os
import sys
import sqlite3
import unicodedata
import latex
import logging
from copy import copy
from string import Template
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
            hdir = os.path.join(hdir, 'Mendeley Ltd', 'Mendeley Desktop')
        elif platform.system() == 'Darwin':
            hdir = os.path.expanduser("~/Library/Application Support/Mendeley Desktop")
        else:
            hdir = os.path.expanduser("~/.local/share/data/Mendeley Ltd./Mendeley Desktop")
        return hdir

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

        def getEntries(self, folder=None, group=None, onlyFavourites=False, writebackKeys=False):
            query = 'SELECT * FROM Documents AS d WHERE deletionPending != \'true\''
            params = []
            if folder is not None:
                if folder == 0:
                    query = '%s AND d.id NOT IN (SELECT documentID FROM DocumentFolders)' % query
                else:
                    query = '%s AND d.id IN (SELECT documentID FROM DocumentFolders AS df WHERE df.folderId = ?)' % query
                    params.append(folder)
            if group is not None:
                query = '%s AND d.id IN (SELECT documentID FROM RemoteDocuments AS rd WHERE rd.groupId = ?)' % query
                params.append(group)
            if onlyFavourites:
                query = '%s AND d.favourite = \'true\'' % query
            query = '%s;' % query
            entries = self.conn.execute(query, params).fetchall()
            for entry in entries:
                authors = self.getDocumentContributors(entry, 'DocumentAuthor')
                entrytype = entry['type']
                if not entry['citationKey']:
                    if authors and entry['year']:
                        entry['citationKey'] = '%s%s' % (authors[0]['lastName'], entry['year'])
                        if writebackKeys:
                            self.conn.execute('UPDATE Documents SET citationKey=? WHERE id=?', [entry['citationKey'], entry['id']])
                            self.conn.commit()
                            log.info('%s entry \'%s\' lacks a citation key, generated as \'%s\' and written to Mendeley db' % (entrytype, entry['title'], entry['citationKey']))
                        else:
                            log.warning('%s entry \'%s\' lacks a citation key, but it has been generated to be \'%s\'. Be careful, as changing the author/year changes this generated key. Set one in Mendeley Desktop (quickest way: ctrl+a ctrl+k), or use the -k argument.' % (entrytype, entry['title'], entry['citationKey']))
                    else:
                        log.warning('%s entry \'%s\' lacks a citation key, and none could be generated because it lacks authors and/or a year! It will be excluded from the .bib file as there is no way to reference it.' % (entrytype, entry['title']))
                        return None
            return [ entry for entry in entries if entry['citationKey'] ]

        def getFolders(self):
            folders = {}
            rows = self.conn.execute('SELECT * FROM Folders;').fetchall()
            for row in rows:
                folders[row['id']] = row
            names = {0: '/'}
            def getFolderName(index, rows):
                row = rows[index]
                parent = getFolderName(row['parentId'], rows) if row['parentId'] > 0 else ''
                return '%s/%s' % (parent, row['name'])
            for (id, folder) in folders.items():
                names[id] = getFolderName(id, folders)
            return names
            
        def getGroups(self):
            rows = self.conn.execute('SELECT * FROM Groups WHERE id != 0;').fetchall()
            names = {0: '<no group>'}
            for row in rows:
                names[row['id']] = row['name']
            return names

        def getFolderID(self, identifier):
            if identifier.isdigit():
                matches = lambda id, item: int(id) == int(item[0])
            else:
                matches = lambda id, item: id == item[1]
            for folder in self.getFolders().items():
                if matches(identifier, folder):
                    return folder[0]
            return None
            
        def getGroupID(self, identifier):
            if identifier.isdigit():
                matches = lambda id, item: int(id) == int(item[0])
            else:
                matches = lambda id, item: id == item[1]
            for group in self.getGroups().items():
                if matches(identifier, group):
                    return group[0]
            return None

        def getDocumentContributors(self, entry, type):
            return self.conn.execute('SELECT * FROM DocumentContributors WHERE contribution=? AND documentId=?', [type, entry['id']]).fetchall()

        def getTags(self, entry):
            return self.conn.execute('SELECT * FROM DocumentTags WHERE documentId=?', [entry['id']]).fetchall()

        def getKeywords(self, entry):
            return self.conn.execute('SELECT * FROM DocumentKeywords WHERE documentId=?', [entry['id']]).fetchall()

        def getURL(self, entry):
            url = self.conn.execute('SELECT * FROM DocumentUrls WHERE documentId=? LIMIT 1', [entry['id']]).fetchone()
            return self.fixString(url['url']) if url else None

        def getURLs(self, entry):
            urls = self.conn.execute('SELECT * FROM DocumentUrls WHERE documentId=?', [entry['id']]).fetchall()
            return [self.fixString(url['url']) for url in urls] if urls else []

        def fixString(self, input):
            if not isinstance(input, str):
                return input.decode("utf-8")
            return input

"""
'Abstract' class which should be extended by all converter classes to convert a list of entries into an output string.
Has access to an opened Mendeley2Bib.openDatabase class.
"""
class MendeleyEntryConverter:
    db = None

    def __init__(self, database):
        self.db = database
        self.entryTemplate = Template(self.entryTemplate)
        self.entryMemberTemplate = Template(self.entryMemberTemplate)

    def convertEntries(self, entryset):
        entries = [self.convertEntry(entry) for entry in entryset]
        count = sum([(1 if entry else 0) for entry in entries])
        output = ''.join([(entry if entry else '') for entry in entries ])
        return (count, output)

    def buildEntry(self, entry, entryType, members):
        entryMembers = self.entryMemberSeparator.join([self.entryMemberTemplate.substitute({'key': key, 'value': value}) for (key, value) in members])
        return self.entryTemplate.substitute(dict(list(entry.items()) + [('entryType', entryType), ('members', entryMembers)]))

    def convertEntry(self, origEntry):
        entry = copy(origEntry) # make sure the original entry is not modified
        entrytype = entry['type']
        citationKey = entry['citationKey']
        log.debug('Processing entry \'%s\'' % citationKey)
        if not entrytype in self.entryTypeMap:
            log.warning('No conversion available for entry type \'%s\'! Entry \'%s\' will not be available in your .bib file.' % (entry['type'], citationKey))
            return None
        outputEntryType = self.entryTypeMap[entrytype]
        entries = copy(self.commonEntries)
        if entrytype in self.entryMap:
            entries.extend(self.entryMap[entrytype])
        outputEntries = []
        for e in entries:
            raw = None
            key = None
            value = None
            if isinstance(e, tuple):
                key = e[0]
                if isinstance(e[1], str):
                    # mapped simply to another variable
                    if e[1]  in entry:
                        raw = entry[e[1]]
                        if type(raw) == bytes:
                            raw = raw.decode('UTF-8')
                    value = self.processGenericEntry(raw)
                else:
                    # mapped to a function (we hope)
                    value = e[1](entry)
            else:
                # 1-to-1 relation
                key = e
                if e in entry:
                    raw = entry[key]
                    if type(raw) == bytes:
                        raw = raw.decode('UTF-8')
                value = self.processGenericEntry(raw)
            if value is not None:
                outputEntries.append((key, value))
        return self.buildEntry(entry, outputEntryType, outputEntries)


if __name__=='__main__':
    if sys.version_info < (2, 6):
        print('This ain\'t gonna work out I\'m afraid; better install Python 2.6+!')
        sys.exit(-1)

    m2b = Mendeley2Bib()
    defaultDB = m2b.getDatabases()[0] if len(m2b.getDatabases()) is 1 else None

    argparser = ArgumentParser(description='Convert Mendeley entries to a Biblatex-compatible bib file')
    argparser.add_argument('-d', '--dbfile', metavar='NAME', help='The database to load. Use -l to list all available databases. Required when more than one database is available.', default=defaultDB)
    argparser.add_argument('-f', '--folder', metavar='FOLDER', help='The folder to process entries from. By default all folders are traversed. Use -lf to see available folders. May be either given as ID or name; when the argument is numeric, it is assumed to be the ID.', default=None)
    argparser.add_argument('-g', '--group', metavar='GROUP', help='The group to process entries from. By default all groups are traversed. Use -lg to see available groups. May be either given as ID or name; when the argument is numeric, it is assumed to be the ID.', default=None)
    argparser.add_argument('-s', '--starred', dest='onlyFavourites', action='store_const', const=True, default=False, help='Only process starred (favourite) items')
    
    argparser.add_argument('-l', '--list', dest='list', action='store_const', const=True, default=False, help='In stead of processing a database, list available databases.')
    argparser.add_argument('-lf', '--list-folders', dest='listfolders', action='store_const', const=True, default=False, help='Just list all available Mendeley folders')
    argparser.add_argument('-lg', '--list-groups', dest='listgroups', action='store_const', const=True, default=False, help='Just list all available Mendeley groups')
    
    argparser.add_argument('-k', '--write-keys', dest='writebackKeys', action='store_const', const=True, default=False, help='When an absent citation key is generated, write it back to the Mendeley database. NOTE: this only works when Mendeley Desktop is not running, since it locks its database')
    argparser.add_argument('-v', '--verbose', dest='loglevel', action='store_const', const=logging.DEBUG, default=logging.INFO, help='Set debug level to DEBUG in stead of INFO')
    args = argparser.parse_args()

    logging.basicConfig(level=args.loglevel, format='\n%(levelname)s: %(message)s')

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

    if args.listfolders:
        with m2b.openDatabase(args.dbfile) as db:
            print('Available Mendeley folders:')
            for (id, folder) in sorted(db.getFolders().items(), key=lambda x: x[1]):
                print('%d: %s' % (id, folder))
            sys.exit(0)
            
    if args.listgroups:
        with m2b.openDatabase(args.dbfile) as db:
            print('Available Mendeley groups:')
            for (id, group) in sorted(db.getGroups().items(), key=lambda x: x[1]):
                print('%d: %s' % (id, group))
            sys.exit(0)

    numConverted = 0

    with m2b.openDatabase(args.dbfile) as db:
        from bibconverter import BibConverter
        folderID = None
        if args.folder:
            folderID = db.getFolderID(args.folder)
            if folderID is None:
                log.error('Folder \'%s\' not found! Use -lf to list available folders.' % args.folder)
                sys.exit(-1)
        groupID = None
        if args.group:
            groupID = db.getGroupID(args.group)
            if groupID is None:
                log.error('Group \'%s\' not found! Use -lg to list available groups.' % args.group)
                sys.exit(-1)
        (numConverted, output) = BibConverter(db).convertEntries(db.getEntries(folder=folderID, group=groupID, onlyFavourites=args.onlyFavourites, writebackKeys=args.writebackKeys))
        print(output)

    log.info('Successfully converted %d Mendeley Desktop entries from database %s' % (numConverted, args.dbfile))
