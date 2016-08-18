import MySQLdb.cursors
import re
from elasticsearch import Elasticsearch

expected_tests = (
    "SELECT storm_testset_id, qc_id "
    "FROM storm_cycle_testset_details "
    "INNER JOIN storm_cycle_test_result USING(storm_testset_id) "
    "WHERE end_date >= '2016-01-01 00:00:00' "
    "AND storm_testset_name LIKE 'Auto :: e2e.set%%' "
    "AND storm_testset_name LIKE '%%.inweek.%%' "
    "AND storm_testset_status != '' "
)


query = ("SELECT storm_testset_id, storm_testset_name, "
         "storm_testset_status, start_time, end_time, qc_id, run_status "
         "FROM storm_test_run "
         "INNER JOIN storm_test_run_info USING(test_id) "
         "INNER JOIN storm_cycle_testset_details USING(storm_testset_id) "
         "WHERE storm_testset_id != 0 "
         "AND check_status != 'Discarded' "
         "AND storm_testset_name LIKE 'Auto :: e2e.set%%' "
         "AND storm_testset_name LIKE '%%.inweek.%%' "
         "AND storm_testset_status != '' "
         "AND end_date >= '2016-01-01 00:00:00' "
         "AND qc_id NOT IN (43, 41, 47, 58, 59, 63, 54, 55, 73, 72) "
         "ORDER BY storm_testset_name, qc_id, start_time")



run_status_order = {"Fail": 0, "Incomplete": 1, "Unknown": 2,
                    "Not Covered": 3, "In Progress": 4, "Not Started": 5, "Pass": 6}

map_result_to_test_set_counter = {"Fail": "testsFailed", "Incomplete": "testsIncomplete", "Unknown": "testsUnknown",
                    "Not Covered": "testsNotCovered", "In Progress": "testsInProgress", "Not Started": "testsNotStarted",
                    "Pass": "testsPassed"}


def new_test_set(current_test_result, totalsets):
    # Auto :: e2e.set.analytics.1.sut1.45D1 :: Q000.006.41.00:: QC set 12037
    match = re.match(r"^Auto :: e2e\.set\.(?P<type>[a-z0-9\._]*)\.(?P<platform>[a-zA-Z0-9\+]*) "
                     r":: (?P<stream>Q[0-9]{3})\.(?P<baseline>[0-9]{3}.[0-9]{2}.[0-9]{2})([A-Z]{1})? :: QC set [0-9]*$"
                     , current_test_result[1])
    if match is None:
        return None
    mg = match.groupdict()

    test_set = {"testsetId": current_test_result[0],
                "testsetType": mg["type"],
                "stream": mg["stream"],
                "baseline": mg["baseline"],
                "platform": mg["platform"],
                "startDate": current_test_result[3],
                "endDate": current_test_result[4] if isinstance(current_test_result[4], datetime)
                                                                else current_test_result[3],
                "testsFailed": 0, "testsIncomplete": 0, "testsUnknown": 0, "testsNotCovered": 0,
                "testsInProgress": 0, "testsNotStarted": 0, "testsPassed": 0
                }
    totalsets["root"].append(test_set)
    return test_set

from datetime import datetime

def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""

    if isinstance(obj, datetime):
        serial = obj.isoformat()
        return serial
    raise TypeError ("Type not serializable")

def _get_sql_connection():
    return MySQLdb.connect(host='10.20.32.99',
                          port=3306,
                          user='auto_ethan',
                          passwd='useC0nf1gFile',
                          db='ethan_autodb')


def _get_testset_collections():
    con = _get_sql_connection()
    try:
        con.query(expected_tests)
        r = con.store_result()
        testsets = dict()
        for i in r.fetch_row(maxrows=0):
            if not testsets.has_key(i[0]):
                testsets[i[0]] = set([i[1]])
            else:
                testsets[i[0]].add(i[1])
        return testsets
    finally:
        con.close()

def _add_none_run_tests(test_set, testset_tests, tests_recorded):
    diff = testset_tests.difference(tests_recorded)
    test_set[map_result_to_test_set_counter["Not Started"]] += len(diff)

def export_storm_test_results():
    testset_tests = _get_testset_collections()
    totalsets = {"root": []}
    con = _get_sql_connection()
    cursor = con.cursor(MySQLdb.cursors.SSCursor)
    cursor.execute(query)
    previous_test_result = cursor.fetchone()
    current_test_set = new_test_set(previous_test_result, totalsets)
    run_tests_for_set = set()
    for current_test_result in cursor:
        # for each test set determined by the testset name
        if current_test_set is None or current_test_result[0] != current_test_set["testsetId"]:
            if previous_test_result:
                current_test_set[map_result_to_test_set_counter[previous_test_result[6]]] += 1
                _add_none_run_tests(current_test_set, testset_tests[current_test_set["testsetId"]], run_tests_for_set)
                run_tests_for_set = set()
            current_test_set = new_test_set(current_test_result, totalsets)
            if current_test_set is None:
                continue
            previous_test_result = None

        if current_test_result[3] < current_test_set["startDate"]:
            current_test_set["startDate"] = current_test_result[3]

        if isinstance(current_test_result[4], datetime) and current_test_result[4] > current_test_set["endDate"]:
            current_test_set["endDate"] = current_test_result[4]

        if previous_test_result:
            if previous_test_result[5] == current_test_result[5]:
                # lower order runs (e.g. Fail) trump higher order (Pass)
                if run_status_order[previous_test_result[6]] < run_status_order[current_test_result[6]]:
                    # So skip this item
                    continue
            else:
                current_test_set[map_result_to_test_set_counter[previous_test_result[6]]] += 1
        previous_test_result = current_test_result
        run_tests_for_set.add(previous_test_result[5])
    # for the last test result make sure to update the totals
    if previous_test_result:
        current_test_set[map_result_to_test_set_counter[previous_test_result[6]]] += 1
        _add_none_run_tests(current_test_set, testset_tests[current_test_set["testsetId"]], run_tests_for_set)
    return totalsets


def index_testset_documents(testsetdocuments):
    es = Elasticsearch()
    counter = 0
    for doc in testsetdocuments["root"]:
        try:
            es.index(index="testsetindex", doc_type="test_set", id=doc["testsetId"], body=doc)
        except Exception as e:
            print e
        counter += 1
    print "Indexed {} test set documents".format(counter)


def main():
    testsetdocuments = export_storm_test_results()
    index_testset_documents(testsetdocuments)


if __name__ == "__main__":
    main()