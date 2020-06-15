# Overview

Framework with set of Docker images and python libraries to deploy and control TON Validator node.

:warning: **It's work-in-progress project**

Status:
- :heavy_check_mark: TonValidator deployment, execution and synchronization
- :heavy_check_mark: TonControl deployment
- :heavy_check_mark: TonControl can track for validator health and its sync status
- **=== We are here ===**
- :clock1: TonLibs are moved to own project and re-usable for other needs
- :clock1: TonControl automates participation in elections
- :clock1: TonControl reports telemetry via LogStash using TCP protocol
- :clock1: LogStash analyzing tonvalidator logs
- :clock1: TonControl can send notifications to service-bus
- :clock1: TonControl can be controlled via service-bus messages


# Usage

## Prerequisite
- Generate secret seed for work-chain `-1` (validators) using `tonoscli` utility as described in the [Ton Dev doc](https://docs.ton.dev/86757ecb2/p/94921e-multisignature-wallet-management-in-tonos-cli) 
- Install Docker (no need to enable Hyper-V on windows, but requires docker CLI utilities, `docker-compose` in particular)
- For setup phase make your server accessible via SSH by root via ssh-keys (or grant root perms for some account you are going to use)
  Remove this ssh access once setup is finished (or revoke root perms for the account used).
  Root access will be required by Docker, so that it would be able to connect to remote Docker daemon and run images.
- Prepare you validator machine which should have dedicated place for Ton work-dir (500GB-1TB SSD), and work-dir for ton-controller (no special requirements). 
- Optional: generate RSA keys, place private key to `<ton-controller-work-dir/keys>`. 
  Encrypt your wallet seed with public key and convert to base64 format.

Create following project structure:
```text
node-1/
      settings.py
manage.py
requirements.txt
```

Where `manage.py` has following contents:
```python
from suton import TonManage
TonManage().main()
```

And `node-1/settings.py` with the following:
```python
from suton import TonSettings
import os

class NodeSettings(TonSettings):
    # where to connect to
    DOCKER_HOST = "ssh://root@<validator machine IP>"
    # work-dir on HOST machine (where db, logs and configs will be)
    TON_WORK_DIR = "/data/ton-work"
    # work-dir on HOST mahcine for ton-control (for logs, and key pick-up & remove by ton-control)
    TON_CONTROL_WORK_DIR = "/data/ton-control"
    # either data-structure for default secret-manager or connection-string for Keyvault type of secret-managers
    # note: it's possible to encrypt data using RSA keys, check Settings docs.
    # don't commit your seed phrases!
    TON_CONTROL_SECRET_MANAGER_CONNECTION_STRING = {
        "validator_seed": os.environ.get("SOME_ENV_VAR_WITH_SEED"), # can be encrypted
        "validator_address": "-1:<validator address>",
        "custodian_seeds": []
    }
```
More info about possible settings options and seed encryption described here: [Settings](#settings)

And to `requirements.txt`
```requirements.txt
git+git://github.com/jarig/suton@master#egg=suton
```

Then run:
1. `$ pip install -r requirements.txt`
1. `$ python manage.py --node=node-1 run`
   
   Note: at a moment `tonvalidator` and `toncontrol` are deployable services, so you can run
   
   `$ python manage.py --node=node-1 run --service tonvalidator`
   
   `$ python manage.py --node=node-1 run --service toncontrol`

# Architecture

![Alt text](docs/imgs/arch.jpeg?raw=true "Architecture overview")

Notes:
- Validator node doesn’t have any extra ports exposed
- Every deployment can be scaled independently and whenever is required
- Very flexible in controlling costs - Validator, Controller and Logstash are deployed via Docker (backed-up with docker-compose) either to bare-metal machine or VM. (Ansible can help in some maintenance later on, I’ve excluded Terraform as it’s not that good for bare-metal cases).
  At the same time monitoring can be either custom solution or one of SaaS solutions with pay-as-you-go subscriptions. The same applies for message-queue (either custom deployment or SaaS).
  With the current specs for a Validator node bare-metal machines will be the most cost-effective I believe comparing to any VM in any of cloud providers.
- Pub/Sub layer provides good abstraction and allows to inject many type of notifications and ways to control validator(s), including safe for the validator web interfaces.
- It is easy to integrate any kind of alerting and automatic response to those alerts.


# Setup and Configuration

Check [Usage](#usage) first.

## Settings

Here are possible values for settings
```python
from suton import TonSettings

class NodeSettings(TonSettings):
    # define where docker-compose should connect to
    DOCKER_HOST = "ssh://root@<validator machine IP>"
    # working directory on HOST machine for validator
    # Database, logs and configurations will appear there
    TON_WORK_DIR = "/data/ton-work"
    # working directory on HOST machine for ton-control
    # Logs will be written under this location, also ton-control might pick-up keys
    # from under $TON_CONTROL_WORK_DIR/keys for use by secret-manager
    TON_CONTROL_WORK_DIR = "/data/ton-control"
    # Either dict/json data that will be passed to default secret-manager (EnvProvider) 
    # or can be connection-string for Keyvault type of secret-managers
    TON_CONTROL_SECRET_MANAGER_CONNECTION_STRING = {
        "validator_seed": '<seed phrase>',
        "validator_address": "-1:<validator address>",
        # optional name of a private key you placed under $TON_CONTROL_WORK_DIR/keys
        # by specifying it you suppose to encrypt with appropriate public key and convert to base64 validator_seed and custodian_seeds entries.
        "encryption_key_name": "",
        # list of custodian seeds that want to automate approvals on their behalf
        "custodian_seeds": []
    }
```

## SuTon CLI Commands

This is commands you can run against your setup after you've followed [usage](#usage) steps and included SuTon framework.

**Global Options**

`--node` - Select what node settings to read/pick-up.

### Command "run"

Command for starting containers on the host machine.

`$ python manage.py --node=node-1 run -h`

**Options**

`--service` - Specify which service to start.

`--build` - Rebuild image before starting it.

`--attach` - Run and attach to the executed container.

### Command "docker"

Command to invoke any arbitrary `docker-compose` commands on host machine.

`$ python manage.py --node=node-1 docker <docker_args>`

Ex: `$ python manage.py --node=node-1 docker ps`
Ex: `$ `

# Troubleshooting

## Known-host issue with docker-compose

Docker-compose might complain about missing known-host entry. In this case connect at least once via ssh to generate known-host entry.
In case of Windows you can transfer such known-host entry to `%USERPROFILE%/.ssh/`. 