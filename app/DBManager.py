import xml.etree.ElementTree as ET
import pymongo


class DBManager:

    def __init__(self):
        client = pymongo.MongoClient(
            "mongodb+srv://admin:admin@cluster0-d70d1.mongodb.net/test?retryWrites=true&w=majority")
        self.db = client['diploma']
        self.versions_col = self.db['versions-col6']

    def get_old_analyze(self, version=None):
        return self.versions_col.find_one(None if version is None else {'version': version})

    def save_analyze(self, version, failures):

        find_it = self.versions_col.find_one({'version': version})
        if find_it is None:
            failures_arr = []
            for error_msg, failure in failures:
                failures_arr.append({'error': str(error_msg),
                                     'failure': failure.do_serialize()})
            self.versions_col.insert_one({'version': version, 'failures': failures_arr})
        else:
            print('ERROR: version already exist.')
            print(find_it)
