import os
import xml.etree.ElementTree as ET
from app.models.error import Error
from app.models.test import Test
from app.models.failure import Failure
from app.reportGenerator import ReportGenerator
from app.argumentManager import ArgumentManager
from app.DBManager import DBManager
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


def _get_errors_from_XML(root):
    errors = {}
    errors_XML = root.find('.//errors')
    for error in errors_XML.findall('.//error'):
        temp_count = int(error.get('count'))
        temp_first_version = error.get('first_version')
        temp_error = Error(error.get('msg'))
        temp_tests = set()
        for test in error.findall('.//test'):
            temp_tests.add(Test(test.get('file'), test.get('test_suite'), test.get('test_case')))
        temp_versions = []
        for version in error.findall('.//version'):
            temp_versions.append(version.get('version'))

        errors[temp_error] = Failure(temp_tests, temp_first_version, temp_count, temp_versions)

    return errors


def get_old_fail(data_save_path):
    global gERRORS

    path = data_save_path + '/fails.xml'
    # TBD: copy old fails.xml with timestamp to have version history? Or add timestamp to xml file as version?
    if not os.path.exists(path):
        with open(path, 'w'): pass
    if os.stat(path).st_size == 0:
        return
    tree = ET.parse(path)
    root = tree.getroot()

    gERRORS = _get_errors_from_XML(root)


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

    print('Length of known error database = {}'.format(len(gERRORS)))
    #_process_preliminary_failures(version)
    print('Potential error count = {}'.format(len(gNEW_ERRORS)))
    print('Update error database = {}'.format(len(gERRORS)))


def write_fails_2_file(data_save_path, version=None):
    global gERRORS

    root = ET.Element("root")

    db_manager = DBManager()

    # processing gERRORS
    xml = ET.SubElement(root, 'errors')
    for error_msg, failure in gERRORS.items():
        error = ET.SubElement(xml, 'error', msg=str(error_msg),
                              count=str(failure.count), first_version=str(failure.first_version))
        tests = ET.SubElement(error, 'tests')
        for test in failure.tests:
            ET.SubElement(tests, "test", file=str(test.file), test_suite=str(test.test_suite),
                          test_case=str(test.test_case))
        versions = ET.SubElement(error, 'versions')
        for version in reversed(failure.last_versions[-5:]):
            ET.SubElement(versions, "version", version=str(version))

        #print(str(error_msg))
    db_manager.save_analyze(version, gERRORS.items())

    tree = ET.ElementTree(root)
    tree.write(f'{data_save_path}/fails.xml')


def do_check(path, version, data_save_path, generate_report=False):
    _clean_common_variables()

    if not os.path.isdir(path):
        print(f"Folder {path} does not exists!")
        return
    get_old_fail(data_save_path=data_save_path)
    check_logs(path=path, version=version)
    write_fails_2_file(data_save_path=data_save_path, version=version)
    if generate_report:
        ReportGenerator.write_fails_2_HTML(gERRORS=gERRORS, data_save_path=data_save_path, version=version)


def run():
    print('Starting SF Manager Result...')
    argsManager = ArgumentManager()

    do_check(argsManager.get_path_logs(), argsManager.get_version(),
             argsManager.get_path2save(), argsManager.get_need_save())

    print('Done!')


if __name__ == '__main__':
    run()
