import protonbridge as pb
import mail_protocols as mp
import yaml, email, time

if __name__ == '__main__':
    config = None
    with open("config.yaml", "r") as stream:
        config = yaml.safe_load(stream)
    account = config['account']
    password = config['password']
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

    while True:
        for incoming in imap.getUnreadEmailsIter():

            incoming_sender = mp.getAddressesFromHeader(incoming['From'])[0]
            incoming_subject = incoming['Subject']
            incoming_to = mp.getAddressesFromHeader(incoming['To'])
            incoming_cc = mp.getAddressesFromHeader(incoming['Cc'])

            incoming_recipients = set(incoming_to)
            incoming_recipients.update(incoming_cc)
            outgoing_recipients = set()
            outgoing_from = ""
            for mail_recipient in incoming_recipients:
                if mail_recipient in incoming_to_intended:
                    outgoing_recipients.update(incoming_to_intended[mail_recipient])
                    outgoing_from = mail_recipient
            outgoing_recipients = list(outgoing_recipients)
            if len(outgoing_recipients) == 0:
                imap.readMail(incoming.number)
                continue 
            
            outgoing = email.message.Message()
            outgoing['From'] = outgoing_from
            outgoing['To'] = ', '.join([f"<{a}>" for a in outgoing_recipients])
            outgoing['Subject'] = incoming_sender + ': ' + incoming_subject
            outgoing['Reply-To'] = incoming_sender
            #outgoing['Return-Path'] = 'mailadmin@mail.com' # Define the return path address in the settings

            outgoing_payload = []
            # TODO: We need to handle if the message is HTML (by checking the Content-Type. Try looking in the headers) or not (the line breaks are affected)
            #print("Conent type:", incoming['Content-Type']) # text/plain; charset=utf-8
            if incoming.is_multipart():
                for payload in incoming.get_payload():
                    print("Payload charset:", payload.get_charset(), payload.get_content_type())
                    line_break = "\n"
                    outgoing_payload.append(f"Forwarded email from {incoming_sender} :{line_break}{payload}")
            else:
                line_break = "\n"
                outgoing_payload = f"Forwarded email from {incoming_sender} :{line_break}{incoming.get_payload()}"
            outgoing.set_payload(outgoing_payload)

            print(f"Got mail \"{incoming_subject}\" from {incoming_sender}; sending to {outgoing_recipients}")
            smtp.sendMessage(outgoing)
            # Set read flag so we don't reprocess the message
            imap.readMail(incoming.number)
        
        sleepTime = 10
        print(f"Mailbox checked. Checking again in {sleepTime}s")
        time.sleep(sleepTime)