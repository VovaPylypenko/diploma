import os
import xml.etree.ElementTree as ET
from app.models.error import Error
from app.models.test import Test
from app.models.failure import Failure
import argparse
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

        errors[temp_error] = Failure(set(), set(), temp_tests, temp_first_version, temp_count, temp_versions)

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
        gERRORS[error] = Failure({Test(file, test_suite_name, test_case_name)},
                                       set(), set(), failed_version, 1, [failed_version])
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
                    print(';')
                    print(len(failure.tests_new))
                    gERRORS[err].tests_new = failure.tests_new
                    for test in failure.tests_replay:
                        gERRORS[err].add_test(test)
                    for test in failure.tests_old:
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


def write_fails_2_file(data_save_path):
    global gERRORS

    root = ET.Element("root")

    # processing gERRORS
    xml = ET.SubElement(root, 'errors')
    for error, failure in gERRORS.items():
        error = ET.SubElement(xml, 'error', msg=str(error),
                              count=str(failure.count), first_version=str(failure.first_version))
        tests = ET.SubElement(error, 'tests')
        for test in failure.tests_new:
            ET.SubElement(tests, "test", file=str(test.file), test_suite=str(test.test_suite),
                          test_case=str(test.test_case))
        for test in failure.tests_replay:
            ET.SubElement(tests, "test", file=str(test.file), test_suite=str(test.test_suite),
                          test_case=str(test.test_case))
        for test in failure.tests_old:
            ET.SubElement(tests, "test", file=str(test.file), test_suite=str(test.test_suite),
                          test_case=str(test.test_case))
        versions = ET.SubElement(error, 'versions')
        for version in reversed(failure.last_versions[-5:]):
            ET.SubElement(versions, "version", version=str(version))

    tree = ET.ElementTree(root)
    tree.write(f'{data_save_path}/fails.xml')


def add_td(text, type=""):
    return f'<td {type}> {text} </td>'


def create_table(error_blocks, status, style):
    error_table = ''

    for error_block in error_blocks:
        error_table += f'<tr>'
        # all failures in single block have the same errorID and failed version list
        error_table += add_td(error_block[0], style)

        tests_new_str = ''
        if not error_block[1].tests_new or len(error_block[1].tests_new) != 0:
            #print(error_block[1].tests_new)
            print(len(error_block[1].tests_new))
            tests_new_str = '<details><summary>NEW</summary>'
            for test in sorted(error_block[1].tests_new):
                tests_new_str += f'{test}<br>'
            tests_new_str += '</details>'
        else:
            print('NOT empty1')

        tests_replay_str = ''
        if not error_block[1].tests_replay or len(error_block[1].tests_replay) != 0:
            tests_replay_str = '<details><summary>REPLAY</summary>'
            for test in sorted(error_block[1].tests_replay):
                tests_replay_str += f'{test}<br>'
            tests_replay_str += '</details>'
        else:
            print('NOT empty2')

        tests_old_str = ''
        if not error_block[1].tests_old or len(error_block[1].tests_old) != 0:
            tests_old_str = '<details><summary>OLD</summary>'
            for test in sorted(error_block[1].tests_old):
                tests_old_str += f'{test}<br>'
            tests_old_str += '</details>'
        else:
            print('NOT empty3')

        error_table += add_td(tests_new_str + tests_replay_str + tests_old_str)
        error_table += add_td(status, style)
        error_table += add_td(error_block[1].count, 'class="data" align="left"')

        error_table += add_td(error_block[1].first_version)
        failed_versions_str = ''
        for failedVersion in error_block[1].last_versions:
            failed_versions_str += f'{failedVersion}<br>'
        error_table += add_td(failed_versions_str)
        error_table += f'</tr>'

    return error_table


def create_new_table(new_error_list):
    return create_table(new_error_list, 'New', 'class="failed data"')


def create_replay_table(replay_error_list):
    return create_table(replay_error_list, 'Replay', 'class="replay data"')


def create_old_table(old_error_list):
    return create_table(old_error_list, 'Old', 'class="data"')


