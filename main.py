
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
            # This is potentially dangerous, as fetching the body marks the message as read.
            # Marking the message as read means that if an error is thrown, the message is not reprocessed
            typ, data = M.fetch(num,'(RFC822)') # num is a byte, https://www.rfc-editor.org/rfc/rfc3501
            # Re-put unseen flag
            M.store(num,'-FLAGS','\\Seen')

            body = data[0][1]
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
                M.store(num,'+FLAGS','\\Seen')
                continue 
            
            newDest = ', '.join([f"<{a}>" for a in newDest])

            old_msg = email.message_from_string(body.decode('utf-8'))
            forwarding_msg = email.message.Message()
            forwarding_msg['From'] = smtp.username
            forwarding_msg['To'] = newDest
            forwarding_msg['Subject'] = 'Fwd: ' + subject

            newPayload = []
            # TODO: We need to handle if the message is HTML or not (the line breaks are affected)
            if old_msg.is_multipart():
                for payload in old_msg.get_payload():
                    print("Payload charset:", payload.get_charset(), payload.get_content_type())
                    break_ = "\n"
                    newPayload.append(f"Forwarded email from {from_} :{break_}{payload}")
            else:
                break_ = "\n"
                newPayload = f"Forwarded email from {from_} :{break_}{old_msg.get_payload()}"
            forwarding_msg.set_payload(newPayload)

            print(f"Got mail \"{subject}\" from <{from_}>; sending to {newDest}")
            S.send_message(forwarding_msg)

            # Set read flag so we don't reprocess the message
            M.store(num,'+FLAGS','\\Seen')
        
        sleepTime = 10
        print(f"Mailbox checked. Checking again in {sleepTime}s")
        time.sleep(sleepTime)