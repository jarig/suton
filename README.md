# Overview

Framework with set of Docker images and python libraries to deploy and control TON Validator node.

:warning: **It's work-in-progress project**

Status:
- :heavy_check_mark: TonValidator deployment, execution and synchronization
- :heavy_check_mark: TonControl deployment
- :heavy_check_mark: TonControl can track for validator health and its sync status
- :heavy_check_mark: TonControl automates participation in elections
- :heavy_check_mark: TonControl reports telemetry via LogStash using TCP protocol
- :heavy_check_mark: TonControl automates participation in DePool elections
- **=== We are here ===**
- :clock1: LogStash publishing parsed tonvalidator logs
- :clock1: Extendable TonControl with own secret-managers
- :clock1: TonControl can send notifications to service-bus
- :clock1: TonControl can be controlled via service-bus messages
- :clock1: TonLibs are moved to own project and re-usable for other needs
- :clock1: Extendable TonControl with own service-bus message processors

# Usage

## Prerequisite
- Generate secret seed for work-chain `-1` (validators) using `tonoscli` utility as described in the [Ton Dev doc](https://docs.ton.dev/86757ecb2/p/94921e-multisignature-wallet-management-in-tonos-cli) 
- Install Python3 and Docker on your machine (no need to enable Hyper-V on windows, but requires docker CLI utilities, `docker-compose` in particular)
- Install Docker-daemon on remote machine (validator), for example [Ubuntu](https://docs.docker.com/engine/install/ubuntu/)
- For setup phase make your server accessible via SSH by root via ssh-keys (or grant root perms for some account you are going to use).
  Remove this ssh access once setup is finished (or revoke root perms for the account used).
  *Root access will be required by Docker, so that it would be able to connect to remote Docker daemon and build/run images.*
- Prepare you validator machine which should have dedicated place for Ton work-dir (500GB-1TB SSD), and work-dir for ton-controller (no special requirements). 
- Optional: generate RSA keys, place private key to `<ton-controller-work-dir/configs/keys>`. 
  Encrypt your wallet seed with public key and convert to base64 format, [details here](#seed-encryption).

Create following project structure:
```text
node-1/
      configs/        (optional)
          logstash/   # logstash configs should be under this directory
      settings.py
manage.py
requirements.txt
```

Where `manage.py` has following contents:
```python
from suton.core import TonManage
TonManage().main()
```

And `node-1/settings.py` with the following:
```python

from suton.toncontrol.settings.core import TonSettings
import os

class NodeSettings(TonSettings):
    # where to connect to
    DOCKER_HOST = "ssh://root@<validator machine IP>"
    # test or main
    TON_ENV = "net.ton.dev"
    # work-dir on HOST machine (where db, logs and configs will be)
    TON_WORK_DIR = "/data/ton-work"
    # work-dir on HOST mahcine for ton-control (for logs, and key pick-up & remove by ton-control)
    TON_CONTROL_WORK_DIR = "/data/ton-control"
    # either data-structure for default secret-manager or connection-string for Keyvault type of secret-managers
    # note: it's possible to encrypt data using RSA keys, check Settings docs.
    # don't commit your seed phrases!
    TON_CONTROL_SECRET_MANAGER_CONNECTION_STRING = {
        "validator_seed": os.environ.get("SOME_ENV_VAR_WITH_SEED"), # can be encrypted, read further
        "validator_address": "-1:<validator address>",
        "custodian_seeds": []
    }
    # note: at a moment better to use config that is coming from github of net.ton.dev scripts as it's more reliable
    # though is setting is optional and if omitted, then will derive config based on TEST_ENV param and download them from the corresponding end-points
    TON_VALIDATOR_CONFIG_URL = "https://raw.githubusercontent.com/tonlabs/net.ton.dev/master/configs/ton-global.config.json"
```
More info about possible settings options and [seed encryption](#seed-encryption) described here in the [settings](#settings) section.

Note: `TON_WORK_DIR` and `TON_CONTROL_WORK_DIR` should be pre-created on Host machine.
Also based on other settings you might put extra configuration files into them such as `configs/logstash` for controlling logstash outputs or `configs/keys` for encryption functionality.
Once all files in place grant `ton` and `toncontrol` users permissions to respected work folders:
```bash
$ chown 1001:1001 /path/to/ton-work-dir
$ chown 1002:1002 /path/to/ton-control-dir
```

Create in your local setup `requirements.txt` with
```requirements.txt
git+git://github.com/jarig/suton@master#egg=suton
```

Then run:
1. `$ pip install -r requirements.txt`
1. `$ python manage.py --node=node-1 run --build`
   
   Or if you want to run them separately:
   
   `$ python manage.py --node=node-1 run --build --service tonvalidator`
   
   `$ python manage.py --node=node-1 run --build --service toncontrol`
   
   `$ python manage.py --node=node-1 run --build --service tonlogstash`


# Architecture

![Alt text](docs/imgs/arch.jpeg?raw=true "Architecture overview")

Notes:
- Validator node doesn’t have any extra ports exposed
- Every deployment can be scaled independently and whenever is required
- Very flexible in controlling costs - Validator, Controller and Logstash are deployed via Docker (backed-up with docker-compose) either to bare-metal machine or VM.
  At the same time monitoring can be either custom solution or one of SaaS solutions with pay-as-you-go subscriptions. The same applies for message-queue (either custom deployment or SaaS).
- Pub/Sub layer provides good abstraction and allows to inject many type of notifications and ways to control validator(s), including safe for the validator web interfaces.
- It is easy to integrate any kind of alerting and automatic response to those alerts.


# Setup and Configuration

Check [Usage](#usage) first.

## Settings

Here are possible values for settings
```python

from suton.toncontrol.settings.core import TonSettings
from suton.toncontrol.settings.elections import ElectionSettings

class MyElectionSettings(ElectionSettings):

    # set to DePool Mode
    # optional: max-factor for the elections. The maximum ratio allowed between your stake and the minimal validator stake in the elected validator group
    TON_CONTROL_STAKE_MAX_FACTOR = "3"
    # optional: percent or absolute value(in tokens) of the stake that elector should make
    TON_CONTROL_DEFAULT_STAKE = "35%"


class NodeSettings(TonSettings):
    # define where docker-compose should connect to
    DOCKER_HOST = "ssh://root@<validator machine IP>"
    # defines what env validator will use
    TON_ENV = "net.ton.dev"
    # working directory on HOST machine for validator
    # Database, logs and configurations will appear there
    TON_WORK_DIR = "/data/ton-work"
    # working directory on HOST machine for ton-control
    # Logs will be written under this location (under /log subdir), also ton-control might pick-up keys
    # from under $TON_CONTROL_WORK_DIR/configs/keys for use by secret-manager
    TON_CONTROL_WORK_DIR = "/data/ton-control"
    # Either dict/json data that will be passed to default secret-manager (EnvProvider) 
    # or can be connection-string for Keyvault type of secret-managers
    TON_CONTROL_SECRET_MANAGER_CONNECTION_STRING = {
        "validator_seed": '<seed phrase or encrypted seed phrase>',
        "validator_address": "-1:<validator address>",
        # optional name of a private key you placed under $TON_CONTROL_WORK_DIR/configs/keys
        # by specifying it you suppose to encrypt with appropriate public key and convert to base64 validator_seed and custodian_seeds entries.
        "encryption_key_name": "",
        # list of custodian seeds that want to automate approvals on their behalf
        # also should be in encrypted form if 'encryption_key_name' is present.
        "custodian_seeds": []
    }
    ELECTIONS_SETTINGS = MyElectionSettings()
    # optional: url to configuration that tonos-cli should use (default is derived from TON_ENV, i.e https://$TON_ENV)
    TONOS_CLI_CONFIG_URL = None
    # optional: Setting is optional and if omitted, then will derive config based on TEST_ENV param and 
    # download them from the corresponding end-points: TEST_ENV/ton-global.config.json
    TON_VALIDATOR_CONFIG_URL = "https://raw.githubusercontent.com/tonlabs/net.ton.dev/master/configs/ton-global.config.json"
```

## Seed Encryption

It's bad practice to commit sensitive information to git repos, even private ones. So it's better to encrypt your seed and put it into the git in encrypted form.

To generate encrypted seed:
```bash
$ openssl genrsa -out key.pem 1024
$ openssl rsa -in key.pem -pubout -out pub.pem
$ echo '<seed phrase>' | openssl rsautl -encrypt -pubin -inkey ./pub.pem |openssl enc -A -base64
# save base64 string, this is your encrypted seed that you can put to settings of NodeSettings class
# verify that encrypted and converted to base64 format key is correct
$ echo "<base64_output>" |base64 -d | openssl rsautl -decrypt -inkey key.pem
```

Your private key (`key.pem` in the example above) should be placed to `<ton_control_work_dir>/configs/keys` folder and its name saved in `TON_CONTROL_SECRET_MANAGER_CONNECTION_STRING` json of `NodeSettings` class under `encryption_key_name` key of json payload.

## DePool Elections

SuTon can also automate maintenance of DePool contract and elections that are performed via latter.

Here is example config for this:

```python
from suton.toncontrol.settings.core import TonSettings
from suton.toncontrol.settings.elections import ElectionSettings, ElectionMode
from suton.toncontrol.settings.models.depool import DePoolSettings

#  
_DEPOOL_HELPER_SEED_NAME = "depool_helper"

class MyDepoolElectionSettings(ElectionSettings):

    # set to DePool Mode
    TON_CONTROL_ELECTION_MODE = ElectionMode.DEPOOL
    DEPOOL_LIST = [
        DePoolSettings(depool_address="<depool_address_in_workchain>",
                       proxy_addresses=["<first_proxy_in_masterchain>",
                                        "<second_proxy_in_masterchain>"],
                       helper_address="<helper_address_in_workchain>",
                       # name of a secret within 'secrets' section of the connection string payload (if ENV SecretManager used)
                       helper_seed_name=_DEPOOL_HELPER_SEED_NAME,
                       # helper ABI file
                       helper_abi_url="https://raw.githubusercontent.com/tonlabs/ton-labs-contracts/master/solidity/depool/DePoolHelper.abi.json")
    ]


class NodeSettings(TonSettings):
    DOCKER_HOST = "ssh://root@<validator machine IP>"

    TON_ENV = "net.ton.dev"
    TON_WORK_DIR = "/data/ton-work"
    TON_CONTROL_WORK_DIR = "/data/ton-control"
    TON_CONTROL_SECRET_MANAGER_CONNECTION_STRING = {
        "encryption_key_name": "<encryption_key_name>",
        "validator_seed": '<seed>',
        "validator_address": "<addr>",
        "custodian_seeds": [
            "<seed>"
        ],
        "secrets": {
            _DEPOOL_HELPER_SEED_NAME: "<seed>"
        }
    }
    TON_VALIDATOR_CONFIG_URL = "https://raw.githubusercontent.com/tonlabs/net.ton.dev/master/configs/net.ton.dev/ton-global.config.json"
    TONOS_CLI_CONFIG_URL = "https://net.ton.dev"
    # Specify election settings, in current case it's depool ones
    ELECTIONS_SETTINGS = MyDepoolElectionSettings()
```

## LogStash Monitoring

Logstash image going to collect sent to it telemetry from `toncontrol` (being send via TCP) and from `tonvalidator` (log parsing).

Inputs and basic filters configured for both, but for desired output you would need to create configuration.
Logstash image has 2 pipelines (`toncontrol` and `tonvalidator` ones), each can have own configuration.

### TonControl configuration

Picked up from `<folder_with_your_node_settings_file>/configs/logstash/`

Example configuration:
```ruby
output {
  elasticsearch {
    hosts => ["https://<cluster>.bonsaisearch.net:443"]
    ssl   => true
    index => "logstash-suton-%{+YYYY.MM}"
  }
}
```

All files will be automatically uploaded to remote server via ssh on `run` command to `<ton_control_workdir>/configs/logstash/`.

[Bonsai.io](https://bonsai.io/) providing free tier where you can send logstash data and get Kibana dashboard very fast.



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
Ex: `$ python manage.py --node=node-1 docker exec tonvalidator ./check_node_sync_status.sh`

# Troubleshooting

## Known-host issue with docker-compose

Docker-compose might complain about missing known-host entry. In this case connect at least once via ssh to generate known-host entry.
In case of Windows you can transfer such known-host entry to `%USERPROFILE%/.ssh/`. 