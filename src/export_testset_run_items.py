import MySQLdb.cursors
import re
import json


query = ("SELECT testset.storm_testset_id, testset.storm_testset_name, "
         "testset.storm_testset_status, run.start_time, run.end_time, run.qc_id, run.run_status "
         "FROM storm_test_run run "
         "INNER JOIN storm_test_run_info run_info ON run_info.test_id = run.test_id "
         "INNER JOIN storm_cycle_testset_details testset ON testset.storm_testset_id = run_info.storm_testset_id "
         "WHERE run_info.storm_testset_id != 0 "
         "AND run_info.check_status != 'Discarded' "
         "AND testset.storm_testset_name LIKE 'Auto :: e2e.set%%' "
         "AND testset.storm_testset_name LIKE '%%.inweek.%%' "
         "AND testset.storm_testset_status != '' "
         "AND testset.end_date >= '2016-01-01 00:00:00' "
         "AND run.qc_id NOT IN (43, 41, 47, 58, 59, 63, 54, 55, 73, 72) "
         "ORDER BY storm_testset_name, run.qc_id, run.start_time")


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
                "startDate": str(current_test_result[3]),
                "endDate": str(current_test_result[4]),
                "testsFailed": 0, "testsIncomplete": 0, "testsUnknown": 0, "testsNotCovered": 0,
                "testsInProgress": 0, "testsNotStarted": 0, "testsPassed": 0
                }
    totalsets["root"].append(test_set)
    return test_set


def export_storm_test_results():
    totalsets = {"root": []}
    con = MySQLdb.connect(host='10.20.32.99',
                          port=3306,
                          user='auto_ethan',
                          passwd='useC0nf1gFile',
                          db='ethan_autodb')
    cursor = con.cursor(MySQLdb.cursors.SSCursor)
    cursor.execute(query)
    previous_test_result = cursor.fetchone()
    current_test_set = new_test_set(previous_test_result, totalsets)

    for current_test_result in cursor:
        # for each test set determined by the testset name
        if current_test_set is None or current_test_result[0] != current_test_set["testsetId"]:
            if previous_test_result:
                current_test_set[map_result_to_test_set_counter[previous_test_result[6]]] += 1
            current_test_set = new_test_set(current_test_result, totalsets)
            if current_test_set is None:
                continue
            previous_test_result = None

        if str(current_test_result[3]) < current_test_set["startDate"]:
            current_test_set["startDate"] = str(current_test_result[3])

        if str(current_test_result[4]) > current_test_set["endDate"]:
            current_test_set["endDate"] = str(current_test_result[4])

        if previous_test_result:
            if previous_test_result[5] == current_test_result[5]:
                # lower order runs (e.g. Fail) trump higher order (Pass)
                if run_status_order[previous_test_result[6]] < run_status_order[current_test_result[6]]:
                    # So skip this item
                    continue
            else:
                current_test_set[map_result_to_test_set_counter[previous_test_result[6]]] += 1

        previous_test_result = current_test_result

    with open("/tmp/out.json", "wt", 10248) as outfile:
        json.dump(totalsets, outfile)


def main():
    export_storm_test_results()


if __name__ == "__main__":
    main()