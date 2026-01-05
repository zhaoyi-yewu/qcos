# Makefile for Sphinx documentation
#

SPHINXOPTS    = -T -j auto $(SPHINX_FAIL_ON_WARNING)
SPHINXBUILD   = sphinx-build
SOURCEDIR     = source
PAPER         =
BUILDDIR      = dist

# Internal variables.
PAPEROPT_a4     = -D latex_paper_size=a4
PAPEROPT_letter = -D latex_paper_size=letter
ALLSPHINXOPTS   = -d $(BUILDDIR)/doctrees $(PAPEROPT_$(PAPER)) $(SPHINXOPTS)

.PHONY: help clean html dirhtml singlehtml dist-html latex latexpdf text man

help:
	@echo "Please use \`make <target>' where <target> is one of"
	@echo "  html       to make standalone HTML files"
	@echo "  dirhtml    to make HTML files named index.html in directories"
	@echo "  singlehtml to make a single large HTML file"
	@echo "  latex      to make LaTeX files, you can set PAPER=a4 or PAPER=letter"
	@echo "  latexpdf   to make LaTeX files and run them through pdflatex"
	@echo "  text       to make text files"
	@echo "  man        to make manual pages"

clean:
	-rm -rf $(BUILDDIR)/*

html:
	$(SPHINXBUILD) -b html -t html $(ALLSPHINXOPTS) ${SOURCEDIR} $(BUILDDIR)/html
	@echo
	@echo "Build finished. The HTML pages are in $(BUILDDIR)/html."

dirhtml:
	$(SPHINXBUILD) -b dirhtml -t dirhtml $(ALLSPHINXOPTS) ${SOURCEDIR} $(BUILDDIR)/dirhtml
	@echo
	@echo "Build finished. The HTML pages are in $(BUILDDIR)/dirhtml."

singlehtml:
	$(SPHINXBUILD) -b singlehtml -t singlehtml $(ALLSPHINXOPTS) ${SOURCEDIR} $(BUILDDIR)/singlehtml
	@echo
	@echo "Build finished. The HTML page is in $(BUILDDIR)/singlehtml."

chm:
	$(SPHINXBUILD) -b htmlhelp -t chm $(ALLSPHINXOPTS) ${SOURCEDIR} $(BUILDDIR)/chm_src
	@echo
	@echo "Build finished. The CHM page is in $(BUILDDIR)/chm."

latex:
	@rm -rf $(BUILDDIR)/latex
	$(SPHINXBUILD) -b latex -t latex $(ALLSPHINXOPTS) ${SOURCEDIR} $(BUILDDIR)/latex
	# cp texinputs/* $(BUILDDIR)/latex/
	@echo
	@echo "Build finished; the LaTeX files are in $(BUILDDIR)/latex."
	@echo "Run \`make' in that directory to run these through (pdf)latex" \
          "(use \`make latexpdf' here to do that automatically)."

latexpdf:
	@rm -rf $(BUILDDIR)/latex
	$(SPHINXBUILD) -b latex -t latexpdf $(ALLSPHINXOPTS) ${SOURCEDIR} $(BUILDDIR)/latex
	# cp texinputs/* $(BUILDDIR)/latex/
	@echo "Running LaTeX files through pdflatex..."
	make -C $(BUILDDIR)/latex all-pdf
	@echo "pdflatex finished; the PDF files are in $(BUILDDIR)/latex."

text:
	@echo $(SPHINXBUILD) -b text -t text $(ALLSPHINXOPTS) ${SOURCEDIR} $(BUILDDIR)/text
	@echo
	@echo "Build finished. The text files are in $(BUILDDIR)/text."

man:
	$(SPHINXBUILD) -b man -t man $(ALLSPHINXOPTS) ${SOURCEDIR} $(BUILDDIR)/man
	@echo
	@echo "Build finished. The manual pages are in $(BUILDDIR)/man."
