# -*- coding: utf-8 *-*

# variables used in these templates are either column names from the Mendeley Desktop SQLite db, or defined in Mendeley2bib.openDatabase.convertEntry

bibtemplates = {
    "ConferenceProceedings": """\
        @inproceedings{$citationKey,
            abstract = {$abstract},
            author = {$authors},
            booktitle = {$publication},
            doi = {$doi},
            issn = {$issn},
            isbn = {$isbn},
            keywords = {$keywords},
            mendeley-tags = {$tags},
            month = {$month},
            pages = {$pages},
            publisher = {$publisher},
            title = {{$title}},
            url = {$url},
            year = {$year}
        }}
    """
    ,
    "JournalArticle": """\
        @article{$citationKey,
            abstract = {$abstract},
            author = {$authors},
            journal = {$publication},
            doi = {$doi},
            issn = {$issn},
            isbn = {$isbn},
            keywords = {$keywords},
            mendeley-tags = {$tags},
            month = {$month},
            pages = {$pages},
            publisher = {$publisher},
            title = {{$title}},
            url = {$url},
            volume = {$volume},
            year = {$year}
        }}
    """
    ,
    "Book": """\
        @book{$citationKey,
            author = {$authors},
            editor = {$editors},
            title = {$title},
            publisher = {$publisher},
            year = {$year},
            isbn = {$isbn},
            volume = {$volume},
            address = {$city},
            edition = {$edition},
            month = {$month},
            note = {$note},
            url = {$url},
        }
    """
    ,
    "Patent": """\
        @patent{$citationKey,
            author = {$authors},
            title = {$title},
            number = {$revisionNumber},
            publisher = {$publisher},
            year = {$year},
            doi = {$doi},
            holder = {$owner},
            note = {$note},
            url = {$url},
        }
    """
    ,
    "Thesis": """\
        @thesis{$citationKey,
            author = {$authors},
            title = {$title},
            type = {$userType},
            institution = {$institution},
            department = {$department},
            publisher = {$publisher},
            year = {$year},
            doi = {$doi},
            note = {$note},
            url = {$url},
        }
    """
    ,
    "WebPage": """\
        @misc{$citationKey,
            author = {$authors},
            title = {$title},
            year = {$year},
            doi = {$doi},
            note = {$note},
            howpublished = {\\url{$url}},
        }
    """
}

