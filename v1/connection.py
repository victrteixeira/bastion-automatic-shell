import time
from v1.bastion import BastionDefinition
from v1.logger import LoggerDefinition
from v1.ssh_conn import SSHDefinition
import botocore.exceptions
import sys

from v1.ssm_conn import ssm_agent_command, ssm_agent_conn

def ssh_connection(bastion_name: str, key_path: str, username: str, wait_ssh: int):
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
    sc.ssh_session(host=host, username=username, key_path=key_path)
    sc.ssh_interactive_shell(bastion=bastion, bastion_id=bastion_id)

def ssm_connection(interactive: bool, command: str, bastion_name: str): # TODO: Fix this function, it should have a better name, better logs, and a better structure
    bastion = BastionDefinition() # TODO: Find a way to reutilize either bastion objects for both functions
    logger = LoggerDefinition().logger()

    if not check_aws_configuration(bastion.client, logger):
        logger.critical("AWS configuration is not properly set up. Exiting.")
        sys.exit(1)

    bastion_id = bastion.find_bastion_instance(bastion_name)
    bastion_state = bastion.get_bastion_state(bastion_id)

    if bastion_state == 'stopped':
        logger.info("Bastion stopped, starting it")
        bastion.start_bastion(bastion_id)

    logger.info("Bastion is now running.")

    if command is not None and interactive is False and bastion_name is not None:
        logger.info(f"Running command {command} using secure SSM Agent connection.")
        process = ssm_agent_command(command, bastion_id)
        if process is not True: # TODO: Find a better way to finish this process
            sys.exit(1)
            
        sys.exit(0)    

    if interactive is True and command is None:
        logger.info(f"Starting interactive shell using secure SSM Agent connection.")
        process = ssm_agent_conn(bastion_id) # TODO: Find a way to handle possible errors here, and send an informative error message to the user

        if process != 0:
            logger.error("SSM session ended, a possible error ocurred.")
            sys.exit(process)

        logger.info("SSM session ended successfully.")
        sys.exit(process)

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
