import os
import xml.etree.ElementTree as ET
from app.models.error import Error
from app.models.test import Test
from app.models.failure import Failure
from app.reportGenerator import ReportGenerator
from app.argumentManager import ArgumentManager
from app.DataManager import DataManager
import sys

#   CONFIGURATION
# threshold = 0.9
numberOfLastFailedVersions = 5


# ignoredChars = ' \t\n'


# TBD: do we need to have ignoredVersions / ignoredErrors / ignoredTests functionality?
# TBD: maybe we should not show all old errors in report, only recent ones?
# TBD: report generation is slow, think what and how to optimize. Need to profile execution to get bottlenecks
#   Bottleneck is difflib, especially for huge number of long error messages
#   Decided to treat all query errors equal, anyway we need to process them manually
#   Also added initial check on string length comparison

def _clean_common_variables():
    # globals are created upon first execution
    global gERRORS, gNEW_ERRORS

    gERRORS = {}  # map: Error <-> list<Failure>
    gNEW_ERRORS = {}  # map: Error <-> list<Failure>


def get_fail_message(message):
    error_markers = ["TestCheck.Failure: ", "Exception: ", "NameError: ", "RuntimeError: ", "IndexError: ",
                     "AssertionError: ", "TypeError: ", "AttributeError: ", "ValueError: "]
    for error_marker in error_markers:
        if error_marker in message:
            return message.split(error_marker, 1)[1]
    return message


def get_old_fail(data_save_path):
    global gERRORS

    data_manager = DataManager()
    gERRORS = data_manager.get_old_analyze(data_save_path)


def _add_failure_preliminary(file, test_suite_name, test_case_name, failure, failed_version):
    global gERRORS
    error = Error(failure)
    if gERRORS.get(error) is None:
        for er in gERRORS.keys():
            if er == error:
                gERRORS[er].add_test(Test(file, test_suite_name, test_case_name))
                gERRORS[er].count_up(failed_version)
                return
        gERRORS[error] = Failure({Test(file, test_suite_name, test_case_name)}, failed_version, 1, [failed_version])
    else:
        gERRORS[error].add_test(Test(file, test_suite_name, test_case_name))
        gERRORS[error].count_up(failed_version)


def _process_preliminary_failures(version):
    global gERRORS, gNEW_ERRORS

    for error, failure in gNEW_ERRORS.items():
        if gERRORS.get(error) is None:
            gERRORS[error] = failure
            continue
        else:
            it = True
            for err in gERRORS.keys():
                if err == error:
                    for test in failure.tests:
                        gERRORS[err].add_test(test)
                    gERRORS[err].count_up(version)
                    it = False
                    break
            if it:
                for test in failure.tests:
                    gERRORS[error].tests.add(test)
                gERRORS[error].count_up(version)


def _check_for_suite_failure(file, test_suite, test_suite_name, failed_version):
    if test_suite.get('testsuite_failed') == 'True':
        test_case_name = 'setup'
        for failure in test_suite.findall('.//failure'):
            _add_failure_preliminary(file, test_suite_name, test_case_name,
                                     get_fail_message(failure.text), failed_version)


def check_logs(path, version):
    global gNEW_ERRORS, gERRORS
    for file in os.listdir(path):
        if file.endswith(".xml"):
            root = ET.parse(path + '/' + file).getroot()
            print(file)

            for test_suite in root.findall('.//testsuite'):
                test_suite_name = str(test_suite.get('name'))
                if test_suite.get('skipped') != '0':
                    _check_for_suite_failure(file, test_suite, test_suite_name, version)
                else:
                    for test_case in test_suite.findall('.//testcase'):
                        for failure in test_case.findall('.//failure'):
                            test_case_name = str(test_case.get('name'))
                            _add_failure_preliminary(file, test_suite_name,
                                                     test_case_name, get_fail_message(failure.text), version)

    #print('Length of known error database = {}'.format(len(gERRORS)))
    # _process_preliminary_failures(version)
    #print('Potential error count = {}'.format(len(gNEW_ERRORS)))
    #print('Update error database = {}'.format(len(gERRORS)))


def save_errors(data_save_path):
    global gERRORS

    data_manager = DataManager()
    data_manager.save_analyze(data_save_path, gERRORS.items())


def do_check(path, version, data_save_path, need_save=False):
    _clean_common_variables()

    if not os.path.isdir(path):
        print(f"Folder {path} does not exists!")
        return

    get_old_fail(data_save_path)
    check_logs(path=path, version=version)
    if need_save:
        save_errors(data_save_path)
    ReportGenerator.write_fails_2_HTML(gERRORS=gERRORS, data_save_path=data_save_path, version=version)


def run():
    print('Starting SF Manager Result...')
    argsManager = ArgumentManager()

    do_check(argsManager.get_path_logs(), argsManager.get_version(), argsManager.get_path2save(),
             argsManager.get_need_save())

    print('Done!')


if __name__ == '__main__':
    run()
