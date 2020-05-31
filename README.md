# Overview

Framework with set of Docker images and python libraries to deploy and control TON Validator node.

:warning: **It's work-in-progress project**

Status:
- TonValidator deployment, execution and synchronization
- TonControl deployment
- TonControl can track for validator health and its sync status
- **=== We are here ===**
- TonLibs are moved to own project and re-usable for other needs
- TonControl automates participation in elections
- TonControl reports telemetry via Logstash using TCP protocol
- Logstash analyzing tonvalidator logs
- TonControl can send notifications to service-bus
- TonControl can be controlled via service-bus messages


# Usage

## Prerequisite
- Generate secret seed for work-chain `-1` (validators) using `tonoscli` utility as described in the [Ton Dev doc](https://docs.ton.dev/86757ecb2/p/94921e-multisignature-wallet-management-in-tonos-cli) 
- Install Docker (no need to enable Hyper-V on windows, but requires docker CLI utilities, `docker-compose` in particular)
- For setup phase make your server accessible via SSH by root via ssh-keys (or grant root perms for some account you are going to use)
  Remove th


Create following project structure:
```text
node-1/
      settings.py
manage.py
requirements.txt
```

Where manage.py has following contents:
```python
from suton import TonManage
TonManage().main()
```

And `node-1/settings.py` with the following:
```python
from suton import TonSettings

class NodeSettings(TonSettings):
    DOCKER_HOST = "ssh://root@<validator machine IP>"
    TON_WORK_DIR = "/data/ton-work"
    TON_CONTROL_WORK_DIR = "/data/ton-control"
    TON_CONTROL_SECRET_MANAGER_CONNECTION_STRING = {
        "validator_seed": '<seed phrase>',
        "validator_address": "-1:<validator address>",
        "custodonian_seeds": []
    }
```
More info about possible settings options described here: [Settings](#settings)

And to `requirements.txt`
```requirements.txt
git+git://github.com/jarig/suton@master#egg=suton
```

Then run:
1. `$ pip install -r requirements.txt`
1. `$ python manage.py --node=node-1 run`


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

Check [Usage](#usage)

## Settings

Here are possible values for settings
```python
from suton import TonSettings

class NodeSettings(TonSettings):
    # define where docker-compose
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
        # by specifying it you suppose to encrypt with appropriate public key and convert to base64 validator_seed and custodonian_seeds entries.
        "encryption_key_name": "",
        # list of custodonian seeds that want to automate approvals on their behalf
        "custodonian_seeds": []
    }
```
