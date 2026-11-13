# tv-control

Hobby project: connect to my Samsung TV over the local network and operate it
(power, volume, input, apps, navigation).

## Check the TV is reachable

On a computer on the same network as the TV (Python 3.8+, no installs needed):

    python3 find_tv.py                    # search the network
    python3 find_tv.py --ip 192.168.1.50  # or check a known address

It prints the TV's name, model, power state and whether the remote-control
ports are open. It only reads information; it sends no commands.

Status: discovery script and phone remote page written; neither tried on the real TV yet.

## Phone remote (`remote.html`)

A single web page with remote buttons. Opened in a phone browser on the same
Wi-Fi as the TV, it connects straight to the TV (port 8002, or 8001 when the
page is served without https) and sends key presses. The TV asks to allow it
the first time; the pairing token is then remembered in the browser.

The page has to be served from a web address to run on a phone. It cannot
switch the TV on from standby, because that needs a network wake-up packet a
browser cannot send.

Tested against a fake TV only, not yet against a real one.
