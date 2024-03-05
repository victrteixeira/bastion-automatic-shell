import paramiko
import sys
from v1.bastion import BastionDefinition
from v1.logger import LoggerDefinition
from paramiko.ssh_exception import NoValidConnectionsError, SSHException

class SSHDefinition():
    def __init__(self):
        paramiko.util.log_to_file('/tmp/paramiko.log')
        self.logger = LoggerDefinition().logger()
        self.ssh_client = paramiko.SSHClient()
        self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    def ssh_connector(self, host: str, username: str, key_path: str):
        try:
            self.ssh_client.connect(hostname=host, username=username, key_filename=key_path)
            self.logger.info('Successfully connected to bastion')
        except NoValidConnectionsError as e:
            self.logger.error(f"SSH Connection could not be established: {e}")
            self.logger.warning("""It, perhaps, was caused due the SSH service is not ready yet.
            You should try --wait--ssh 'seconds' option to wait for the SSH service to be ready.
            $ python main.py connect --help""")
            sys.exit(1)
        except SSHException as e:
            self.logger.error(f"SSH Error Connection Happened: {e}")
            sys.exit(1)
    
    def ssh_terminal_channel(self, bastion: BastionDefinition, bastion_id: str):
        try:
            channel = self.ssh_client.invoke_shell()
            self.logger.info('Interactive SSH session established')

            while True:
                while channel.recv_ready():
                    sys.stdout.write(channel.recv(1024).decode("utf-8"))
                    sys.stdout.flush()

                command = input()
                if command.lower() == 'exit':
                    self.logger.info('Exiting the interactive shell')
                    break

                channel.send(command + "\n")
        except paramiko.ssh_exception.ChannelException as e:
            self.logger.error(f"Channel Error Happened: {e}")
            sys.exit(1)
        finally:
            if self.ssh_client.get_transport() is None or not self.ssh_client.get_transport().is_active():
                self.logger.info('No SSH connection to close')
                return
            
            self.logger.info('Closing SSH connection')
            self.ssh_client.close()

            if bastion.stop_bastion(bastion_id) is True:
                self.logger.info('Process finished.')