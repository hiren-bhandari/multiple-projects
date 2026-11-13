# tv-control

Hobby project: connect to my Samsung TV over the local network and operate it
(power, volume, input, apps, navigation).

## Check the TV is reachable

On a computer on the same network as the TV (Python 3.8+, no installs needed):

    python3 find_tv.py                    # search the network
    python3 find_tv.py --ip 192.168.1.50  # or check a known address

It prints the TV's name, model, power state and whether the remote-control
ports are open. It only reads information; it sends no commands.

Status: discovery only. Remote-control commands are not written yet.
