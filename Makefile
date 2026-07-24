POSTS_DIR = posts
TEMPLATE_DIR = $(POSTS_DIR)/templates
TEMPLATE_HTML5 = $(TEMPLATE_DIR)/template.html5
FLAG = --data-dir . --template $(TEMPLATE_HTML5) --standalone --mathjax
SRC = $(POSTS_DIR)/src
METADATA = $(TEMPLATE_DIR)/metadata.yaml
RSS = atom.xml
SITEMAP = sitemap.xml
PYTHON = uv run

MD = $(shell ls $(SRC) |grep \.md)
HTML = $(MD:%.md=$(POSTS_DIR)/%.html)

# Modification date of a post, taken from the source file's mtime.
LAST_MOD = $$(date -u -r $< +%FT%TZ)

all: $(HTML)

$(POSTS_DIR)/%.html: $(SRC)/%.md $(METADATA) $(TEMPLATE_HTML5)
	@echo Converting $< to $@
	@pandoc $(METADATA) $< -f markdown -t html $(FLAG) --metadata last_modified="$(LAST_MOD)" --metadata path="$@" -o $@

rss: rss_generator.py $(HTML)
	@rm -f $(RSS)
	@echo Generating RSS feed...
	$(PYTHON) ./rss_generator.py
	@echo Done!

sitemap: sitemap_generator.py $(HTML)
	@rm -f ${SITEMAP}
	@echo Generating sitemap...
	$(PYTHON) ./sitemap_generator.py
	@echo done

ga: ga.py $(HTML)
	@echo Updating Google Analytics data
	@$(PYTHON) ./ga.py
	@echo done

sync: all
	@rsync -cavz ./ root@144.202.35.37:/var/www/html --delete

clean:
	@rm $(HTML) $(RSS)


