# ProtonmailRouter

> ⚠️ This is a relatively fragile piece of software.  

> 💲 A paid ProtonMail plan is needed for this to work, as this is based on 
[ProtonMail Bridge](https://github.com/ProtonMail/proton-bridge).

Now that disclaimers are out the way:  
ProtonmailRouter is a piece of software to emulate 
[distribution lists](https://en.wikipedia.org/wiki/Distribution_list) in [Protonmail](https://proton.me/).  
We employ a generic mailbox with many aliases and then forward incoming mail to the intended recipients
based on the targeted alias.  

## Motivation
At AI Forensics (and formerly at Tracking.Exposed) we tend to have a flat hierarchy.  
This implies that we frequently use a generic mailbox (e.g. `workgroup@example.com` 
or `team@example.com`) for both external and internal communications.  

At the time of writing, ProtonMail does not provide a way to have distribution lists out of the box  
> which (in the author's point of view) is unacceptable from any mail provided that advertises 
> business features or sells (expensive) business licenses.  

This program aims to workaround that limitation.

## How 
This program works by spawning a [ProtonMail Bridge](https://github.com/ProtonMail/proton-bridge) instance 
and orchestrating it to expose the IMAP and SMTP protocols.  
We then use the IMAP protocol to read the incoming mail and SMTP to `route` (read: forward) the mail 
to the proper destination(s) addresses.  
## Gotchas
Apparently the bridge prevents us to forward the mail like in a proper distribution list: 
the `From` header will be the Proton mailbox rather than the original sender.

## Quickstart
### Requirements
This program have some requirements:
- Access to a Protonmail business plan 
- Username and password to a protonmail account (in the business plan) without 2FA
- (Eventually) aliases set-up in the protonmail account to allow for multiple lists without paying for more users

### Docker-compose
```yaml
version: "3"
services:
  pmr:
    image: ghcr.io/aiforensics/protonmailrouter:0.0.5
    container_name: protonmail_router
    volumes:
      - ./config.yaml:/app/config.yaml
    restart: unless-stopped
```
With `config.yaml` being based on this:

```yaml
account: mail@example.com
password: v3rS3cr3t
checkIntervalMinutes: 15
forwarding:
  - address: team1@example.com
    recipients:
      - jhon.doe@example.com
      - will.spears@example.com
      - bob.smith@example.com
  - address: team2@example.com
    recipients:
      - bob.smith@example.com
  - address: admin@example.com
    recipients:
      - bob.smith@example.com
      - joe.brown@example.com
      - joe.brown@gmail.com
```


### K8s
TBD; Just create a deployment (no more than 1 replica plz)

### Developer quickstart
```bash
virtualenv venv
. venv/bin/activate
pip install -r requirements.txt

# Fill your config.yaml file with the credentials and the routing stuff you want
python3 src/main.py
```

### Building the image
`DOCKER_BUILDKIT=1 docker build . -t protonmailrouter --platform linux/amd64`  
(If you don't have buildkit, remove the `--mount` parameter from the `RUN` step in the Dockerfile)
## TODOs
- Find a way to implement a "forged" `From` using the `Sender` header and use the `Reply-To` header ([RFC4021](https://www.rfc-editor.org/rfc/rfc4021#page-7)) (looks like this [might not be possible](https://github.com/ProtonMail/proton-bridge/blob/master/pkg/message/parser.go#L445-L538))
- Prometheus exporter
- Config file provided as a flag
- Credentials passed as env variables (should be really easy)
- Delete received message after forwarding (as a parameter)
- Use fuzzer or something to test the solidity of the solution
- Transform those TODOs in GitHub issues
- GitHub Action pipeline for automatic docker releases on tag
- Try alpine docker image (the debian is 800MB+ large!)
