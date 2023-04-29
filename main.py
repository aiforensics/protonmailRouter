import pexpect, os, re, time

def init_pmbridge() -> pexpect.pty_spawn.spawn:
    nl = '>>> '
    c = pexpect.spawnu('/usr/bin/protonmail-bridge --cli')
    c.expect(nl)
    c.sendline('')
    c.expect(nl)
    c.sendline('')
    return c

class Account(object):
    def __init__(self, id: int, name:str, status:str ):
        self.id = id
        self.name = name
        self.status = status # "locked", "connected", "signed out"
        self.smtp = None
        self.imap = None

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
    #proc.expect('>>> ')
    
    # # : account              (status         , address mode   )
    # 0 : ***REMOVED***         (connected      , combined       )
    #
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
    proc.sendline("***REMOVED***")
    proc.expect('Password: ')
    proc.sendline("***REMOVED***")
    proc.expect('Authenticating ...')
    proc.expect('Account (.+) was added successfully.|the user is already logged in') # Account ***REMOVED*** was added successfully.
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

#[a.name for a in list_accounts(c)]

class Socket(object):
    def __init__(self, address, port, username, password, security):
        self.address = address
        self.port = port
        self.username = username
        self.password = password
        self.security = security

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

#c = init_pmbridge()
#is_ready(c)
#


if __name__ == '__main__':
    import yaml, eml_parser
    config = None
    with open("config.yaml", "r") as stream:
        config = yaml.safe_load(stream)

    account = config['account']
    password = config['password']
    forwarding = {}
    for b in config['forwarding']:
        forwarding[b['address'].lower()] = b['recipients']
    print("Config file parsed")

    pb = init_pmbridge()
    print("Proton bridge started")
    ready = False

    import os 

    while not ready:
        ready = is_ready(pb)

        accounts = list_accounts(pb)
        if len(accounts) < 1:
            print("No accounts found. Adding account")
            add_account(pb, account, password)
            print(f"Added account {account}")
            ready = False
        time.sleep(2)
    
    print("Proton bridge initialized")

    imap, smtp = get_account_info(pb, 0)

    from imaplib import IMAP4
    from smtplib import SMTP
    import email

    M = IMAP4("127.0.0.1", int(imap.port))
    M.login(imap.username, imap.password) # ('OK', [b'[CAPABILITY IDLE IMAP4rev1 MOVE STARTTLS UIDPLUS UNSELECT] Logged in'])

    S = SMTP("127.0.0.1", int(smtp.port))
    S.ehlo()
    S.starttls()
    S.login(smtp.username, smtp.password) # (235, b'2.0.0 Authentication succeeded')

    print('Login successful. Opening mailbox and starting loop...')
    M.select('Inbox')
    while True:
        typ, data = M.search(None,'(UNSEEN)')
        
        for num in data[0].split():
            typ, data = M.fetch(num,'(BODY[HEADER.FIELDS (To)] BODY[HEADER.FIELDS (Cc)] BODY[HEADER.FIELDS (Bcc)] BODY[HEADER.FIELDS (Subject)] RFC822)') # num is a byte, https://www.rfc-editor.org/rfc/rfc3501
            
            #print(data)
            #to = data[1][1].decode('utf-8').strip()
            #if len(to) > 4:
            #    to = to[4:].split(',')
            #cc = data[2][1].decode('utf-8').strip()
            #if len(cc) > 4:
            #    cc = cc[4:].split(',')
            #bcc = data[3][1].decode('utf-8').strip() # b'\r\n'
            #subject = data[4][1].decode('utf-8').strip() # b'Subject: Re: This is a test for the auto-forward (4)\r\n\r\n'
            body = data[5][1]
            ep = eml_parser.EmlParser()
            parsed_eml = ep.decode_email_bytes(body)
            
            from_ = subject = ""
            to = cc = []
            if 'from' in parsed_eml['header']:
                from_ = parsed_eml['header']['from']
            if 'subject' in parsed_eml['header']:
                subject = parsed_eml['header']['subject']
            if 'to' in parsed_eml['header']:
                to = parsed_eml['header']['to']
            if 'cc' in parsed_eml['header']:
                cc = parsed_eml['header']['cc']

            dest = set(to)
            dest.update(cc)

            newDest = set()
            for d in dest:
                if d in forwarding:
                    newDest.update(forwarding[d])
            newDest = list(newDest)
            if len(newDest) == 0:
                continue # The mail has already been marked as read by the RFC field
            newDest = ', '.join([f"<{a}>" for a in newDest])

            old_msg = email.message_from_string(body.decode('utf-8'))
            forwarding_msg = email.message.Message()
            forwarding_msg['From'] = smtp.username
            forwarding_msg['To'] = newDest
            forwarding_msg['Subject'] = 'Fwd: ' + subject

            #forwarding_msg.set_content(f'Forwarded email from {from_} :\n\n' + body.decode('utf-8').strip())
            newPayload = []
            if old_msg.is_multipart():
                for payload in old_msg.get_payload():
                    print("Payload charset:", payload.get_charset(), payload.get_content_type())
                    break_ = "\n"
                    #if payload.get_content_type() == 'text/html':
                    #    break_ = '<br/><br/><br/>'
                    newPayload.append(f"Forwarded email from {from_} :{break_}{payload}")
            else:
                #print forwarding_msg.get_payload()
                break_ = "\n"
                #if old_msg.get_content_type() == 'text/html':
                #    break_ = '<br/><br/><br/>'
                newPayload = f"Forwarded email from {from_} :{break_}{old_msg.get_payload()}"
            forwarding_msg.set_payload(newPayload)

            print(f"Got mail \"{subject}\" from <{from_}>; sending to {newDest}")
            #S.send_message(forwarding_msg)

            # Set read flag
            #typ, data = M.store(num,'+FLAGS','\\Seen')
        
        sleepTime = 10
        print(f"Mailbox checked. Checking again in {sleepTime}s")
        time.sleep(sleepTime)