from elasticsearch import Elasticsearch
from elasticsearch_dsl import Search
from typing import List

from searchapp.constants import DOC_TYPE, INDEX_NAME

HEADERS = {
    'content-type': 'application/json'
}


class SearchResult():
    """Represents a product returned from elasticsearch."""

    def __init__(self, id_, url, title, content):
        self.id = id_
        self.url = url
        self.title = title
        self.content = content

    def from_doc(doc) -> 'SearchResult':
        try:
            highlight_title = doc.meta.highlight['title.chinese_analyzed'][0].replace('em', 'span').replace("<span>", "<span class=\"highlight\">")
        except:
            highlight_title = doc.title
        return SearchResult(
            id_=doc.meta.id,
            url=doc.url,
            title=highlight_title,
            content=doc.content,
        )


def search(term: str, count: int) -> List[SearchResult]:
    client = Elasticsearch()

    # Elasticsearch 6 requires the content-type header to be set, and this is
    # not included by default in the current version of elasticsearch-py
    client.transport.connection_pool.connection.headers.update(HEADERS)

    s = Search(using=client, index=INDEX_NAME)

    name_query = {
        "dis_max": {
            "queries": [
                {
                    "match": {
                        "title": {
                            "query": term,
                            "operator": "and",
                            "fuzziness": "AUTO"
                        }
                    }
                },
                {
                    "match": {
                        "content": {
                            "query": term,
                            "operator": "and",
                            "fuzziness": "AUTO"
                        }
                    }
                },
                {
                    "match": {
                        "title.chinese_analyzed": {
                            "query": term,
                            "operator": "and"
                        }
                    }
                }
            ],
            "tie_breaker": 0.7
        }
        # "match": {
        #     "title" : term
        # }
    }

    docs = s.query(name_query).highlight('title.chinese_analyzed')[:count].execute()

    return [SearchResult.from_doc(d) for d in docs]
