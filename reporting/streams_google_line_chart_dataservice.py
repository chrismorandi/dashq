from elasticsearch import Elasticsearch
from operator import itemgetter
import json
import copy

query = {
    "size": 0,
    "query": {
        "bool": {
            "must": [
                {
                    "match": {"stream": ""}
                },
                {
                    "match": {"platform.raw": ""}
                },
                {
                    "range": {
                        "startDate": {
                            "gte": "2016-06-07T00:00:00.000Z"
                        }
                    }
                }
            ]
        }
    },
    "aggs": {
        "streams": {
            "terms": {
                "field": "stream"
            },
            "aggs": {
                "baseline": {
                    "terms": {
                        "field": "baseline",
                        "size": 100
                    },
                    "aggs": {
                        "platform": {
                            "terms": {"field": "platform.raw"},
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
                                "notstarted": {
                                    "sum": {
                                        "field": "testsNotStarted"
                                    }
                                },
                                "inprogress": {
                                    "sum": {
                                        "field": "testsInProgress"
                                    }
                                },
                                "incomplete": {
                                    "sum": {
                                        "field": "testsIncomplete"
                                    }
                                },
                                "passfailure_percentage": {
                                    "bucket_script": {
                                        "buckets_path": {
                                            "total_passes": "passes",
                                            "total_failures": "failures",
                                            "total_incomplete": "incomplete",
                                            "total_inprogress": "inprogress",
                                            "total_notstarted": "notstarted"
                                        },
                                        "script": "total_passes/(total_passes + total_failures + total_incomplete + total_inprogress + total_notstarted)*100"
                                    }
                                }
                            }

                        }
                    }
                }
            }
        }
    }
}

'''
{"cols":[{"id":"","label":"Baseline","pattern":"","type":"string"},
         {"id":"","label":"45d1","pattern":"","type":"number"},
         {"id":"","label":"mult","pattern":"","type":"number"},
         {"id":"","label":"xwng","pattern":"","type":"number"},
         {"type":"string","role":"annotationText","p":{"role":"annotationText"}},
         {"type":"boolean","role":"certainty","p":{"role":"certainty"}}],
 "rows":[{"c":[{"v":"000.12.00"},{"v":2},{"v":0.8333333333333334},{"v":1.75},{"v":""},{"v":""},{"v":true}]},
         {"c":[{"v":"000.13.00"},{"v":3.4},{"v":6.333333333333333},{"v":3.4},{"v":""},{"v":""},{"v":true}]},
         {"c":[{"v":"000.14.00"},{"v":2.142857142857143},{"v":4.5},{"v":6.333333333333333},{"v":""},{"v":""},{"v":true}]},
         {"c":[{"v":"000.15.00"},{"v":2.6666666666666665},{"v":2.6666666666666665},{"v":4.5},{"v":""},{"v":""},{"v":true}]},
         {"c":[{"v":"000.16.00"},{"v":2.142857142857143},{"v":1.4444444444444444},{"v":2.142857142857143},{"v":""},{"v":""},{"v":true}]},
         {"c":[{"v":"000.18.00"},{"v":1.75},{"v":2.6666666666666665},{"v":6.333333333333333},{"v":""},{"v":""},{"v":true}]},
         {"c":[{"v":"000.19.00"},{"v":2.142857142857143},{"v":1.75},{"v":3.4},{"v":""},{"v":""},{"v":true}]},
         {"c":[{"v":"000.20.00"},{"v":3.4},{"v":2.142857142857143},{"v":1.75},{"v":""},{"v":""},{"v":true}]},
         {"c":[{"v":"000.21.00"},{"v":1.75},{"v":1},{"v":3.4},{"v":""},{"v":""},{"v":true}]},
         {"c":[{"v":"000.22.00"},{"v":2.142857142857143},{"v":2.6666666666666665},{"v":3.4},{"v":""},{"v":""},{"v":false}]}]
 }
'''


def _get_column_data(known_platforms):

    def _create_label(label, type):
        return {"id": "", "label": label, "pattern": "", "type": type}

    return [_create_label("Baseline", "string")] + [_create_label(p, "number") for p in known_platforms] + [{"type": "string", "role": "annotation", "p": {"role": "annotation"}}, {"type": "string", "role": "annotationText", "p": {"role": "annotationText"}}, {"type": "boolean", "role": "certainty", "p": {"role": "certainty"}}]


def _get_platforms_for_stream(stream):
    return ["45D1", "MULT+45D1", "XWNG", "MULT+XWNG", "UKV2", "MULT+UKV2"]


def _get_row_data(known_platforms, stream):

    def baseline_annotations(baseline):
        if baseline == "007.35.00":
            return "Golden"
        if baseline == "000.09.00":
            return "Pinned"
        else:
            return ""

    def process_baseline(b):
        '''
            {"c": [{"v": "000.12.00"}, {"v": 2}, {"v": 0.8333333333333334}, {"v": 1.75}, {"v": ""},  {"v": true}]}
        '''
        platforms_values = {p["key"]: p["passfailure_percentage"]["value"] for p in b["platform"]["buckets"]}
        still_to_complete = [p["inprogress"]["value"] > 0 or p["notstarted"]["value"] > 0 for p in b["platform"]["buckets"]]
        return {"c": [{"v": b["key"]}]
                     + [{"v": int(platforms_values[kp]) if kp in platforms_values else 0} for kp in known_platforms]
                     + [{"v": baseline_annotations(b["key"])}]
                     + [{"v": baseline_annotations(b["key"])}]
                     + [{"v": True not in still_to_complete}]
               }

    return [process_baseline(b) for b in sorted(stream["baseline"]["buckets"], key=itemgetter("key"))]


def get_data(stream, platform, start_date):
    es = Elasticsearch()
    current_query = copy.deepcopy(query)
    current_query["query"]["bool"]["must"][0]["match"]["stream"] = stream
    current_query["query"]["bool"]["must"][1]["match"]["platform.raw"] = platform
    current_query["query"]["bool"]["must"][2]["range"]["startDate"]["gte"] = start_date
    if platform is None:
        del current_query["query"]["bool"]["must"][1]
    print current_query
    res = es.search(index="testsetindex", body=current_query)
    if res and res["hits"]["total"] > 0:
        stream = res["aggregations"]["streams"]["buckets"][0]
        known_platforms = _get_platforms_for_stream(stream) if platform is None else [platform]
        return json.dumps({"cols": _get_column_data(known_platforms),
                           "rows": _get_row_data(known_platforms, stream)})
    else:
        return json.dumps({"cols": "", "rows": ""})

if "__main__":
    print get_data("q000", None, "2016-08-07T00:00:00.000Z")
