import os
import xml.etree.ElementTree as ET
from app.models.error import Error
from app.models.test import Test
from app.models.failure import Failure
from app.reportGenerator import ReportGenerator
from app.argumentManager import ArgumentManager
from app.parserLogs import ParserLogManager
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
    global gERRORS

    gERRORS = {}  # map: Error <-> list<Failure>


def _get_errors_from_DB(data):
    errors = {}

    if data is not None:
        for failure in data['failures']:
            errors[Error(failure['error'])] = Failure(data=failure['failure'])

    return errors


def get_old_fail(version4analyze):
    global gERRORS

    db_manager = DBManager()
    gERRORS = _get_errors_from_DB(db_manager.get_old_analyze(version=
                                                             version4analyze if version4analyze is not None else None))


def save_errors(version=None):
    global gERRORS

    db_manager = DBManager()
    db_manager.save_analyze(version, gERRORS.items())


def pars_and_check(path, version):
    global gERRORS

    ParserLogManager.check_logs(path, version, gERRORS)


def do_check(path, version, data_save_path, version4analyze, generate_report=False):
    _clean_common_variables()

    if not os.path.isdir(path):
        print(f"Folder {path} does not exists!")
        return
    get_old_fail(None if (version4analyze is None or version4analyze == 'last') else version4analyze)
    pars_and_check(path=path, version=version)
    save_errors(version=version)
    if generate_report:
        ReportGenerator.write_fails_2_HTML(gERRORS=gERRORS, data_save_path=data_save_path, version=version)


def run():
    print('Starting SF Manager Result...')
    argsManager = ArgumentManager()

    do_check(argsManager.get_path_logs(), argsManager.get_version(), argsManager.get_path2save(),
             argsManager.get_version4analyze(), argsManager.get_need_save())

    print('Done!')
    print('file:///Users/vova/Duplom/ManagerResultTool/result/reportSFManager.html')


if __name__ == '__main__':
    run()
