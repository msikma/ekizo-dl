#!/usr/bin/env python3

import os
import sys
import re
import subprocess
import urllib.request
import time
import json
import html as htmlmodule
import urllib.parse
from pprint import pprint


def mandarake_search_url(search):
  return 'https://ekizo.mandarake.co.jp/auction/item/itemsListJa.html?t=0&q={}'.format(urllib.parse.quote(search))


def mandarake_shop_search_url(search):
  return 'https://order.mandarake.co.jp/order/listPage/list?categoryCode={}&keyword={}'.format(search[1], urllib.parse.quote(search[0]))


def get_url_base(url):
  return '/'.join(url.split('/')[:-1]) + '/'


def get_shop_url_base(url):
  return '/'.join(url.split('/')[:3]) + '/'


def load_json(file):
  with open(file) as f:
    data = json.load(f)
  return data


def ensure_dir(dir):
  if not os.path.exists(dir):
    os.makedirs(dir)


def get_search_data():
  path = os.path.expanduser('~/.config/ekizo-dl/searches.json')
  data = load_json(path)
  data['target'] = os.path.expanduser(data['target'])
  return data


def get_cache():
  path = os.path.expanduser('~/.cache/ekizo-dl')
  ensure_dir(path)
  cache = path + '/cache.json'
  if os.path.exists(cache):
    return load_json(cache)
  else:
    return {}


def fetch_shop_images(html, base):
  images_re = re.compile(r"<img\s+src\s*=\s*\"(https://img.mandarake.co.jp/webshopimg/)(.+?)s_(.+?)\".+?>")
  images = [(m.group(1) + m.group(2) + m.group(3)).strip() for m in images_re.finditer(html)]
  return images


def fetch_shop_links(html, base):
  links_re = re.compile(r"<a\s+href\s*=\s*\"(/order/detailPage/item)(.+?)\".*>")
  links_path = list(set([(m.group(1) + m.group(2)).strip() for m in links_re.finditer(html)]))
  links = list(map(lambda x: urllib.parse.unquote(htmlmodule.unescape(base.rstrip('/') + x)), links_path))
  return links


def fetch_links(html, base):
  items_re = re.compile(r'<!-- 商品情報のリスト -->(.*?)<!-- /id="aucItems" -->', re.MULTILINE | re.DOTALL)
  items = [m.group(1) for m in items_re.finditer(html)][0]
  
  blocks_re = re.compile(r'<div class="block">', re.MULTILINE | re.DOTALL)
  blocks = blocks_re.split(items)

  links = []
  links_re = re.compile(r"<a\s+id\s*=\s*\"goItemInfo\"\s+href\s*=\s*\"(.+?)\".+?>")
  for block in blocks:
    if not '>セル画<' in block:
      continue
    block_links = [m.group(1) for m in links_re.finditer(block)]
    for link in block_links:
      links.append(base + link)
  
  return links


def add_to_cache(cache, url, search):
  if not cache.get('cached_items'):
    cache['cached_items'] = {}
  cache['cached_items'][url] = [True, search]
  with open(os.path.expanduser('~/.cache/ekizo-dl/cache.json'), 'w') as f:
    json.dump(cache, f)
  return cache


def check_cache(cache, url):
  if not cache.get('cached_items'):
    return False
  item = cache['cached_items'].get(url)
  if item is None:
    return False
  return item[0]


def report_dl(url, search, id, result):
  if result:
    print('Downloaded item: {id}; search: {search}'.format(id=id, search=search))
  else:
    print('Could not download item: {id}; search: {search}'.format(id=id, search=search))


def report_search(url, search, urls, utilized_urls):
  print('Searched keyword: {search} - items found: {items}, new items: {utilized_urls}'.format(search=search, items=len(urls), utilized_urls=utilized_urls))
  print('URL: {url}'.format(url=url))


def get_url_id(url):
  id = re.search(r'index=(.+?)$', url)
  id = id.group(1) if id else None
  return id


def get_shop_url_id(url):
  id = re.search(r'itemCode=(.+?)&', url)
  id = id.group(1) if id else None
  return id


def download_url(url, search, id, target):
  search = search[0] if isinstance(search, list) else search
  search_dir = target + '/' + search
  ensure_dir(search_dir)
  os.chdir(search_dir)
  proc = subprocess.run(['ascr', '--dir-min', '1', '--overwrite', url])
  return proc.returncode == 0


def main():
  search_data = get_search_data()
  cache = get_cache()

  target = search_data['target']
  ensure_dir(target)

  for search in search_data['searches_shop']:
    time.sleep(1)
    url = mandarake_shop_search_url(search)
    base = get_shop_url_base(url)
    html = urllib.request.urlopen(url).read().decode('utf-8')
    urls = fetch_shop_links(html, base)
    utilized_urls = 0

    for url in urls:
      time.sleep(1)
      # Check if we've already downloaded this link before.
      has_cache = check_cache(cache, url)
      if has_cache: continue
      id = get_shop_url_id(url)
      result = download_url(url, search, id, target)
      report_dl(url, search, id, result)
      #cache = add_to_cache(cache, url, search)
      if not result: continue
      utilized_urls += 1
    
    report_search(url, search, urls, utilized_urls)

  for search in search_data['searches']:
    time.sleep(5)
    url = mandarake_search_url(search)
    base = get_url_base(url)
    html = urllib.request.urlopen(url).read().decode('utf-8')
    urls = fetch_links(html, base)
    utilized_urls = 0
    
    for url in urls:
      time.sleep(5)
      # Check if we've already downloaded this link before.
      has_cache = check_cache(cache, url)
      if has_cache: continue
      id = get_url_id(url)
      result = download_url(url, search, id, target)
      report_dl(url, search, id, result)
      cache = add_to_cache(cache, url, search)
      if not result: continue
      utilized_urls += 1
    
    report_search(url, search, urls, utilized_urls)

if __name__ == "__main__":
  main()
