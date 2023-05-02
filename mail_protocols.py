
from imaplib import IMAP4
from smtplib import SMTP
import email, re

class IMAPClient(object):
    def __init__(self, host:str, port:int, start_tsl:bool, username:str, password:str, default_folder:str='Inbox'):
        self.client = IMAP4(host, port)
        if start_tsl:
            self.client.starttls()
        if username and password:
            self.client.login(username, password) # ('OK', [b'[CAPABILITY IDLE IMAP4rev1 MOVE STARTTLS UIDPLUS UNSELECT] Logged in'])
        self.client.select(default_folder)
        self.default_folder = default_folder
    
    def changeFolder(self, folder:str = 'Inbox'):
        self.client.select(folder)

    def getUnreadEmails(self) -> [email.message.Message]:
        return [m for m in getUnreadEmailsIter()]
    
    def getUnreadEmailsIter(self) -> email.message.Message:
        for mail in self.getEmailsIter('(UNSEEN)'):
            yield mail

    def getEmails(self, filter:str='()') -> [email.message.Message]:
        return [m for m in getEmailsIter(filter)]

    def getEmailsIter(self, filter:str='()') -> email.message.Message:
        res, data = self.client.search(None,filter)
        if res != 'OK':
            return
        for num in data[0].split():
            # Getting the whole body sets the '\Seen' flag.
            # We don't want that: we want instead the flag to be set manually
            # https://www.rfc-editor.org/rfc/rfc3501
            res, fetchedMsg = self.client.fetch(num, '(RFC822)')
            if res != 'OK':
                print("IMAP server replied to mail fetch with NOT ok status. Reported status: ", res, ". Skipping.")
                continue
            self.unreadMail(num)

            mailIndex = -1
            # I requested only one message: it's probably fine to just get the first tuple corresponding
            #   to the first message
            for i, response_part in enumerate(fetchedMsg):
                if isinstance(response_part, tuple) and str(response_part).find("RFC822") != -1:
                    mailIndex = i
                    
            if mailIndex == -1:
                print("Error: should have got a mail, but apparently I found no message in the IMAP response data")
                continue

            messageBodyBytes = fetchedMsg[mailIndex][1]
            if type(messageBodyBytes) is not bytes:
                print("Error encountered. Message body was expected to be bytes, got '{type}'. Value: {content}{ellipsis}".format(type=type(messageBodyBytes), content=str(messageBodyBytes)[0:100], ellipsis= '...' if len(str(messageBodyBytes)) > 100 else '' ))
                print(fetchedMsg)
                continue
            mail = email.message_from_bytes(messageBodyBytes)
            mail.number = num
            yield mail

    def unreadMail(self, mailNumber:str):
        return self.removeMailFlag(mailNumber, '\\Seen')

    def readMail(self, mailNumber:str):
        return self.addMailFlag(mailNumber, '\\Seen')

    def addMailFlag(self, mailNumber:str, flags:str):
        return self.client.store(mailNumber, '+FLAGS', flags)

    def removeMailFlag(self, mailNumber:str, flags:str):
        return self.client.store(mailNumber, '-FLAGS', flags)


class SMTPClient(object):
    def __init__(self, host:str, port:int, start_tsl:bool, username:str, password:str):
        self.client = SMTP(host, port)
        self.client.ehlo()
        if start_tsl:
            self.client.starttls()
        self.client.login(username, password) # (235, b'2.0.0 Authentication succeeded')
    
    def sendMessage(self, message: email.message.Message):
        self.client.send_message(message)

def getAddressesFromHeader(addresses:str) -> [str]:
    regex = r"<?(?P<mail>[a-z0-9_+-]+@[a-z0-9_-]+\.[a-z]+)>?"
    mails = re.findall(regex, addresses, re.MULTILINE | re.IGNORECASE)
    for i,_ in enumerate(mails):
        if mails[i][0] == '<':
            mails[i] = mails[i][1:-1]
    return mails