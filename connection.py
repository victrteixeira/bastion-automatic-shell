import paramiko
import sys
from bastion import BastionDefinition

def connect_to_bastion(bastion: BastionDefinition):
    bastion_id = bastion.find_bastion_instance()
    bastion_state = bastion.get_bastion_state(bastion_id)

    if bastion_state is None:
        raise Exception("Bastion is not in a valid state")

    if bastion_state == 'stopped':
        print("Bastion stopped, trying to start it right now")
        state = bastion.start_bastion(bastion_id)
        if state is False:
            raise Exception("Bastion could not be started")
        
    paramiko.util.log_to_file('/tmp/paramiko.log')

    key_path = "/tmp/bastion_test.pem"
    host = bastion.bastion_public_ip(bastion_id)
    username = "ec2-user"
        
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh_client.connect(hostname=host, username=username, key_filename=key_path)
        print("Successfully connected to bastion")

        # Opening a shell
        channel = ssh_client.invoke_shell()
        print("Interactive SSH session established")

        while True:
            while channel.recv_ready():
                sys.stdout.write(channel.recv(1024).decode("utf-8"))
                sys.stdout.flush()

            command = input()
            if command.lower() == 'exit':
                print("Exiting the interactive shell")
                break

            channel.send(command + "\n")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if ssh_client.get_transport() is not None and ssh_client.get_transport().is_active():
            print("Closing SSH connection")
            ssh_client.close()
            print("Stopping bastion instance")
            
            if bastion.stop_bastion(bastion_id) is True:
                print("Bastion stopped")
        else:
            print("No SSH connection to close")
    
