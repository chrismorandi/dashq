from elasticsearch import Elasticsearch
import json


query = {
   "size": 0,
   "aggs": {
      "streams": {
         "terms": {
            "field": "stream"
         },
         "aggs": {
            "recentbaselines": {
               "terms": {
                  "field": "baseline",
                  "size": 5,
                  "order": {"startDate": "desc"}
               },
               "aggs": {
                  "startDate" : { "max" : { "field" :"startDate" } },
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

def _get_top_5(streams):
   buckets = []
   for s in streams:
      for b in s["recentbaselines"]["buckets"]:
         buckets.append([b["startDate"]["value_as_string"], s["key"].upper() + "." + b["key"], b])
   return sorted(buckets, key=lambda t: t[0], reverse=True)[:5]


def _get_lastbaseline_data(top_bs):
    def format_baseline(bs):
        return [bs[1],
              float(bs[2]["passpercentage"]["value"]), float(bs[2]["failurepercentage"]["value"]),
              float(bs[2]["inprogresspercentage"]["value"]), float(bs[2]["incompletepercentage"]["value"]),
              float(bs[2]["notrunpercentage"]["value"])]
    return [format_baseline(bs) for bs in top_bs]

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
        data += _get_lastbaseline_data(_get_top_5(res["aggregations"]["streams"]["buckets"]))
    return json.dumps({"data": data})


if "__main__":
    print get_data()