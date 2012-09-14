mendeley2bib
============

Python tool to export a Mendeley Desktop database into a biblatex-compatible .bib file.

BEWARE: This is Python 3, and won't work on Python 2.x! Also, on Windows, it requires pywin32 (http://sourceforge.net/projects/pywin32/) to be installed.

Currently works on Windows, Linux and OSX.

Call with -h or --help to see how to use it.
Your .bib file contents will be output to stdout; use output redirection to bake a .bib file.
Note that the number of entry types supported is severely limited; feel free to add your own templates to bibconverter.py and contribute to the project!
Also, keep in mind to watch your console, as the tool will notify you of any limitations/quirks/warnings.
