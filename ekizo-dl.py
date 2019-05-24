#!/usr/bin/env python3

import os
import re
import subprocess
import urllib.request
import time
import json
import urllib.parse


def mandarake_search_url(search):
  return 'https://ekizo.mandarake.co.jp/auction/item/itemsListJa.html?t=0&q={}'.format(urllib.parse.quote(search))


def get_url_base(url):
  return '/'.join(url.split('/')[:-1]) + '/'


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


def fetch_links(html, base):
  regex = r"<a\s+id\s*=\s*\"goItemInfo\"\s+href\s*=\s*\"(.+?)\".+?>"
  matches = re.finditer(regex, html, re.MULTILINE)
  links = []
  for match in matches:
    links.append(base + match.group(1))
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


def get_url_id(url):
  id = re.search(r'index=(.+?)$', url)
  id = id.group(1) if id else None
  return id


def download_url(url, search, id, target):
  search_dir = target + '/' + search
  ensure_dir(search_dir)
  os.chdir(search_dir)
  proc = subprocess.run(['ascr', url])
  return proc.returncode == 0


def main():
  search_data = get_search_data()
  cache = get_cache()

  target = search_data['target']
  ensure_dir(target)
  for search in search_data['searches']:
    url = mandarake_search_url(search)
    base = get_url_base(url)
    html = urllib.request.urlopen(url).read().decode('utf-8')
    urls = fetch_links(html, base)
    
    for url in urls:
      # Check if we've already downloaded this link before.
      has_cache = check_cache(cache, url)
      if has_cache: continue
      id = get_url_id(url)
      result = download_url(url, search, id, target)
      report_dl(url, search, id, result)
      if not result: continue
      cache = add_to_cache(cache, url, search)
      time.sleep(5)

if __name__ == "__main__":
  main()
