from elasticsearch import Elasticsearch
import json


query = {
   "size": 0,
   "aggs": {
      "stream": {
         "terms": {
            "field": "stream",
            "size": 4
         },
         "aggs": {
            "recentbaselines": {
               "terms": {
                  "field": "baseline",
                  "size": 1,
                  "order": {
                     "_term": "desc"
                  }
               },
               "aggs": {
                  "passes": {
                     "sum": {
                        "field": "testsPassed"
                     }
                  },
                  "failures": {
                     "sum": {
                        "field": "testsFailed"
                     }
                  },
                  "incompletes": {
                     "sum": {
                        "field": "testsIncomplete"
                     }
                  },
                  "notrun": {
                     "sum": {
                        "field": "testsNotStarted"
                     }
                  },
                  "inprogress": {
                     "sum": {
                        "field": "testsInProgress"
                     }
                  },
                  "grandtotal": {
                     "bucket_script": {
                        "buckets_path": {
                           "tpasses": "passes",
                           "tfailures": "failures",
                           "tincomplete": "incompletes",
                           "tinprogress": "inprogress",
                           "tnotstarted": "notrun"
                        },
                        "script": "tpasses + tfailures + tincomplete + tinprogress + tnotstarted"
                     }
                  },
                  "passpercentage": {
                     "bucket_script": {
                        "buckets_path": {
                           "tpasses": "passes",
                           "total": "grandtotal"
                        },
                        "script": "(tpasses/total) * 100"
                     }
                  },
                  "failurepercentage": {
                     "bucket_script": {
                        "buckets_path": {
                           "tfailures": "failures",
                           "total": "grandtotal"
                        },
                        "script": "(tfailures/total) * 100"
                     }
                  },
                  "inprogresspercentage": {
                     "bucket_script": {
                        "buckets_path": {
                           "tinprogress": "inprogress",
                           "total": "grandtotal"
                        },
                        "script": "(tinprogress/total) * 100"
                     }
                  },
                  "incompletepercentage": {
                     "bucket_script": {
                        "buckets_path": {
                           "tincomplete": "incompletes",
                           "total": "grandtotal"
                        },
                        "script": "(tincomplete/total) * 100"
                     }
                  },
                  "notrunpercentage": {
                     "bucket_script": {
                        "buckets_path": {
                           "tnotrun": "notrun",
                           "total": "grandtotal"
                        },
                        "script": "(tnotrun/total) * 100"
                     }
                  }
               }
            }
         }
      }
   }
}

def _get_lastbaseline_data(sb):
    # just get the first item for each stream
    b = sb["recentbaselines"]["buckets"][0]
    item = ["{}.{}".format(sb["key"], b["key"]),
            int(b["passpercentage"]["value"]), int(b["failurepercentage"]["value"]), int(b["inprogresspercentage"]["value"]), int(b["incompletepercentage"]["value"]), int(b["notrunpercentage"]["value"])]
    print item
    return item

def get_data():
    data = [["Baseline", "Passed", "Failed", "Inprogress", "Incomplete", "Not run"]]
    print type(data)
    es = Elasticsearch()
    res = es.search(index="testsetindex", body=query)
    if res:
        '''
        ['Baseline', 'Passed', 'Failed', 'Inprogress' 'Incomplete', 'Not run', { role: 'annotation' } ],

        ['Q002.004.02.01', 60, 15, 25, 0],......

        '''
        data += [_get_lastbaseline_data(s) for s in res["aggregations"]["stream"]["buckets"]]
    return json.dumps({"data": data})


if "__main__":
    print get_data()