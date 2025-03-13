# Asyncronus mail fetcher

## Install

```sh

python -m pip install --user 'git+https://github.com/roderik333/syncmail.git#egg=syncmail'
```

## WHATSIT?

This is a simple mail fetcher meant for use with `neomutt` that has been set up using `mutt-wizard`.

> **_NOTE:_** Since `neomutt` has been set up with `mutt-wizard` there are some assumptions made. Most notably, you have actually used `mutt-wizard` to configure `neomutt` and installed all dependencies. If not, then you might have to adjust this script to your liking.

The use case for this is an immutable distro, in my case bazzite, where I couldn't get `*.timer` to work reliably. Why did I need this? Because everything is installed in a distrobox...

There is no `systemd` in `distrobox` so I can't run `cron` or `mailsync.timer`. But what you can do is to run the following out side of distrobox.

```
# ~/.config/systemd/user/mailsync.service

[Unit]
Description=Run mailsync in distrobox
After=network.target

[Service]
Type=oneshot
TimeoutSec=1200
ExecStart=/usr/bin/distrobox-enter --name <my container name> -- /usr/local/bin/mailsync

[Install]
WantedBy=default.target
```

```
# ~/.config/systemd/user/mailsync.timer

[Unit]
Description=Run mailsync every 5 minutes
After=mailsync.service

[Timer]
OnUnitActiveSec=5min
Unit=mailsync.service

[Install]
WantedBy=timers.target
```

Installed on `systemctl --user` this runs once, then bombs out. After restarting the timer it runs as expected. This happenes each and every time the machine starts. I got fed ut with it and I couldn't figure out what I was doing wrong. Thusly, `syncmail`.

## ENVs

After installation you can use the `dotenv cli` to add enviroment variables.

```sh
dotenv -f .syncmailenv set NEOMUTT_LOG_FILE /tmp/mutt_fetch.log
dotenv -f .syncmailenv set NEOMUTT_ACCOUNTS_PATH /home/<your user name>/.config/mutt/accounts
dotenv -f .syncmailenv set NEOMUTT_CHECK_INTERVAL 300
```

Now, provided you have installed this script on `--user` or in a active `venv` you will have a commandline tool `syncmail` in your path.

```sh

$ syncmail
Usage: syncmail [OPTIONS] COMMAND [ARGS]...

  General commands

Options:
  --help  Show this message and exit.

Commands:
  infinite-loop  Run the mail fetcher indefinitely.
  one-shot       one shot execution of sync mail.
```

`one-shot` will fetch mail once and stop. `infinite-loop` will fetch mail at `INTERVAL` util `ctrl-c`

```sh
$ syncmail infinite-loop &  # starts and sends syncmail into the background
[1] <process id>  # will print [1] provided this is your only background process in this terminal
$ fg  # takes syncmail to the foreground
^Z (ctrl-z) # suspends syncmail and sends it to the background
[1] <process id>
$ bg %1  # resumes syncmail while still in the bacground
$ fg  # takes syncmail to the foreground
^ctrl-c  # quits out of syncmail
```

That's about it.
