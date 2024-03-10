import protonbridge as pb
import mail_protocols as mp
import config as cfg
import time
from email.message import Message
from email.utils import getaddresses
from dataclasses import dataclass
from parsed_message import ParsedMessage
from typing import List

@dataclass
class context:
    imap: mp.SMTPClient
    smtp: mp.IMAPClient
    distribution_list: dict

"""
routeEmail takes in a context (imap and smtp clients, distribution list) and a mail message.
It elaborates the message, forwarding it to the proper distribution list, and then proceeds to read the message and forward it
"""
def routeEmail(ctx:context, incoming_email_message: Message):
    incoming = ParsedMessage(incoming_email_message)
    try:
        destination_distribution_list = getMailingList(incoming, ctx.distribution_list)
    except:
        print(f"Got mail from ${incoming.sender} directed to ${incoming.all_recipients} and couldn't find a proper list. Skipping.")
        ctx.imap.readMail(incoming_email_message.number)
        return
    # recipients = getRecipients(incoming, ctx.distribution_list)
    recipients = ctx.distribution_list[destination_distribution_list]
    
    # Somehow we don't have recipients, drop the message
    if len(recipients) == 0:
        # We drop the message by reading it: the following loop cycle will ignore it.
        ctx.imap.readMail(incoming_email_message.number)
        return
    
    outgoing = incoming_email_message
    # Remove from the original message all the header that might cause issues
    [outgoing.__delitem__(header) for header in ["Sender", "Cc"]]
    
    # Set the new headers to forward the message to the addresses in the distribution list
    outgoing.replace_header("From", destination_distribution_list)

    if incoming_email_message.get_all("To") is None:
        # If we got here, we (probably) are in the infamous "Undisclosed Recipients" case

        # set_raw is probably incorrect here, but idk what else to use
        outgoing.set_raw("To", ", ".join(recipients))
    else:
        outgoing.replace_header("To", ", ".join(recipients))

    outgoing.replace_header("Subject", f"{incoming.sender} -> {destination_distribution_list}: {incoming.subject}")

    print(f"Got mail \"{incoming.subject}\" from \"{incoming.sender[0]}\" ({incoming.sender[1]}); sending to {recipients}")

    # Forward the message
    ctx.smtp.sendMessage(outgoing)

    # Set read flag so we don't reprocess the message
    ctx.imap.readMail(incoming_email_message.number)
    # Archive the mail to have a clean & neat inbox
    ctx.imap.archiveMail(incoming_email_message.number)

"""
getRecipients returns a list of all the recipients in the message (to, cc, bcc)
It also removes any message recipients that also happen to be in the distribution list 
"""
def getRecipients(message:ParsedMessage, distribution_list: dict) -> List[str]:
    recipients = set()
    for recipient_name, recipient_email in message.all_recipients:
        recipient_email = recipient_email.strip().lower()
        if recipient_email in config.distribution_list:
            recipients.update(config.distribution_list[recipient_email])

    for addr in distribution_list.keys():
        try:
            recipients.remove(addr) # Removes from the set all the aliases, to avoid a loop
        except Exception:
            pass
    recipients = list(recipients)
    return recipients


"""
getMailingList returns the mail address of the first distribution list it finds in the recipients.
This will be the account/alias the the mail will be re-forwarded from
For our usecase it's reasonable to think that only one distribution list at the time will receive messages
"""
def getMailingList(message: ParsedMessage, distribution_list: dict) -> str:
    for (_, addr) in message.all_recipients:
        dest_address = addr.strip().lower()
        if dest_address in distribution_list:
            return dest_address
    # Some emails can have "Undisclosed Recipients", but they apparently have this "Delivered-To"
    #   header which contains the intended destination, so we might recur to that I guess...
    deliverTo = message.original.get_all("Delivered-To")
    if deliverTo is not None:
        for address in deliverTo:
            dest_address = address.strip().lower()
            if dest_address in distribution_list:
                return dest_address 
    raise ValueError('Unable to find a distribution list in the provided message and distribution list', message.all_recipients)


if __name__ == '__main__':
    config = cfg.Config()
    print("Config file parsed")

    bridge = pb.ProtonmailBridge()
    print("Proton bridge process started")
    bridge.login_and_boostrap(config.account, config.password)
    print("Proton bridge operative")

    imap, smtp = bridge.get_account_info(0)
    imap = mp.IMAPClient(imap.address, imap.port, imap.security.upper() == 'STARTTLS', imap.username, imap.password)
    smtp = mp.SMTPClient(smtp.address, smtp.port, smtp.security.upper() == 'STARTTLS', smtp.username, smtp.password)
    print("IMAP and SMTP clients initialized. Starting ProtonRouter!")
    ctx = context(imap, smtp, config.distribution_list)

    while True:
        # We keep track of the read addresses by filtering the unread ones
        # The mailbox is supposed to be unattended, so all the non-matching messages will remain in the inbox folder
        for mail in imap.getUnreadEmailsIter():
            routeEmail(ctx, mail)
        time.sleep(config.sleepTime)
