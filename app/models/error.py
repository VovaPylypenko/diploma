import Levenshtein
import re

threshold = 0.9
ignored_chars = ' \t\n'


class Error:
    def __init__(self, msg):
        self.msg = self.msg_no_HTTPError(self.msg_no_GUID(msg))
        self.msg_transformed = self.apply_transformations(msg)

    def __str__(self):
        return self.msg

    def __repr__(self):
        return self.msg

    def __eq__(self, other):
        # we do not need to calculate ratio for significantly different messages
        if self.messages_definitely_different(self.msg_transformed, other.msg_transformed):
            return False
        return Levenshtein.ratio(self.msg_transformed, other.msg_transformed) > threshold

    def __hash__(self):
        return hash(self.msg_transformed)

    def apply_transformations(self, message):
        for transformation in [self.msg_no_HTTPError, self.msg_no_GUID, self.msg_no_GUID,
                               self.msg_no_TIMEOUT_message_number, self.msg_no_ignored_chars,  # , Error.msgNoNumber
                               self.msg_no_prefix]:
            message = transformation(message)
        return message

    def messages_definitely_different(self, message1, message2):
        # we consider messages different, if their relative size difference is more than (1 - threshold)
        possible_difference_percent = (1.0 - threshold) / 2
        return not (0.5 + possible_difference_percent >=
                    len(message1) / (len(message1) + len(message2)) >=
                    0.5 - possible_difference_percent)

    def msg_no_GUID(self, message):
        guids = re.findall(r'(\w{8}-\w{4}-\w{4}-\w{4}-\w{12})', message)
        for i in guids:
            message = message.replace(i, 'XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX')
        return message

    def msg_no_TIMEOUT_message_number(self, message):
        if message.find('TIMEOUT/Message number:') > -1:
            second_part = message \
                .replace(r'*.TIMEOUT/Message number: ', '') \
                .replace(r" - Application message don't come*.", '')
            return message.replace(second_part, 'X/XX')
        else:
            return message

    def msg_no_ignored_chars(self, message):
        return message.translate({ord(c): None for c in ignored_chars})

    def msg_no_queries(self, message):
        # we do not want to compare query outputs with each other automatically, it is extremely slow
        if message.find('xml version') != -1:
            message = 'Query error'
        return message

    # try without nemoving number from message
    # @staticmethod
    # def msgNoNumber(message):
    #   return ''.join([i for i in message if not i.isdigit()])

    def msg_no_HTTPError(self, message):
        if message.find('urllib.error.HTTPError: HTTP Error 500: Internal Server Error') != -1:
            message = 'HTTP Error 500: Internal Server Error'
        if message.find('urllib.error.HTTPError: HTTP Error 401: Unauthorized') != -1:
            message = 'HTTP Error 401: Unauthorized'
        return message

    def msg_no_prefix(self, message):
        return message.replace('CQG_', '')
