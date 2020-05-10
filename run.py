import os
import xml.etree.ElementTree as ET
from app.models.error import Error
from app.models.test import Test
from app.models.failure import Failure
import argparse
import sys

#   CONFIGURATION
#threshold = 0.9
numberOfLastFailedVersions = 5
#ignoredChars = ' \t\n'


# TBD: do we need to have ignoredVersions / ignoredErrors / ignoredTests functionality?
# TBD: maybe we should not show all old errors in report, only recent ones?
# TBD: report generation is slow, think what and how to optimize. Need to profile execution to get bottlenecks
#   Bottleneck is difflib, especially for huge number of long error messages
#   Decided to treat all query errors equal, anyway we need to process them manually
#   Also added initial check on string length comparison

def _cleanCommonVariables():
    # globals are created upon first execution
    global gErrors, gNewErrors

    gErrors = {}  # map: Error <-> list<Failure>
    gNewErrors = {}  # map: Error <-> list<Failure>


def getFailMessage(message):
    errorMarkers = ["TestCheck.Failure: ", "Exception: ", "NameError: ", "RuntimeError: ", "IndexError: ",
                    "AssertionError: ", "TypeError: ", "AttributeError: ", "ValueError: "]
    for errorMarker in errorMarkers:
        if errorMarker in message:
            return message.split(errorMarker, 1)[1]
    return message


def _getErrorsFromXML(root):
    errors = {}
    errorsXML = root.find('.//errors')
    for error in errorsXML.findall('.//error'):
        temp_count = int(error.get('count'))
        temp_firstVersion = error.get('firstVersion')
        temp_error = Error(error.get('msg'))
        temp_tests = set()
        for test in error.findall('.//test'):
            temp_tests.add(Test(test.get('file'), test.get('testsuite'), test.get('testcase')))
        temp_versions = []
        for version in error.findall('.//version'):
            temp_versions.append(version.get('version'))

        errors[temp_error] = Failure(temp_tests, temp_firstVersion, temp_count, temp_versions)

    return errors


def getOldFail(dataSavePath):
    global gErrors, gTests, gFailedVersions, gFailures

    path = dataSavePath + '/fails.xml'
    # TBD: copy old fails.xml with timestamp to have version history? Or add timestamp to xml file as version?
    if not os.path.exists(path):
        with open(path, 'w'): pass
    if os.stat(path).st_size == 0:
        return
    tree = ET.parse(path)
    root = tree.getroot()

    gErrors = _getErrorsFromXML(root)


def _addFailurePreliminary(file, testsuiteName, testcaseName, failure, failedVersion):
    global gNewErrors
    error = Error(failure)
    if gNewErrors.get(error) is None:
        for er in gNewErrors.keys():
            if er == error:
                gNewErrors[er].addTest(Test(file, testsuiteName, testcaseName))
                gNewErrors[er].count_up(failedVersion)
                return
        gNewErrors[error] = Failure({Test(file, testsuiteName, testcaseName)}, failedVersion, 1, [failedVersion])
    else:
        gNewErrors[error].addTest(Test(file, testsuiteName, testcaseName))
        gNewErrors[error].count_up(failedVersion)


def _processPreliminaryFailures(version):
    global gNewErrors, gErrors

    for error, failure in gNewErrors.items():
        if gErrors.get(error) is None:
            gErrors[error] = failure
            continue
        else:
            it = True
            for err in gErrors.keys():
                if err == error:
                    for test in failure.tests:
                        gErrors[err].tests.add(test)
                    gErrors[err].count_up(version)
                    it = False
                    break
            if it:
                for test in failure.tests:
                    gErrors[error].tests.add(test)
                gErrors[error].count_up(version)


def _checkForSuiteFailure(file, testsuite, testsuiteName, failedVersion):
    if testsuite.get('testsuite_failed') == 'True':
        testcaseName = 'setup'
        for failure in testsuite.findall('.//failure'):
            _addFailurePreliminary(file, testsuiteName, testcaseName,
                                   getFailMessage(failure.text), failedVersion)


def checkLogs(path, version):
    global gNewErrors, gErrors
    for file in os.listdir(path):
        if file.endswith(".xml"):
            root = ET.parse(path + '/' + file).getroot()

            for testsuite in root.findall('.//testsuite'):
                testsuiteName = str(testsuite.get('name'))
                if testsuite.get('skipped') != '0':
                    _checkForSuiteFailure(file, testsuite, testsuiteName, version)
                else:
                    for testcase in testsuite.findall('.//testcase'):
                        for failure in testcase.findall('.//failure'):
                            testcaseName = str(testcase.get('name'))
                            _addFailurePreliminary(file, testsuiteName,
                                                   testcaseName, getFailMessage(failure.text), version)

    print('Length of known error database = {}'.format(len(gErrors)))
    _processPreliminaryFailures(version)
    print('Potential error count = {}'.format(len(gNewErrors)))
    print('Update error database = {}'.format(len(gErrors)))


