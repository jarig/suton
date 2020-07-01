import time
import argparse
import logging
import sys
import os
from logging.handlers import RotatingFileHandler

from logstash.client import LogStashClient

# TODO: remove once tonlibs are moved away
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'tonlibs'))

from routines.elections import ElectionsRoutine
from routines.qcontroller import QueueRoutine
from tonvalidator.core import TonValidatorEngineConsole
from tonliteclient.core import TonLiteClient
from tonoscli.core import TonosCli
from tonfift.core import FiftCli


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--work_dir', dest='work_dir', default='/var/ton-control',
                        help='Working directory for ton-control service')
    parser.add_argument('--log_path', dest='log_path', default='/var/ton-control/log', help='Path to log file')
    parser.add_argument("--keys_dir", default='/var/ton-control/configs/keys',
                        help="Path to toncontrol keys folder, copied from hosted machine")
    parser.add_argument("--validator_wallet_seed",
                        help="Validator seed phrase or connection string")
    parser.add_argument('--default_election_stake', dest='default_election_stake', default='30%',
                        help='Stake to make on elections, % or absolute value')
    parser.add_argument('--stake_max_factor', dest='stake_max_factor', default='3',
                        help='Stake max-factor')
    parser.add_argument("--secret_manager_connection_env",
                        help="Env variable containing secret manager connection string")
    parser.add_argument("--secret_manager_provider", default='secrets.envprovider.core',
                        help="Python module path to use to import Secret Manager provider")
    parser.add_argument("--queue_provider", default='mqueue.azureservicebus.core',
                        help="Python module path to use to import Queue provider")
    parser.add_argument("--queue_name", default='ton-validator-0', 
                        help="Name of the queue to use")
    parser.add_argument("--validator_max_sync_diff", default=30,
                        help="Minimum time difference that validator can have to consider it as synced")
    parser.add_argument("--client_key", default='/var/ton-keys/client', help="Path to client private key")
    parser.add_argument("--server_pub_key", default='/var/ton-keys/server.pub', 
                         help="Path to server public key")
    parser.add_argument("--validator_engine_path", 
                        default='/opt/ton/validator-engine-console/validator-engine-console', 
                        help="Base path to TON validator-engine CLI")
    parser.add_argument("--validator_network_address", default='tonvalidator:3030',
                        help="TON Validator network address, including port. Can contain Docker hostnames")
    parser.add_argument("--lite_client_path", 
                        default='/opt/ton/lite-client/lite-client',
                        help="Base path to TON lite-client")
    parser.add_argument("--lite_client_network_address", default='tonvalidator:3031',
                        help="Address to use for lite-client, including port. Can contain Docker hostnames")
    parser.add_argument("--lite_server_pub_key", default='/var/ton-keys/liteserver.pub',
                        help="Path to public-key that lite-client will be using")
    parser.add_argument("--tonos_config_url",
                        default='net.ton.dev',
                        help="Hostname of ton environment.")
    parser.add_argument("--tonos_cli_path",
                        default='/opt/ton/utils/tonos-cli',
                        help="Path to tonos-cli utility")
    parser.add_argument("--tonos_cli_cwd", default='/opt/tonos_cwd',
                        help="Address to use for lite-client, including port. Can contain Docker hostnames")
    parser.add_argument("--tonos_cli_abi_path",
                        default='/opt/configs/SafeMultisigWallet.abi.json',
                        help="Path to ABI file")
    parser.add_argument("--tonos_cli_tvc_path",
                        default='/opt/configs/SafeMultisigWallet.tvc',
                        help="Path to tvc file")
    parser.add_argument("--fift_cli_path",
                        default='/opt/ton/crypto/fift',
                        help="Path to fift utility")
    parser.add_argument("--fift_includes",
                        default='/opt/ton/fift-libs/libs:/opt/ton/fift-libs/smartcont',
                        help="Includes for Fift to generate contract payloads")

    args = parser.parse_args()
    if not os.path.exists(args.work_dir):
        os.makedirs(args.work_dir)

    configure_logging(args.log_path)
    log = logging.getLogger("")
    
    # verify that keys exist
    keys_to_verify = [args.client_key, args.server_pub_key]
    for key in keys_to_verify:
        if not os.path.exists(key):
            raise Exception("Required key do not exist: {}".format(key))

    log.info("Keys present. Good.")
    # get queue provider
    log.info("Initializing QueueProvider from {}".format(args.queue_provider))
    queue_provider_mod = __import__(args.queue_provider, fromlist=['QueueProvider'])
    queue_provider = queue_provider_mod.QueueProvider(args.queue_name)
    log.info("Initializing SecretManager from {}".format(args.secret_manager_provider))
    secret_manager_mod = __import__(args.secret_manager_provider, fromlist=['SecretManager'])
    secret_manager = secret_manager_mod.SecretManager(os.environ.get(args.secret_manager_connection_env).strip("'"),
                                                      args.keys_dir)
    # start registrator routine
    log.info("Initializing CLI wrappers...")
    tonos_cli = TonosCli(cli_path=args.tonos_cli_path, cwd=args.tonos_cli_cwd,
                         config_url=args.tonos_config_url, abi_path=args.tonos_cli_abi_path,
                         tvc_path=args.tonos_cli_tvc_path)
    fift_cli = FiftCli(cli_path=args.fift_cli_path, includes=args.fift_includes)
    lite_client = TonLiteClient(client_path=args.lite_client_path,
                                server_addr=args.lite_client_network_address,
                                client_pub_key=args.lite_server_pub_key)
    validation_engine_console = TonValidatorEngineConsole(args.validator_engine_path, 
                                                          client_key=args.client_key,
                                                          server_pub_key=args.server_pub_key,
                                                          server_addr=args.validator_network_address)

    log.info("Initializing LogStash client...")
    LogStashClient.configure_client("tonlogstash", 5959)

    log.info("Starting routines...")
    LogStashClient.start_client()
    # Validator
    elections_routine = ElectionsRoutine(work_dir=os.path.join(args.work_dir, "elections"),
                                         validation_engine_console=validation_engine_console,
                                         lite_client=lite_client,
                                         tonos_cli=tonos_cli,
                                         fift_cli=fift_cli,
                                         secret_manager=secret_manager,
                                         max_sync_diff=args.validator_max_sync_diff,
                                         stake_to_make=args.default_election_stake,
                                         stake_max_factor=args.stake_max_factor).start()
    # Queue
    QueueRoutine(elections_routine=elections_routine,
                 validation_engine_console=validation_engine_console,
                 queue_provider=queue_provider).start()
    log.info("All routines started")

    while True:
        try:
            log.info("Still alive")
            # main routine
            time.sleep(60)
        except Exception:
            log.exception("Main routine failed")
            pass


