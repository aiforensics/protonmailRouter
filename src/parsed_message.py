from email.utils import getaddresses
from email.message import Message


class ParsedMessage:
    def __init__(self, mail: Message):
        self.sender = getaddresses(mail.get_all('from', []))[0]
        self.subject = mail['Subject']

        self.tos = mail.get_all('to', [])
        self.ccs = mail.get_all('cc', [])
        self.resent_tos = mail.get_all('resent-to', [])
        self.resent_ccs = mail.get_all('resent-cc', [])

        self.all_recipients = getaddresses(self.tos + self.ccs + self.resent_tos + self.resent_ccs)

        # self.tos = getaddresses(tos)
