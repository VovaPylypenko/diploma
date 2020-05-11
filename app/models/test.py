class Test:
    def __init__(self, file, test_suite, test_case):
        self.file = file
        self.test_suite = test_suite
        self.test_case = test_case

    def __eq__(self, other):
        return self.file == other.file \
               and self.test_suite == other.test_suite \
               and self.test_case == other.test_case

    def __hash__(self):
        return hash((self.file, self.test_suite, self.test_case))

    def __str__(self):
        return '{}/{}.{}'.format(self.file, self.test_suite, self.test_case)

    def __repr__(self):
        return self.__str__()

    def __lt__(self, other):
        return self.__str__() < str(other)
