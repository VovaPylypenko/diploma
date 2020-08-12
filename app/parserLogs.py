import xml.etree.ElementTree as ET
from app.models.test import Test
from app.models.failure import Failure
from app.models.error import Error
import os


class ParserLogManager:

    @staticmethod
    def get_fail_message(message):
        error_markers = ["TestCheck.Failure: ", "Exception: ", "NameError: ", "RuntimeError: ", "IndexError: ",
                         "AssertionError: ", "TypeError: ", "AttributeError: ", "ValueError: "]
        for error_marker in error_markers:
            if error_marker in message:
                return message.split(error_marker, 1)[1]
        return message

    @staticmethod
    def add_failure_preliminary(file, test_suite_name, test_case_name, failure, failed_version, gERRORS):
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

    @staticmethod
    def _check_for_suite_failure(file, test_suite, test_suite_name, failed_version, gERRORS):
        if test_suite.get('testsuite_failed') == 'True':
            test_case_name = 'setup'
            for failure in test_suite.findall('.//failure'):
                ParserLogManager.add_failure_preliminary(file, test_suite_name, test_case_name,
                                                          ParserLogManager.get_fail_message(failure.text),
                                                          failed_version, gERRORS)

    @staticmethod
    def check_logs(path, version, gERRORS):
        for file in os.listdir(path):
            if file.endswith(".xml"):
                root = ET.parse(path + '/' + file).getroot()

                for test_suite in root.findall('.//testsuite'):
                    test_suite_name = str(test_suite.get('name'))
                    if test_suite.get('skipped') != '0':
                        ParserLogManager._check_for_suite_failure(file, test_suite, test_suite_name, version, gERRORS)
                    else:
                        for test_case in test_suite.findall('.//testcase'):
                            for failure in test_case.findall('.//failure'):
                                test_case_name = str(test_case.get('name'))
                                ParserLogManager.add_failure_preliminary(file, test_suite_name, test_case_name,
                                                                         ParserLogManager.get_fail_message(failure.text),
                                                                         version, gERRORS)

        #print('Length of known error database = {}'.format(len(gERRORS)))
        #print('Update error database = {}'.format(len(gERRORS)))
