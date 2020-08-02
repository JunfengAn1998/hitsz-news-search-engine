from elasticsearch import Elasticsearch

from searchapp.constants import DOC_TYPE, INDEX_NAME
from searchapp.data import all_products, ProductData
from elasticsearch.helpers import bulk


def main():
    # Connect to localhost:9200 by default.
    es = Elasticsearch()

    es.indices.delete(index=INDEX_NAME, ignore=404)
    es.indices.create(
        index=INDEX_NAME,
        body={
            'mappings': {
                'properties': {                             # Just a magic word.
                    'title': {                                 # The field we want to configure.
                        'type': 'text',                         # The kind of data we’re working with.
                        'fields': {                             # create an analyzed field.
                            'chinese_analyzed': {                 # Name that field `name.english_analyzed`.
                                'type': 'text',                     # It’s also text.
                                'analyzer': 'ik_max_word',              # And here’s the analyzer we want to use.
                                'search_analyzer': 'ik_smart'
                            }
                        }
                    }
                }
            },
            'settings': {},
        },
    )
    bulk(es, products_to_index())


def index_product(es, product: ProductData):
    """Add a single product to the ProductData index."""

    es.create(
        index=INDEX_NAME,
        doc_type=DOC_TYPE,
        id=1,
        body={
            "name": "A Great Product",
            "image": "http://placekitten.com/200/200",
        }
    )

    # Don't delete this! You'll need it to see if your indexing job is working,
    # or if it has stalled.
    print("Indexed {}".format("A Great Product"))


def products_to_index():
    for product in all_products():
        yield {
            '_op_type': 'create',
            "_index": INDEX_NAME,
            # doc_type=DOC_TYPE,
            "_id": product.id,
            "_source": {
                "url": product.url,
                "title": product.title,
            }
        }


if __name__ == '__main__':
    main()
