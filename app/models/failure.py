class Failure:
    def __init__(self, tests, firstVersion, count, lastVersions):
        self.tests = tests
        self.count = count
        self.firstVersion = firstVersion
        self.lastVersions = lastVersions

    def __eq__(self, other):
        return self.tests == other.tests \
               and self.count == other.count \
               and self.firstVersion == other.firstVersion \
               and self.lastVersions == other.lastVersions

    def __str__(self):
        return '{} {} ({}, {})'.format(self.tests, self.count, self.firstVersion, self.lastVersions)

    def __repr__(self):
        return self.__str__()

    def count_up(self, newVersion):
        if newVersion not in self.lastVersions:
            self.count += 1
            self.lastVersions.append(newVersion)

    def addTest(self, newTest):
        self.tests.add(newTest)
