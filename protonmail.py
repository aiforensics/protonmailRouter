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

def init_pmbridge() -> pexpect.pty_spawn.spawn:
    nl = '>>> '
    c = pexpect.spawnu('/usr/bin/protonmail-bridge --cli')
    c.sendline('')
    c.expect(nl)
    return c

def send_cmd(proc, cmd: str) -> str:
    proc.sendline('')
    proc.sendline(cmd)
    # Empty prev buffer
    proc.expect(f"\r>>> {cmd}")
    # Get the output of the command (up to the next newline)
    proc.expect('\r>>>  \x08')
    return proc.before

def is_ready(c) -> bool:
    accs = list_accounts(c)
    unready = [a for a in accs if a.status != 'connected']
    return len(unready) == 0

def list_accounts(c, readyOnly= False) -> [Account]:
    accountsTxt = send_cmd(c, 'list')
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

def add_account(proc, user, pwd):
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
    
def close_process_and_quit(proc):
    proc.stdin.close()
    proc.terminate()
    proc.wait(timeout=0.2)
    os.exit(0)

def delete_account(proc, number):
    proc.sendline(f'delete {number}')
    proc.expect(f'\r>>> delete {number}')
    proc.expect("Are you sure you want to \\x1b\[1mremove account")
    proc.sendline('yes')
    proc.expect('\r>>>  \x08')

def get_account_info(proc, number) -> (Socket, Socket):
    output = send_cmd(proc, f"info {number}")
    output = output[output.find("Configuration for"):].split('\r\n\r\n')
    imapSettingsStr = output[0]
    smtpSettingsStr = output[1]
    reg = r"Address:[ ]+(?P<addr>[0-9.:]+).*port:[ ](?P<port>\d+).*Username:[ ]+(?P<user>[a-zA-Z0-9.@_-]+).*Password:[ ]+(?P<pass>[a-zA-Z0-9]+)\r\nSecurity:[ ]+(?P<sec>[A-Z]+)"
    imapR = re.search(reg, imapSettingsStr, re.MULTILINE|re.DOTALL)
    imapS = Socket(imapR.group('addr'),imapR.group('port'),imapR.group('user'),imapR.group('pass'),imapR.group('sec'))

    smtpR = re.search(reg, smtpSettingsStr, re.MULTILINE|re.DOTALL)
    smtpS = Socket(smtpR.group('addr'),smtpR.group('port'),smtpR.group('user'),smtpR.group('pass'),smtpR.group('sec'))

    return (imapS, smtpS)
