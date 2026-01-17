AUTHOR=James Clark
PANDOC=pandoc
OUTPUTS=casictool.1 casictool.1.md

all: $(OUTPUTS)

# roff man page from pandoc markdown
%: %.src.md
	$(PANDOC) -s --metadata=title="$(basename $*)" --metadata=section="$(subst .,,$(suffix $*))" --metadata=author="$(AUTHOR)" -t man -o $@ $<

# GitHub-flavored markdown from roff
%.1.md: %.1
	$(PANDOC) -s -f man -t gfm -o $@ $<

realclean:
	-rm -f $(OUTPUTS)

.PHONY: all realclean
