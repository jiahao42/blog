#! /usr/bin/env python3
# -*- coding: utf-8

import os
import arrow

path = 'posts/'
html_names = list(filter(lambda x: x[-5:] == '.html', (os.listdir(path))))

url = 'http://idle.systems/'

sitemap_preamble = """<?xml version="1.0" encoding="UTF-8"?>
<urlset
      xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
      xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
      xsi:schemaLocation="http://www.sitemaps.org/schemas/sitemap/0.9
            http://www.sitemaps.org/schemas/sitemap/0.9/sitemap.xsd">
"""

sitemap_body = """
<url>
  <loc>http://idle.systems/</loc>
  <priority>1.00</priority>
</url>
<url>
  <loc>http://idle.systems/about.html</loc>
  <priority>0.80</priority>
</url>
"""

try: 
    from BeautifulSoup import BeautifulSoup
except ImportError:
    from bs4 import BeautifulSoup

for html_name in html_names:
  print(f'generating info for {html_name}')
  with open(path + html_name, 'r') as html:
    parsed_html = BeautifulSoup(html.read().encode('utf-8'), "html5lib")
  
  entry = []
  entry.append('<url>')
  entry.append('\t<loc>' + url + path + html_name + '</loc>')
  lastmod = parsed_html.find('meta', attrs={'name':"last_modified"}).get("content")
  entry.append('\t<lastmod>' + lastmod + '</lastmod>')
  entry.append('\t<priority>0.80</priority>')
  entry.append('</url>')
  sitemap_body += '\n'.join(entry)

sitemap_body += '</urlset>' 

with open('./sitemap.xml', 'w') as feed:
  feed.write(sitemap_preamble)
  feed.write(sitemap_body)