def writeFailsToFile(dataSavePath):
    global gErrors

    root = ET.Element("root")

    # processing gErrors
    xml = ET.SubElement(root, 'errors')
    for error, failure in gErrors.items():
        error = ET.SubElement(xml, 'error', msg=str(error),
                              count=str(failure.count), firstVersion=str(failure.firstVersion))
        tests = ET.SubElement(error, 'tests')
        for test in failure.tests:
            ET.SubElement(tests, "test", file=str(test.file), testsuite=str(test.testsuite),
                          testcase=str(test.testcase))
        versions = ET.SubElement(error, 'versions')
        for version in reversed(failure.lastVersions[-5:]):
            ET.SubElement(versions, "version", version=str(version))

    tree = ET.ElementTree(root)
    tree.write(f'{dataSavePath}/fails.xml')


def addTD(text, type=None):
    return f'<td {"" if type is None else type}> {text} </td>'


def createTable(errorBlocks, status, style):
    errorTable = ''

    for errorBlock in errorBlocks:
        errorTable += f'<tr>'
        # all failures in single block have the same errorID and failed version list
        errorTable += addTD(errorBlock[0], style)

        testsStr = '<details><summary>ALL</summary>'
        for test in sorted(errorBlock[1].tests):
            testsStr += f'{test}<br>'
        testsStr += '</details>'

        errorTable += addTD(testsStr)
        errorTable += addTD(status, style)
        errorTable += addTD(errorBlock[1].count, 'class="data" align="left"')

        errorTable += addTD(errorBlock[1].firstVersion)
        failedVersionsStr = ''
        for failedVersion in errorBlock[1].lastVersions:
            failedVersionsStr += f'{failedVersion}<br>'
        errorTable += addTD(failedVersionsStr)
        errorTable += f'</tr>'

    return errorTable


def createNewTable(newErrorList):
    return createTable(newErrorList, 'New', 'class="failed data"')


def createReplayTable(replayErrorList):
    return createTable(replayErrorList, 'Replay', 'class="replay data"')


def createOldTable(oldErrorList):
    return createTable(oldErrorList, 'Old', 'class="data"')


def addStyle():
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


def writeFailsToHTML(dataSavePath, version):
    # Group tests by failure + failed version list, otherwise create new entry
    # if defect failedVersion has id = len(totalFailedVersions) and len(defectFailedVersion) == 1, this is new defect
    # if defect failedVersion has id = len(totalFailedVersions) and len(defectFailedVersion) > 1, this is replay defect
    # otherwise this is old defect
    global gErrors

    newErrors = []
    replayErrors = []
    oldErrors = []

    for error, failure in gErrors.items():
        if failure.firstVersion == version and failure.count == 1:
            newErrors.append([error, failure])
        else:
            if version in failure.lastVersions:
                replayErrors.append([error, failure])
            else:
                oldErrors.append([error, failure])

    _writeFailsToHTML(newErrors, replayErrors, oldErrors, dataSavePath)


def _writeFailsToHTML(newErrors, replayErrors, oldErrors, dataSavePath):
    f = open(dataSavePath + '/reportSFManager.html', 'w')

    message = f'''<html>
    <head>
        {addStyle()}
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
            {createNewTable(newErrors)}
            {createReplayTable(replayErrors)}
            {createOldTable(oldErrors)}
        </table>
    </body>
    </html>'''

    f.write(message)
    f.close()


def doCheck(path, version, dataSavePath, generateReport=True):
    _cleanCommonVariables()

    if not os.path.isdir(path):
        print(f"Folder {path} does not exists!")
        return
    getOldFail(dataSavePath=dataSavePath)
    checkLogs(path=path, version=version)
    writeFailsToFile(dataSavePath=dataSavePath)
    if generateReport:
        writeFailsToHTML(dataSavePath=dataSavePath, version=version)


#def addArgs():
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
        dataSavePath = sys.argv[1]
        for iter in range(2, len(sys.argv) - 3, 2):
            doCheck(path=sys.argv[iter + 1], version=sys.argv[iter], dataSavePath=dataSavePath, generateReport=False)
        doCheck(path=sys.argv[-1], version=sys.argv[-2], dataSavePath=dataSavePath, generateReport=True)
        print('Done!')

    else:
        print('You must run the script with 3 or more parameters:\n'
              '1)Path for save result(should be the same for all runs)\n'
              '2)Name of run version,\n'
              '3)Folder names with logs\n'
              'Example: run.py <dataSavePath> <version 1> <folder 1> <version 2> <folder 2> ... <version N> <folder N>')
