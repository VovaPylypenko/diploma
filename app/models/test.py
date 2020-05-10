class Test:
    def __init__(self, file, testsuite, testcase):
        self.file = file
        self.testsuite = testsuite
        self.testcase = testcase

    def __eq__(self, other):
        return self.file == other.file \
               and self.testsuite == other.testsuite \
               and self.testcase == other.testcase

    def __hash__(self):
        return hash((self.file, self.testsuite, self.testcase))

    def __str__(self):
        return '{}/{}.{}'.format(self.file, self.testsuite, self.testcase)

    def __repr__(self):
        return self.__str__()

    def __lt__(self, other):
        return self.__str__() < str(other)
