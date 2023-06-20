import protonbridge as pb
import mail_protocols as mp
import yaml, email, time

if __name__ == '__main__':
    config = None
    with open("config.yaml", "r") as stream:
        config = yaml.safe_load(stream)
    account = config['account']
    password = config['password']
    check_interval:int = config['checkIntervalMinutes']
    sleepTime = check_interval * 60
    incoming_to_intended = {}
    for b in config['forwarding']:
        incoming_to_intended[b['address'].lower()] = b['recipients']
    print("Config file parsed")

    bridge = pb.ProtonmailBridge()
    print("Proton bridge started")
    ready = False
    while not ready:
        ready = bridge.is_ready()
        accounts = bridge.list_accounts()
        if len(accounts) < 1:
            print("No accounts found. Adding account")
            bridge.add_account(account, password)
            print(f"Added account {account}")
            ready = False
        time.sleep(2)
    print("Proton bridge initialized")

    imap, smtp = bridge.get_account_info(0)
    imap = mp.IMAPClient(imap.address, imap.port, imap.security.upper() == 'STARTTLS', imap.username, imap.password)
    smtp = mp.SMTPClient(smtp.address, smtp.port, smtp.security.upper() == 'STARTTLS', smtp.username, smtp.password)
    print("IMAP and SMTP clients initialized. Starting ProtonRouter!")

    print("""
______          _             ______            _            
| ___ \        | |            | ___ \          | |           
| |_/ / __ ___ | |_ ___  _ __ | |_/ /___  _   _| |_ ___ _ __ 
|  __/ '__/ _ \| __/ _ \| '_ \|    // _ \| | | | __/ _ \ '__|
| |  | | | (_) | || (_) | | | | |\ \ (_) | |_| | ||  __/ |   
\_|  |_|  \___/ \__\___/|_| |_\_| \_\___/ \__,_|\__\___|_|   
""")

    while True:
        for incoming in imap.getUnreadEmailsIter():

            incoming_sender = incoming.get_all('from', [])[0]
            incoming_subject = incoming['Subject']

            incoming_tos = incoming.get_all('to', [])
            incoming_ccs = incoming.get_all('cc', [])
            incoming_resent_tos = incoming.get_all('resent-to', [])
            incoming_resent_ccs = incoming.get_all('resent-cc', [])
            incoming_recipients = email.utils.getaddresses(incoming_tos + incoming_ccs + incoming_resent_tos + incoming_resent_ccs)

            outgoing_recipients = set()
            outgoing_from = ""
            for recipient_name, recipient_email in incoming_recipients:
                if recipient_email in incoming_to_intended:
                    outgoing_recipients.update(incoming_to_intended[recipient_email])
                    outgoing_from = recipient_email
            outgoing_recipients = list(outgoing_recipients)
            if len(outgoing_recipients) == 0:
                imap.readMail(incoming.number)
                continue 
            
            #outgoing = email.message.Message()
            outgoing = incoming
            #outgoing['From'] =  # outgoing_from # smtplib.SMTPDataError: (554, b'5.0.0 Error: transaction failed, blame it on the weather: invalid return path')
            outgoing.replace_header("From", account)
            outgoing.replace_header("To", ", ".join(outgoing_recipients))
            outgoing.replace_header("Subject", f"{incoming_sender} -> {incoming_tos[0]} : {incoming_subject}")
            outgoing.add_header('X-Original-To', incoming_sender)
            outgoing.add_header('Delivered-To', incoming_sender)

            print(f"Got mail \"{incoming_subject}\" from {incoming_sender[0]} ({incoming_sender[1]}); sending to {outgoing_recipients}")
            smtp.sendMessage(outgoing)
            # Set read flag so we don't reprocess the message
            imap.readMail(incoming.number)
            imap.archiveMail(incoming.number)
        
        time.sleep(sleepTime)