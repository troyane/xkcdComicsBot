# XKCD Comics Bot

Unofficial (yet) Telegram bot for XKCD comics written in Python.

## Requirements

* Python 3+
* python-telegram-bot (installable via `pip`)
* emoji (installable via `pip`)
* vedis (installable via `pip`)

All requirements could be installed via Conda by this command:

```
cd conda/
conda env create -f xkcd_bot_conda_env.yml
```

If you want to specify a different install path than the default for your system (not related to `prefix` in the `env/xkcd_bot_conda_env.yml`), just use the `-p` flag followed by the required path:

```
cd conda/
conda env create -f xkcd_bot_conda_env.yml -p /home/USER/anaconda3/envs/xkcd_bot
```
