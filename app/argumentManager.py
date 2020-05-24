import argparse


class ArgumentManager:

    def __init__(self):
        ap = argparse.ArgumentParser()
        ap.add_argument('version', type=str, help='Name of run version')
        ap.add_argument('path_logs', type=str, help='Path to logs')
        ap.add_argument('-version4analyze', type=str, default='last', help='.(default last)')
        ap.add_argument('-path2save', type=str, default='/', help='Path to save result.(default /)')
        ap.add_argument('-need_save', type=bool, default=True,
                        help="Set True if this analyze need save.(default False)")

        args = vars(ap.parse_args())

        self.version = args['version']
        self.path_logs = args['path_logs']
        self.version4analyze = args['version4analyze']
        self.path2save = args['path2save']
        self.need_save = args['need_save']

    def get_version(self):
        return self.version

    def get_path_logs(self):
        return self.path_logs

    def get_version4analyze(self):
        return self.version4analyze

    def get_path2save(self):
        return self.path2save

    def get_need_save(self):
        return self.need_save
