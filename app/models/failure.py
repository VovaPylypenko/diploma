class Failure:
    def __init__(self, tests_new, tests_replay, tests_old, first_version, count, last_versions):
        self.tests_new = tests_new
        self.tests_replay = tests_replay
        self.tests_old = tests_old
        self.count = count
        self.first_version = first_version
        self.last_versions = last_versions

    def __eq__(self, other):
        return self.tests_new == other.tests_new \
               and self.tests_replay == other.tests_replay \
               and self.tests_old == other.tests_old \
               and self.count == other.count \
               and self.first_version == other.first_version \
               and self.last_versions == other.last_versions

    def __str__(self):
        return '{} {} {} {} ({}, {})'.format(self.tests_new, self.tests_replay, self.tests_old,
                                             self.count, self.first_version, self.last_versions)

    def __repr__(self):
        return self.__str__()

    def count_up(self, new_version):
        if new_version not in self.last_versions:
            self.count += 1
            self.last_versions.append(new_version)

    def add_test(self, new_test):
        if new_test in self.tests_old:
            print('ADD REPLAY')
            self.tests_replay.add(new_test)
            self.tests_old.remove(new_test)
        else:
            print('ADD NEW')
            self.tests_new.add(new_test)
