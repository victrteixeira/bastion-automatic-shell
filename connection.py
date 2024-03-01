from bastion import BastionDefinition
from logger import LoggerDefinition
from ssh_conn import SSHDefinition

def connect_to_bastion(bastion: BastionDefinition):
    logger = LoggerDefinition().logger()

    bastion_id = bastion.find_bastion_instance()
    bastion_state = bastion.get_bastion_state(bastion_id)
    key_path = "/tmp/bastion_test.pem" # TODO: Pass it and also the 'username' as a variable, not hardcoded
    username = "ec2-user"

    if bastion_state is None:
        logger.error("Bastion is neither stopped or running")
        raise ValueError("Bastion is not in a valid state")

    if bastion_state == 'stopped':
        logger.info("Bastion stopped, starting it")
        bastion.start_bastion(bastion_id)

    host = bastion.bastion_public_ip(bastion_id)
        
    sc = SSHDefinition()
    sc.ssh_connector(host=host, username=username, key_path=key_path)
    sc.ssh_terminal_channel(bastion=bastion, bastion_id=bastion_id)
    
