import pexpect, os, re

class Account(object):
    def __init__(self, id: int, name:str, status:str ):
        self.id = id
        self.name = name
        self.status = status # "locked", "connected", "signed out"
        self.smtp = None
        self.imap = None

class Socket(object):
    def __init__(self, address, port, username, password, security):
        self.address = address
        self.port = port
        self.username = username
        self.password = password
        self.security = security

class ProtonmailBridge(object):
    def __init__(self, additional_flags='') -> pexpect.pty_spawn.spawn:
        self.proc = pexpect.spawnu(f'/usr/bin/protonmail-bridge --cli {additional_flags}')
        self.proc.sendline('')
        self.proc.expect('>>> ')

    def send_cmd(self, cmd: str) -> str:
        self.proc.sendline('')
        self.proc.sendline(cmd)
        # Empty prev buffer
        self.proc.expect(f"\r>>> {cmd}")
        # Get the output of the command (up to the next newline)
        self.proc.expect('\r>>>  \x08')
        return self.proc.before

    def is_ready(self) -> bool:
        accs = self.list_accounts()
        unready = [a for a in accs if a.status != 'connected']
        return len(unready) == 0

    def list_accounts(self, readyOnly= False) -> [Account]:
        accountsTxt = self.send_cmd('list')
        accounts = accountsTxt.split('\r\n')[2:-2]

        reg = r'(?P<number>\d+) : (?P<name>[a-zA-Z\d ]+[a-zA-Z]+)[ ]+\((?P<status>[a-zA-Z ]+[a-zA-Z]+)[ ]*, (?P<addr_mode>[a-zA-Z ]+[a-zA-Z]+)[ ]*\)'
        accs = []
        for account in accounts:
            r = re.search(reg, account)
            accNumber = r.group('number')
            accName = r.group('name')
            accStatus = r.group('status')
            accAddrMode = r.group('addr_mode')
            if readyOnly:
                if accStatus == "connected":
                    accs.append(Account(int(accNumber), accName, accStatus))
            else:
                accs.append(Account(int(accNumber), accName, accStatus))
        return accs

    def add_account(self, user:str, pwd:str):
        proc = self.proc
        proc.sendline('add')
        proc.expect('\r>>> add')
        proc.expect('Username: ')
        proc.sendline(user)
        proc.expect('Password: ')
        proc.sendline(pwd)
        proc.expect('Authenticating ...')
        proc.expect('Account (.+) was added successfully.|the user is already logged in') # `Account Name Surname was added successfully.`
        #reNames = proc.match.groups()
        #accName = reNames[0][4:-4]
        #print(f"Authenticated for user {accName}")
    
    def close_process_and_quit(self):
        proc = self.proc
        proc.stdin.close()
        proc.terminate()
        proc.wait(timeout=0.2)
        os.exit(0)

    def delete_account(self, number:int):
        proc = self.proc
        proc.sendline(f'delete {number}')
        proc.expect(f'\r>>> delete {number}')
        proc.expect("Are you sure you want to \\x1b\[1mremove account")
        proc.sendline('yes')
        proc.expect('\r>>>  \x08')

    def get_account_info(self, number) -> (Socket, Socket):
        proc = self.proc
        output = self.send_cmd(f"info {number}")
        output = output[output.find("Configuration for"):].split('\r\n\r\n')
        imapSettingsStr = output[0]
        smtpSettingsStr = output[1]
        reg = r"Address:\s*(?P<addr>[0-9.:]+)\r\n.*port:\s*(?P<port>\d+)\r\nUsername:\s*(?P<user>.+)\r\nPassword:\s*(?P<pass>.+)\r\nSecurity:\s*(?P<sec>[A-Z]+)"
        imapR = re.search(reg, imapSettingsStr, re.MULTILINE|re.IGNORECASE)
        imapS = Socket(imapR.group('addr'),imapR.group('port'),imapR.group('user'),imapR.group('pass'),imapR.group('sec'))

        smtpR = re.search(reg, smtpSettingsStr, re.MULTILINE|re.IGNORECASE)
        smtpS = Socket(smtpR.group('addr'),smtpR.group('port'),smtpR.group('user'),smtpR.group('pass'),smtpR.group('sec'))

        return (imapS, smtpS)
