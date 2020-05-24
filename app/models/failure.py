from app.models.test import Test


class Failure:
    def __init__(self, tests=None, first_version=None, count=None, last_versions=None, data=None):
        if data is not None:
            self.tests = set()
            for test_it in data['tests']:
                self.tests.add(Test(test_it['file'], test_it['test_suite'], test_it['test_case']))
            self.count = data['count']
            self.first_version = data['first_version']
            self.last_versions = data['last_versions']
        else:
            self.tests = tests
            self.count = count
            self.first_version = first_version
            self.last_versions = last_versions

    def __eq__(self, other):
        return self.tests == other.tests \
               and self.count == other.count \
               and self.first_version == other.first_version \
               and self.last_versions == other.last_versions

    def __str__(self):
        return '{} {} ({}, {})'.format(self.tests, self.count, self.first_version, self.last_versions)

    def __repr__(self):
        return self.__str__()

    def count_up(self, new_version):
        if new_version not in self.last_versions:
            self.count += 1
            self.last_versions.append(new_version)

    def add_test(self, new_test):
        self.tests.add(new_test)

    def do_serialize(self):
        tests_arr = []
        for test_it in self.tests:
            tests_arr.append(test_it.do_serialize())
        return {
            'tests': tests_arr,
            'count': self.count,
            'first_version': self.first_version,
            'last_versions': self.last_versions,
        }
