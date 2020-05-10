import Levenshtein
import re

threshold = 0.9
ignoredChars = ' \t\n'


class Error:
    def __init__(self, msg):
        self.msg = Error.msgNoHTTPError(Error.msgNoQueries(msg))
        self.msgTransformed = Error.applyTransformations(msg)

    def __str__(self):
        return self.msg

    def __repr__(self):
        return self.msg

    def __eq__(self, other):
        # we do not need to calculate ratio for significantly different messages
        if Error.messagesAreDefinitelyDifferent(self.msgTransformed, other.msgTransformed):
            return False
        return Levenshtein.ratio(self.msgTransformed, other.msgTransformed) > threshold

    def __hash__(self):
        return hash(self.msgTransformed)

    @staticmethod
    def applyTransformations(message):
        for transformation in [Error.msgNoHTTPError, Error.msgNoQueries, Error.msgNoGUID,
                               Error.msgNoTIMEOUT_MessageNumber, Error.msgNoIgnoredChars,  # , Error.msgNoNumber
                               Error.msgNoPrefix]:
            message = transformation(message)
        return message

    @staticmethod
    def messagesAreDefinitelyDifferent(message1, message2):
        # we consider messages different, if their relative size difference is more than (1 - threshold)
        possibleDifferencePercent = (1.0 - threshold) / 2
        return not (0.5 + possibleDifferencePercent >=
                    len(message1) / (len(message1) + len(message2)) >=
                    0.5 - possibleDifferencePercent)

    @staticmethod
    def msgNoGUID(message):
        guids = re.findall(r'(\w{8}-\w{4}-\w{4}-\w{4}-\w{12})', message)
        for i in guids:
            message = message.replace(i, 'XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX')
        return message

    @staticmethod
    def msgNoTIMEOUT_MessageNumber(message):
        if message.find('TIMEOUT/Message number:') > -1:
            secondPart = message \
                .replace(r'*.TIMEOUT/Message number: ', '') \
                .replace(r" - Application message don't come*.", '')
            return message.replace(secondPart, 'X/XX')
        else:
            return message

    @staticmethod
    def msgNoIgnoredChars(message):
        return message.translate({ord(c): None for c in ignoredChars})

    @staticmethod
    def msgNoQueries(message):
        # we do not want to compare query outputs with each other automatically, it is extremely slow
        if message.find('xml version') != -1:
            message = 'Query error'
        return message

    # try without nemoving number from message
    # @staticmethod
    # def msgNoNumber(message):
    #   return ''.join([i for i in message if not i.isdigit()])

    @staticmethod
    def msgNoHTTPError(message):
        if message.find('urllib.error.HTTPError: HTTP Error 500: Internal Server Error') != -1:
            message = 'HTTP Error 500: Internal Server Error'
        if message.find('urllib.error.HTTPError: HTTP Error 401: Unauthorized') != -1:
            message = 'HTTP Error 401: Unauthorized'
        return message

    @staticmethod
    def msgNoPrefix(message):
        return message.replace('CQG_', '')
