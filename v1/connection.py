import time
from v1.bastion import BastionDefinition
from v1.logger import LoggerDefinition
from v1.ssh_conn import SSHDefinition
import botocore.exceptions
import sys

def bastion_connection(bastion_name: str, key_path: str, username: str, wait_ssh: int):
    logger = LoggerDefinition().logger()
    bastion = BastionDefinition()

    if not check_aws_configuration(bastion.client, logger):
        logger.critical("AWS configuration is not properly set up. Exiting.")
        sys.exit(1)

    bastion_id = bastion.find_bastion_instance(bastion_name)
    bastion_state = bastion.get_bastion_state(bastion_id)

    if bastion_state == 'stopped':
        logger.info("Bastion stopped, starting it")
        bastion.start_bastion(bastion_id)
        logger.info(f"Waiting {wait_ssh} seconds for SSH service to initialize.")
        time.sleep(wait_ssh)


    logger.info("Bastion is now running.")

    host = bastion.bastion_public_ip(bastion_id)
        
    sc = SSHDefinition()
    sc.ssh_connector(host=host, username=username, key_path=key_path)
    sc.ssh_terminal_channel(bastion=bastion, bastion_id=bastion_id)

def check_aws_configuration(client, logger) -> bool:
    try:
        client.describe_regions()
    except botocore.exceptions.NoCredentialsError as e:
        logger.error("AWS credentials not found: %s", e.args)
        return False
    except botocore.exceptions.PartialCredentialsError as e:
        logger.error("AWS credentials are incomplete: %s", e.args)
        return False
    except botocore.exceptions.ClientError as e:
        logger.error("Authentication failure with AWS: %s", e.args) 
        return False
        
    return True
