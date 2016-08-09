from elasticsearch import Elasticsearch
from operator import itemgetter
import json

query = {
    "size": 0,
    "aggs": {
        "streams": {
            "terms": {
                "field": "stream"
            },
            "aggs": {
                "baseline": {
                    "terms": {
                        "field": "baseline"
                    },
                    "aggs": {
                        "platform": {
                            "terms": {"field": "platform"},
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
                                "passfailure_ratio": {
                                    "bucket_script": {
                                        "buckets_path": {
                                            "total_passes": "passes",
                                            "total_failures": "failures",
                                            "total_incomplete": "incomplete",
                                            "total_inprogress": "inprogress",
                                            "total_notstarted": "notstarted"
                                        },
                                        "script": "total_passes / (total_failures + total_incomplete + total_inprogress + total_notstarted)"
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


def platform_baseline_passratios_for_google_line():

    def item_func(i):
        print i["key"]

    def baseline_annotations(baseline):
        return ["", ""]

    def baseline_accuracy(baseline):
        return [True]

    def process_baseline(b):
        test = [item_func(p) for p in sorted(b["platform"]["buckets"], key=itemgetter("key"))]

        return [b["key"]] + [float(p["passfailure_ratio"]["value"]) for p in
                             sorted(b["platform"]["buckets"], key=itemgetter("key"))] \
                       + baseline_annotations(b["key"]) \
                       + baseline_accuracy(b["key"])

    def process_stream(s):
        print s["key"]
        # per stream need to calculate something like this for each baseline
        # ["baseline", "platform1-val", "platform2-val", "platofrom3-val", "platform4-val", "any annotation for the baseline e.g. Gold, Pinned", true]
        return [process_baseline(b) for b in sorted(s["baseline"]["buckets"], key=itemgetter("key"))]

    es = Elasticsearch()
    res = es.search(index="testsetindex", body=query)
    if res:
        return json.dumps({"streams": [process_stream(s) for s in sorted(res["aggregations"]["streams"]["buckets"], key=itemgetter("key"), reverse=True)]})


if "__main__":
    print platform_baseline_passratios_for_google_line()
