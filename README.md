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
- :heavy_check_mark: Support of validator node on Rust
- **=== We are here ===**
- :clock1: LogStash publishing parsed tonvalidator logs
- :clock1: Extendable TonControl with own secret-managers
- :clock1: TonControl can send notifications to service-bus
- :clock1: TonControl can be controlled via service-bus messages
- :clock1: TonLibs are moved to own project and re-usable for other needs
- :clock1: Extendable TonControl with own service-bus message processors

# Architecture

![Alt text](docs/imgs/suton.png?raw=true "Architecture overview")

Notes:
- Validator node doesn’t have any extra ports exposed
- Every deployment can be scaled independently and whenever is required
- Very flexible in controlling costs - Validator, Controller and Logstash are deployed via Docker (backed-up with docker-compose) either to bare-metal machine or VM.
  At the same time monitoring can be either custom solution or one of SaaS solutions with pay-as-you-go subscriptions. The same applies for message-queue (either custom deployment or SaaS).
- Pub/Sub layer provides good abstraction and allows to inject many type of notifications and ways to control validator(s), including safe for the validator web interfaces.
- It is easy to integrate any kind of alerting and automatic response to those alerts.

# Usage

## Prerequisite
- Generate secret seed for if want to use direct-validation in work-chain (`-1:`) or base-chain one (`0:`) if via depool. 
  Use `tonoscli` utility as described in the [Ton Dev doc](https://docs.ton.dev/86757ecb2/p/94921e-multisignature-wallet-management-in-tonos-cli) 
- Install Python3.7 and Docker on your machine (no need to enable Hyper-V on windows if node located remotely, but requires docker CLI utilities, `docker-compose` in particular). 
  If you will run docker containers locally, then you will need full Docker(with Hyper-V on windows).
- *(if validator is remote)*
  Install Docker-daemon on remote machine (aka validator), [Ubuntu](https://docs.docker.com/engine/install/ubuntu/) example.
- *(if validator is remote)*
  For setup phase make your server accessible via SSH by root via ssh-keys (or grant root perms for some account you are going to use).
  Remove this ssh access once setup is finished (or revoke root perms for the account used).
  *Root access will be required by Docker, so that it would be able to connect to remote Docker daemon and build/run images.*
- Prepare you validator machine which should have dedicated place for Ton work-dir (500GB-1TB SSD), and work-dir for ton-controller (no special requirements).
  *(if on NIX)* Grant owner permission for 2 work-folders you will dedicate for `ton-control` and for `ton-validator`.   
  Default is `1001:1001` for validator and `1002:1002` for `toncontrol`. Ex:  
  `$ chown 1001:1001 /data/ton-validator` 
- Optional: generate RSA keys, place private key to `<ton-controller-work-dir/configs/keys>`. 
  Encrypt your wallet seed with public key and convert to base64 format, [details here](#seed-encryption).

## Quick Start

Example workspace: 
https://github.com/jarig/suton-workspace

## Workspace Setup

Take example project as a base:  
https://github.com/jarig/suton-workspace

or start your own from scratch, create following project structure:
```text
node-1/
      configs/        (optional)
          logstash/        # logstash configs should be under this directory
              host/        # configs for pushing telemetry from the host machine
              ton_control/ # configs for ton_control telemetry
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
    
    # any name that will help you to identify the node in the telemetry later on
    NODE_NAME = "my-node"

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
        "validator_seed": os.environ.get(f"SOME_ENV_VAR_WITH_SEED"), # can be encrypted, read further
        "validator_address": "-1:<validator address>",
        "custodian_seeds": []
    }
    # note: at a moment better to use config that is coming from github of net.ton.dev scripts as it's more reliable
    # though is setting is optional and if omitted, then will derive config based on TEST_ENV param and download them from the corresponding end-points
    TON_VALIDATOR_CONFIG_URL = "https://raw.githubusercontent.com/tonlabs/net.ton.dev/master/configs/ton-global.config.json"
```
More info about possible settings options and [seed encryption](#seed-encryption) described here in the [settings](#settings) section.

Note: `TON_WORK_DIR` and `TON_CONTROL_WORK_DIR` should be pre-created on Host machine.
Once all folders are in place grant `ton` and `toncontrol` users permissions to respected work folders:
```bash
$ chown 1001:1001 /path/to/ton-work-dir
$ chown 1002:1002 /path/to/ton-control-dir
```

Create in the your workspace root `requirements.txt` with contents
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

### Workspace Example

You can start creating the workspace from this example which have all main things pre-configured: 

https://github.com/jarig/suton-workspace

# Setup and Configuration

Check [Usage](#usage) first.

## Settings

Here are possible values for settings
```python

from suton.toncontrol.settings.core import TonSettings
from suton.toncontrol.settings.elections import ElectionSettings

class MyElectionSettings(ElectionSettings):

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
    # In case if Elector is Solidity-based contract, then specify ABI file for it. Otherwise keep it commented out, then assumption Elector is fift-based
    # ELECTOR_ABI_URL = "https://raw.githubusercontent.com/tonlabs/rustnet.ton.dev/6b9c09474d2a4a785b04b562d547f12967b8b53d/docker-compose/ton-node/configs/Elector.abi.json" 
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

## Elections

### Direct

```python
from suton.toncontrol.settings.core import TonSettings
from suton.toncontrol.settings.elections import ElectionSettings

class MyElectionSettings(ElectionSettings):
    # optional: max-factor for the elections. The maximum ratio allowed between your stake and the minimal validator stake in the elected validator group
    TON_CONTROL_STAKE_MAX_FACTOR = "3"
    # optional: percent or absolute value(in tokens) of the stake that elector should make
    TON_CONTROL_DEFAULT_STAKE = "35%"

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
        }
    }
    TON_VALIDATOR_CONFIG_URL = "https://raw.githubusercontent.com/tonlabs/net.ton.dev/master/configs/net.ton.dev/ton-global.config.json"
    TONOS_CLI_CONFIG_URL = "https://net.ton.dev"
    # Specify election settings, in current case it's depool ones
    ELECTIONS_SETTINGS = MyElectionSettings()
```

### DePool

SuTon can also automate maintenance of DePool contract and elections that are performed via latter.

Here is example config for this:

```python
from suton.toncontrol.settings.core import TonSettings
from suton.toncontrol.settings.elections import ElectionSettings, ElectionMode
from suton.toncontrol.settings.depool_settings.depool import DePoolSettings
# NOTE: TickTock events are send via Validator wallet to DePool directly

class MyDepoolElectionSettings(ElectionSettings):

    # set to DePool Mode
    TON_CONTROL_ELECTION_MODE = ElectionMode.DEPOOL
    DEPOOL_LIST = [
        DePoolSettings(depool_address=f"0:<depool_address_in_workchain>",
                       abi_url=f"https://<url to DePool ABI json>/DePool.abi.json",
                       max_ticktock_period=1400,  # how often to send tick-tock pings
                       )
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
        }
    }
    TON_VALIDATOR_CONFIG_URL = "https://raw.githubusercontent.com/tonlabs/net.ton.dev/master/configs/net.ton.dev/ton-global.config.json"
    TONOS_CLI_CONFIG_URL = "https://net.ton.dev"
    # Specify election settings, in current case it's depool ones
    ELECTIONS_SETTINGS = MyDepoolElectionSettings()
```

### Prudent Election Settings

Participation in election is like a game, sometimes you can win or loose, outcome depends from your competitors and your actions. 
If a stake you make is too low, then you are not getting into minimal number of validators 
(so TOP N validators made higher stake than you, where N is max allowed number of validators), then you are kicked out and TONs you payed for election requests are gone.
So, it's important to play this game right. To make it easier SuTON provides extra settings - `PrudentSettings` that will help you to win this game.

Example with the DePool mode:
```python
from suton.toncontrol.settings.depool_settings.prudent_elections import PrudentElectionSettings
from suton.toncontrol.settings.elections import ElectionSettings, ElectionMode
from suton.toncontrol.settings.depool_settings.depool import DePoolSettings

class DepoolElectionSettings(ElectionSettings):

    TON_CONTROL_ELECTION_MODE = ElectionMode.DEPOOL
    DEPOOL_LIST = [
        DePoolSettings(depool_address=f"<depool_address_in_workchain>",
                       abi_url=f"https://<url to DePool ABI json>/DePool.abi.json",
                       prudent_election_settings=PrudentElectionSettings(election_end_join_offset=3600,
                                                                 join_threshold=1))
    ]
```  
You can define `PrudentElectionSettings` either in DePoolSettings (if you are using DePools) or in `ElectionSettings.PRUDENT_ELECTION_SETTINGS` if participating directly.

Where

`election_end_join_offset` - Defines time offset when decision to join elections to be made, relative to election-end time.
So for example, if you define 600 - then stake will be made in 10 or less minutes before election ends. Defined in seconds.

`join_threshold` - Percentage that defines election join condition based on the current number of stakes
their `min_value` and stake you can/want to make. Threshold computed as = `participants_with_lower_than_your_stake / first_N_participants`.
So for example, if you define 10, then elections will be taken if 10% of valid participants (who potentially can join) 
has lower stake than yours by the time when election join attempt is made (which regulated by `election_end_join_offset` param).


### Auto-Replenish DePool Balance

DePools have own balance that they spent on staking operations, in case if this balance drops below minimum required, then DePool won't be able to join elections or perform other operations.
To avoid this, balance need to be replenished from time to time, SuTon provides automatic way of doing this via `AutoReplenishSettings` for a DePool.

Example:
```python
from suton.toncontrol.settings.depool_settings.prudent_elections import PrudentElectionSettings
from suton.toncontrol.settings.elections import ElectionSettings, ElectionMode
from suton.toncontrol.settings.depool_settings.depool import DePoolSettings
from suton.toncontrol.settings.depool_settings.auto_replenish import AutoReplenishSettings
from suton.tonlibs.toncommon.models.TonCoin import TonCoin

class DepoolElectionSettings(ElectionSettings):

    TON_CONTROL_ELECTION_MODE = ElectionMode.DEPOOL
    DEPOOL_LIST = [
        DePoolSettings(depool_address=f"<depool_address_in_workchain>",
                       fabi_url="https://<url to DePool ABI json>/DePool.abi.json",
                       replenish_settings=AutoReplenishSettings(TonCoin(2.5), max_period=7200))
    ]
```  

## LogStash Monitoring

Logstash image going to collect sent to it telemetry from configured pipelines (being send via TCP, json input).

Inputs and basic filters configured for both, but for desired output you would need to create configuration.
Logstash image has 2 pipelines (`host` and `toncontrol`), each can have own configuration.

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

At a moment LogStash can send telemetry from the `toncontrol` module and `host` itself.
You can configure output settings for them separately by placing appropriate configs in either `logstash/host` or `logstash/ton_control` folders.

Example structure:
```text
node-1/
      configs/        (optional)
          logstash/        # logstash configs should be under this directory
              host/        # configs for pushing telemetry from the host machine
              ton_control/ # configs for ton_control telemetry
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
Ex: `$ python manage.py --node=node-1 docker exec tonvalidator ./check_node_sync_status.sh`

# Troubleshooting

## Known-host issue with docker-compose

Docker-compose might complain about missing known-host entry. In this case connect at least once via ssh to generate known-host entry.
In case of Windows you can transfer such known-host entry to `%USERPROFILE%/.ssh/`. 