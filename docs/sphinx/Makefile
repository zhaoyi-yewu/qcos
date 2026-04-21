# Makefile for Sphinx documentation
#

SPHINXOPTS    = -T $(SPHINX_FAIL_ON_WARNING)
SPHINXBUILD   = sphinx-build
SOURCEDIR     = source
PAPER         =
BUILDDIR      = dist

# Internal variables.
PAPEROPT_a4     = -D latex_paper_size=a4
PAPEROPT_letter = -D latex_paper_size=letter
ALLSPHINXOPTS   = -d $(BUILDDIR)/doctrees $(PAPEROPT_$(PAPER)) $(SPHINXOPTS)

.PHONY: help clean html dirhtml singlehtml dist-html latex latexpdf docx text man

help:
	@echo "Please use \`make <target>' where <target> is one of"
	@echo "  html       to make standalone HTML files"
	@echo "  dirhtml    to make HTML files named index.html in directories"
	@echo "  singlehtml to make a single large HTML file"
	@echo "  chm        to make chm file"
	@echo "  latex      to make LaTeX files, you can set PAPER=a4 or PAPER=letter"
	@echo "  latexpdf   to make LaTeX files and run them through pdflatex"
	@echo "  docx       to make docx files through docxbuilder"
	@echo "  text       to make text files"
	@echo "  man        to make manual pages"

clean:
	-rm -rf $(BUILDDIR)/*
	-rm -rf $(SOURCEDIR)/api

html:
	$(SPHINXBUILD) -b html $(ALLSPHINXOPTS) ${SOURCEDIR} $(BUILDDIR)/html
	@echo
	@echo "Build finished. The HTML pages are in $(BUILDDIR)/html."

dirhtml:
	$(SPHINXBUILD) -b dirhtml $(ALLSPHINXOPTS) ${SOURCEDIR} $(BUILDDIR)/dirhtml
	@echo
	@echo "Build finished. The HTML pages are in $(BUILDDIR)/dirhtml."

singlehtml:
	$(SPHINXBUILD) -b singlehtml $(ALLSPHINXOPTS) ${SOURCEDIR} $(BUILDDIR)/singlehtml
	@echo
	@echo "Build finished. The HTML page is in $(BUILDDIR)/singlehtml."

chm:
	$(SPHINXBUILD) -b htmlhelp $(ALLSPHINXOPTS) ${SOURCEDIR} $(BUILDDIR)/chm_src
	@echo
	@echo "Build finished. The CHM file is in $(BUILDDIR)/chm."

latex:
	@rm -rf $(BUILDDIR)/latex
	$(SPHINXBUILD) -b latex $(ALLSPHINXOPTS) ${SOURCEDIR} $(BUILDDIR)/latex
	@echo
	@echo "Build finished; the LaTeX files are in $(BUILDDIR)/latex."
	@echo "Run \`make' in that directory to run these through (pdf)latex" \
          "(use \`make latexpdf' here to do that automatically)."

latexpdf:
	@rm -rf $(BUILDDIR)/latex
	$(SPHINXBUILD) -b latex $(ALLSPHINXOPTS) ${SOURCEDIR} $(BUILDDIR)/latex
	@echo "Running LaTeX files through pdflatex..."
	make -C $(BUILDDIR)/latex all-pdf
	@echo "pdflatex finished; the PDF files are in $(BUILDDIR)/latex."

docx:
	@rm -rf $(BUILDDIR)/docx
	$(SPHINXBUILD) -b docx $(ALLSPHINXOPTS) ${SOURCEDIR} $(BUILDDIR)/docx
	@echo
	@echo "Build finished. The docx file is in $(BUILDDIR)/docx."

text:
	@echo $(SPHINXBUILD) -b text $(ALLSPHINXOPTS) ${SOURCEDIR} $(BUILDDIR)/text
	@echo
	@echo "Build finished. The text files are in $(BUILDDIR)/text."

man:
	$(SPHINXBUILD) -b man $(ALLSPHINXOPTS) ${SOURCEDIR} $(BUILDDIR)/man
	@echo
	@echo "Build finished. The manual pages are in $(BUILDDIR)/man."
