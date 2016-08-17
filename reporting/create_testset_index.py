import json
from elasticsearch import Elasticsearch

test_type_mappings = {

    "properties": {
        "testsetId": {
            "type": "long"
        },
        "testsetType": {
            "type": "string"
        },
        "stream": {
            "type": "string"
        },
        "baseline": {
            "type": "string",
            "fields": {
                "raw": {
                    "type": "string",
                    "index": "not_analyzed"
                }
            }
        },
        "platform": {
            "type": "string",
            "fields": {
                "raw": {
                    "type": "string",
                    "index": "not_analyzed"
                }
            }
        },
        "startDate": {
            "type": "date"
        },
        "endDate": {
            "type": "date"
        },
        "testsPassed": {
            "type": "long"
        },
        "testsIncomplete": {
            "type": "long"
        },
        "testsUnknown": {
            "type": "long"
        },
        "testsNotCovered": {
            "type": "long"
        },
        "testsInProgress": {
            "type": "long"
        },
        "testsNotStarted": {
            "type": "long"
        },
        "testsPassed": {
            "type": "long"
        }
    }
}

es = Elasticsearch()
try:
    es.indices.delete("testsetindex")
except:
    pass
es.indices.create("testsetindex")
es.indices.put_mapping(doc_type="test_set", body=test_type_mappings, index="testsetindex")