def add_style():
    return f'''<style>
            table
            {'{'}
                border-collapse: collapse;
                border: 1px solid black;
                width:1900px;
            {'}'}

            tr
            {'{'}
                border:0;
                color:#DD0000;
            {'}'}

            th
            {'{'}
                height:20px;
                color:#727092;
                font-size:12px;
                font-weight:bold;
                font-family:Verdana;
                border: 1px solid #F0F0F0;
            {'}'}

            td
            {'{'}
                margin:0;
                height:20px;
                color:#9A95B0;
                font-size:10px;
                font-weight:bold;
                font-family:Verdana;
                border: 1px solid #F0F0F0;
            {'}'}

            noborder
            {'{'}
                width: 100%;
                border: 0px;
            {'}'}

            p.header
            {'{'}
                color:#727092;
                font-size:14px;
                font-weight:bold;
                font-family:Verdana;
            {'}'}

            td.name
            {'{'}
                padding-left:0px;
                text-align:left;
            {'}'}

            td.data
            {'{'}
                padding-left:0px;
                text-align:center;
            {'}'}

            td.failed
            {'{'}
                color:#FF0000;
            {'}'}

            td.skipped
            {'{'}
                color:#E18B6B;
            {'}'}
            td.passed
            {'{'}
                color:#347235;
            {'}'}

            td.replay
            {'{'}
                color:#505250;
            {'}'}

            td.inInspection
            {'{'}
                color:#4A0AD0;
            {'}'}

            .description
            {'{'}
                overflow:hidden;
                white-space:nowrap;
                width: 50%;
            {'}'}

            th.failed
            {'{'}
                height:12px;
                color:#FF0000;
                background:#FF0000;
            {'}'}
            th.skipped
            {'{'}
                height:12px;
                color:#E18B6B;
                background:#E18B6B;
            {'}'}
            th.passed
            {'{'}
                height:12px;
                color:#347235;
                background:#347235;
            {'}'}
        </style>'''


def write_fails_2_HTML(data_save_path, version):
    # Group tests by failure + failed version list, otherwise create new entry
    # if defect failedVersion has id = len(totalFailedVersions) and len(defectFailedVersion) == 1, this is new defect
    # if defect failedVersion has id = len(totalFailedVersions) and len(defectFailedVersion) > 1, this is replay defect
    # otherwise this is old defect
    global gERRORS

    new_errors = []
    replay_errors = []
    old_errors = []

    for error, failure in gERRORS.items():
        if failure.first_version == version and failure.count == 1:
            new_errors.append([error, failure])
        else:
            if version in failure.last_versions:
                replay_errors.append([error, failure])
            else:
                old_errors.append([error, failure])

    _writeFailsToHTML(new_errors, replay_errors, old_errors, data_save_path)


def _writeFailsToHTML(new_errors, replay_errors, old_errors, data_save_path):
    f = open(data_save_path + '/reportSFManager.html', 'w')

    message = f'''<html>
    <head>
        {add_style()}
    </head>
    <body> 
        <table class = "defect">
            <tr align ="center" width="99%">
                <th width="40%"> Name </th>
                <th width="44%"> Test </th>
                <th width="3%"> Status </th>
                <th width="3%"> Count </th>
                <th width="5%"> First failed version </th>
                <th width="5%"> Last 5 failed versions </th>
            </tr>
            {create_new_table(new_errors)}
            {create_replay_table(replay_errors)}
            {create_old_table(old_errors)}
        </table>
    </body>
    </html>'''

    f.write(message)
    f.close()


def do_check(path, version, data_save_path, generate_report=False):
    _clean_common_variables()

    if not os.path.isdir(path):
        print(f"Folder {path} does not exists!")
        return
    get_old_fail(data_save_path=data_save_path)
    check_logs(path=path, version=version)
    write_fails_2_file(data_save_path=data_save_path)
    if generate_report:
        write_fails_2_HTML(data_save_path=data_save_path, version=version)


# def addArgs():
#    ap = argparse.ArgumentParser()
#    # '+' == 1 or more.
#    # '*' == 0 or more.
#    # '?' == 0 or 1.
#    ap.add_argument('run_version', nargs='?', help="Name of run version")
#    ap.add_argument('path_save', nargs='?', help="Path for save result(should be the same for all runs)")
#    ap.add_argument('path_logs', nargs='*', help="Folder names with logs")
#    args = vars(ap.parse_args())
#    print(args['name'])


if __name__ == '__main__':
    print('Starting SF Manager Result...')

    # params: run version, path for save result, directory with SF result logs(xml)
    if len(sys.argv) > 3:
        data_save_path = sys.argv[1]
        for iter in range(2, len(sys.argv) - 3, 2):
            do_check(path=sys.argv[iter + 1], version=sys.argv[iter], data_save_path=data_save_path)
        do_check(path=sys.argv[-1], version=sys.argv[-2], data_save_path=data_save_path, generate_report=True)
        print('Done!')

    else:
        print('You must run the script with 3 or more parameters:\n'
              '1)Path for save result(should be the same for all runs)\n'
              '2)Name of run version,\n'
              '3)Folder names with logs\n'
              'Example: run.py <dataSavePath> <version 1> <folder 1> <version 2> <folder 2> ... <version N> <folder N>')
