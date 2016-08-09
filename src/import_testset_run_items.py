import json
from elasticsearch import Elasticsearch

d = None
with open('/tmp/out.json') as json_data:
    d = json.load(json_data)

counter = 0
es = Elasticsearch()
for doc in d["root"]:
    es.index(index="testsetindex", doc_type="test_set", id=doc["testsetId"], body=doc)
    counter += 1
print counter


