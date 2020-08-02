import requests
from elasticsearch import Elasticsearch
from searchapp.constants import INDEX_NAME
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import random
from tqdm import tqdm

from bs4 import BeautifulSoup

headers = {'User-Agent': 'Mozilla/5.0'}
url_header = 'http://www.hitsz.edu.cn'

from functools import wraps


def retry(max_retries=5, error_handler=None):
    def _wrapped_factory(fn):
        assert max_retries > 0

        @wraps(fn)
        def _wrapped(*args, **kwargs):
            failed_count = 0
            while True:
                # noinspection PyBroadException
                try:
                    result = fn(*args, **kwargs)
                    return result
                except:
                    failed_count += 1
                    if failed_count > max_retries:
                        if error_handler is None:
                            print("[%s(%s) too many errors, stop" % (fn.__name__, args.__repr__()))
                            return None
                        else:
                            return error_handler(*args, **kwargs)
                    print("[%s(%s)] retry %d / %d" % (fn.__name__, args.__repr__(), failed_count, max_retries))
                    continue

        return _wrapped

    return _wrapped_factory


pool = ThreadPoolExecutor(40)


def reschedule(*args, **kwargs):
    pool.submit(download, *args, **kwargs)


@retry(max_retries=5, error_handler=reschedule)
def download(url):
    content = requests.get(url_header + url, headers=headers).text
    soup = BeautifulSoup(content, 'lxml')
    try:
        # time.sleep(random.uniform(0.1, 1))
        return {
            'url': url_header + url,
            'title': soup.title.string,
            'content': soup.find(class_='edittext').get_text()
        }
    except:
        pass


def get_url():
    stop_url = ''
    url = 'http://www.hitsz.edu.cn/article/index.html'
    columns = [link.get('href') for link in
               BeautifulSoup(requests.get(url, headers=headers).text, 'lxml').find_all('ul')[0].find_all('a')[4:]]
    for url in columns:
        column_urls = set()
        column_url = url_header + url
        for i in range(0, 10000, 20):
            column_url_cur = column_url + '?maxPageItems=20&keywords=&pager.offset=%d' % i
            time.sleep(random.uniform(0.5, 1.5))
            try:
                text = requests.get(column_url_cur, headers=headers).text
            except:
                continue
            a_list = BeautifulSoup(text, 'lxml').find_all('ul')[1].find_all('a')
            if len(a_list) == 0:
                break
            column_urls |= set([link.get('href') for link in a_list])
        with open('article-set.txt', 'a', encoding='utf-8') as f:
            f.writelines('\n'.join(list(column_urls)) + '\n')
    return stop_url


if __name__ == "__main__":
    stop_url = get_url()
    g = list(open('article-set.txt', 'r', encoding='utf-8'))
    es = Elasticsearch()
    es.indices.delete(index=INDEX_NAME, ignore=404)
    es.indices.create(
        index=INDEX_NAME,
        body={
            'mappings': {
                'properties': {  # Just a magic word.
                    'title': {  # The field we want to configure.
                        'type': 'text',  # The kind of data we’re working with.
                        'fields': {  # create an analyzed field.
                            'chinese_analyzed': {  # Name that field `name.english_analyzed`.
                                'type': 'text',  # It’s also text.
                                'analyzer': 'ik_max_word',  # And here’s the analyzer we want to use.
                                'search_analyzer': 'ik_smart'
                            }
                        }
                    }
                }
            },
            'settings': {},
        },
    )

    with open('news.json', 'a', encoding='utf-8') as f:
        for future in tqdm(as_completed(pool.submit(download, url.rstrip()) for url in g), total=len(g)):
            temp = future.result()
            if temp is None:
                continue
            try:
                es.create(
                    index=INDEX_NAME,
                    id=temp['url'],
                    body={
                        'url': temp['url'],
                        'title': temp['title'],
                        'content': temp['content']
                    }
                )
            except:
                try:
                    es.update(
                        index=INDEX_NAME,
                        id=temp['url'],
                        body={
                            'url': temp['url'],
                            'title': temp['title'],
                            'content': temp['content']
                        }
                    )
                except:
                    pass
                pass