def configure_logging(log_dir):
    loggers = {
        "": {
            "file": "toncontrol.log"
        },
        "elections": {
            "file": "elections.log"
        },
        "toncontrol | qcontroller": {
            "propagate": True
        },
        "logstash_client": {
            "file": "telemetry.log"
        },
        # external libs
        "tonvalidator | toncommon": {
            "file": "tonutils.log"
        }
    }
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    default_formatter = logging.Formatter('%(asctime)s::%(name)s::%(levelname)s::%(message)s')
    for logger_names, logger_settings in loggers.items():
        for logger_name in logger_names.split("|"):
            logger_name = logger_name.strip()
            logger = logging.getLogger(logger_name)
            logger.propagate = logger_settings.get('propagate', False)
            logger.setLevel(logging.DEBUG)
            if not logger.propagate:
                # if not propagate, then attach stdout. otherwise 'base' will provide this handler
                fh_stdout = logging.StreamHandler()
                fh_stdout.setLevel(logging.DEBUG)
                fh_stdout.setFormatter(default_formatter)
                logger.addHandler(fh_stdout)
            if "file" in logger_settings:
                log_file = os.path.join(log_dir, logger_settings["file"])
                logger.info("Logging to: {}".format(log_file))
                # create the file logging handler
                fh = RotatingFileHandler(log_file, maxBytes=50 * 1024 * 1024,
                                         backupCount=2)
                fh.setFormatter(default_formatter)
                fh.setLevel(logging.DEBUG)
                logger.addHandler(fh)
            # add handler to logger object
            logger.info("Logger initialized")


if __name__ == "__main__":
    try:
        main()
    except:
        log = logging.getLogger("")
        log.exception("Failed to start toncontrol")
