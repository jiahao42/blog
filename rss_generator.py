#! /usr/bin/env python3
# -*- coding: utf-8

import os
import arrow

path = './posts/'
html_names = list(filter(lambda x: x[-5:] == '.html', (os.listdir(path))))

rss_preamble = "<?xml version=\"1.0\" encoding=\"UTF-8\" ?>"

rss_head = """
  <feed xmlns="http://www.w3.org/2005/Atom">
  <title>Ground Oddity</title>
  <subtitle>Personal blog of Jiahao Cai</subtitle>
  <link href="http://jujuba.me/"/>
  <link href="http://jujuba.me/atom.xml" rel="self" type="application/atom+xml"/>
  <author>
    <name>Jiahao Cai</name>
  </author>
  <id>http://jujuba.me/</id>
"""
rss_head += "<updated>" + str(arrow.now()) + "</updated>\n"

rss_tail = '</feed>'
rss_body = ''

try: 
    from BeautifulSoup import BeautifulSoup
except ImportError:
    from bs4 import BeautifulSoup

for html_name in html_names:
  print(f'generating rss for {html_name}')
  with open(path + html_name, 'r') as html:
    parsed_html = BeautifulSoup(html.read().encode('utf-8'), "html5lib")
  rss_body += '<entry>'
  title = parsed_html.body.find('h1', attrs={'class':'title'}).text
  rss_body += '<title>' + title + '</title>'

  published = parsed_html.find('meta', attrs={'name':"published"}).get("content")
  rss_body += '<published>' + published + '</published>'

  updated = parsed_html.find('meta', attrs={'name':"last_modified"}).get("content")
  rss_body += '<updated>' + updated + '</updated>'

  url = 'http://jujuba.me/posts/' + html_name
  rss_body += '<link href="' + url + '"/>'
  rss_body += '<id>' + url + '</id>'
  rss_body += '<author> <name>Jiahao Cai</name> </author>'

  parsed_html.find('a', {'id': 'return'}).decompose()
  contents = str(parsed_html.body).replace('<body>', '').replace('</body>', '')
  # rss_body += '<summary type="html">' + '<![CDATA[ ' + contents[0:500] + ' ]]>' + '</summary>'
  rss_body += '<content type="html">' + '<![CDATA[ ' + contents + ' ]]>' + '</content>'
  rss_body += '</entry>'


with open('./atom.xml', 'w') as feed:
  feed.write(rss_preamble)
  feed.write(rss_head)
  feed.write(rss_body)
  feed.write(rss_tail)
