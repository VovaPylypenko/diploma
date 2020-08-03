import xml.etree.ElementTree as ET
import os

from app.models.error import Error
from app.models.test import Test
from app.models.failure import Failure


class DataManager:

    def _get_errors_from_XML(self, root):
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

    def get_old_analyze(self, data_save_path):
        path = data_save_path + '/fails.xml'
        # TBD: copy old fails.xml with timestamp to have version history? Or add timestamp to xml file as version?
        if not os.path.exists(path):
            with open(path, 'w'):
                pass
        if os.stat(path).st_size == 0:
            return {}
        tree = ET.parse(path)
        root = tree.getroot()

        return self._get_errors_from_XML(root)

    def save_analyze(self, data_save_path, failures):

        root = ET.Element("root")

        # processing gERRORS
        xml = ET.SubElement(root, 'errors')
        for error_msg, failure in failures:
            error = ET.SubElement(xml, 'error', msg=str(error_msg),
                                  count=str(failure.count), first_version=str(failure.first_version))
            tests = ET.SubElement(error, 'tests')
            for test in failure.tests:
                ET.SubElement(tests, "test", file=str(test.file), test_suite=str(test.test_suite),
                              test_case=str(test.test_case))
            versions = ET.SubElement(error, 'versions')
            for version in reversed(failure.last_versions[-5:]):
                ET.SubElement(versions, "version", version=str(version))

        tree = ET.ElementTree(root)
        tree.write(data_save_path + '/fails.xml')
