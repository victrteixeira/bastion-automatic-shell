import time
import subprocess
import select
import paramiko
import sys
from paramiko.ssh_exception import NoValidConnectionsError, SSHException
import botocore.exceptions

from v1.ec2_utils import BastionDefinition

class ConnectorDefinition(BastionDefinition): # TODO: Include single command execution for SSH as it happens with SSM Send_Command
    def __init__(self):
        super().__init__()
        paramiko.util.log_to_file('/tmp/paramiko.log')
        self.ssh_client = paramiko.SSHClient()
        self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.timeouts = {
            'ssh': 10*60,
            'ssm': 60*60
        }

    def validate_aws_configuration(self, client) -> bool:
        try:
            client.describe_regions()
        except botocore.exceptions.NoCredentialsError as e:
            self.logger.error("AWS credentials not found: %s", e.args)
            return False
        except botocore.exceptions.PartialCredentialsError as e:
            self.logger.error("AWS credentials are incomplete: %s", e.args)
            return False
        except botocore.exceptions.ClientError as e:
            self.logger.error("Authentication failure with AWS: %s", e.args) 
            return False
        
        return True
    
    def ensure_instance_operational(self, bastion_name: str, wait_ssh=None) -> str:
        if not self.validate_aws_configuration(self.client):
            self.logger.critical("AWS configuration is not properly set up. Exiting.")
            sys.exit(1)

        instance_id = self.find_instance_by_name(bastion_name)
        instance_state = self.get_instance_state(instance_id)

        if instance_state == 'stopped':
            self.logger.info("Bastion stopped, starting it")
            self.start_instance(instance_id)
            if wait_ssh is not None:
                self.logger.info(f"Waiting {wait_ssh} seconds for SSH service to initialize.")
                time.sleep(wait_ssh)
            self.logger.info("Bastion is now running.")
        
        return instance_id
    
    def handle_ssh_interaction(self, bastion_name: str, key_path: str, username: str, wait_ssh: int):
        instance_id = self.ensure_instance_operational(bastion_name)

        host = self.get_instance_public_ip(instance_id)
            
        self.connect_to_bastion_via_ssh(host=host, username=username, key_path=key_path)
        self.start_ssh_interactive_session(instance_id)

    def connect_to_bastion_via_ssh(self, host: str, username: str, key_path: str):
        try:
            self.ssh_client.connect(hostname=host, username=username, key_filename=key_path)
            self.logger.info('Successfully connected to bastion')
        except NoValidConnectionsError as e:
            self.logger.error(f"SSH Connection could not be established: {e}")
            self.logger.warning("""It, perhaps, was caused due the SSH service is not ready yet.
            You should try --wait-ssh 'seconds' option to wait for the SSH service to be ready.
            $ python main.py connect --help""")
            sys.exit(1)
        except SSHException as e:
            self.logger.error(f"SSH Error Connection Happened: {e}")
            sys.exit(1)

    def start_ssh_interactive_session(self, bastion_id: str):
        try:
            channel = self.ssh_client.invoke_shell()
            self.logger.info('Interactive SSH session established')

            last_input_time = time.time()

            while True:
                r, _, _ = select.select([channel, sys.stdin], [], [], 0.1)
                current_time = time.time()

                if channel in r:
                    while channel.recv_ready():
                        sys.stdout.write(channel.recv(1024).decode('utf-8'))
                        sys.stdout.flush()
                        last_input_time = current_time

                    while channel.recv_stderr_ready():
                        sys.stderr.write(channel.recv_stderr(1024).decode('utf-8'))
                        sys.stderr.flush()
                        last_input_time = current_time

                if sys.stdin in r:
                    command = sys.stdin.readline()
                    if command.lower().strip() == 'exit':
                        self.logger.info('Exiting the interactive shell')
                        break

                    channel.send(command)

                if channel.exit_status_ready():
                    break

                if (current_time - last_input_time) > self.timeouts['ssh']:
                    self.logger.info(f"Session timeout reached ({self.timeouts['ssh']} seconds). Terminating process. Instance was maintained running.")
                    break
        except paramiko.ssh_exception.ChannelException as e:
            self.logger.error(f"Channel Error Happened: {e}")
            sys.exit(1)
        finally:
            if self.ssh_client.get_transport() is None or not self.ssh_client.get_transport().is_active():
                self.logger.info('No SSH connection to close')
                return
            
            self.logger.info('Closing SSH connection')
            self.ssh_client.close()

            if self.stop_instance(bastion_id) is True:
                self.logger.info('Process finished.')

    def handle_ssm_interaction(self, interactive: bool, command: str, bastion_name: str): # TODO: Fix this function, it should have a better name, better logs, and a better structure
        instance_id = self.ensure_instance_operational(bastion_name)

        if command is not None and interactive is False and bastion_name is not None:
            self.logger.info(f"Running command {command} using secure SSM Agent connection.")
            command_result = self.execute_ssm_command(command, instance_id)
            if command_result is not True: # TODO: Find a better way to finish this process
                sys.exit(1)
                
            sys.exit(0)    

        if interactive is True and command is None:
            self.logger.info(f"Starting interactive shell using secure SSM Agent connection.")
            process = self.start_ssm_session(instance_id) # TODO: Find a way to handle possible errors here, and send an informative error message to the user

            if process != 0:
                self.logger.error(f"SSM session ended with exit_code: {process}")
                sys.exit(process)

            self.logger.info(f"SSM session ended successfully with exit_code: {process}")
            sys.exit(process)

    def start_ssm_session(self, instance_id: str,):
        command = ["aws", "ssm", "start-session", "--target", instance_id]
        last_input_time = time.time()

        try:
            process = subprocess.Popen(command)
            while True:
                exit_code = process.poll()
                if exit_code is not None: # TODO: Include a timeout to maintain the connection open and running, here and for the SSH
                    break
                if time.time() - last_input_time > self.timeouts['ssm']:
                    self.logger.info(f"Session timeout reached ({self.timeouts['ssm']} seconds). Terminating process. Instance was maintained running.")
                    process.terminate()
                    process.wait()
                    exit_code = -1
                    return exit_code
                time.sleep(1)

            if exit_code != 0:
                return exit_code
            
            self.stop_instance(instance_id)
            return exit_code
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to start session: {e}")
            sys.exit(1)

    def execute_ssm_command(self, command: str, instance_id: str) -> bool:
        response = self.ssm.send_command(
            InstanceIds=[instance_id],
            DocumentName="AWS-RunShellScript",
            Comment="Automated command sent by V1 CLI",
            Parameters={"commands": [command]}
        )

        command_id = response["Command"]["CommandId"]
        time.sleep(2)

        output = self.ssm.get_command_invocation(
            CommandId=command_id,
            InstanceId=instance_id
        )

        if output["Status"] != "Success": # FIXME: Some processes don't return a sucess status immediately, causing a false negative: "sudo systemctl restart amazon-ssm-agent"
            self.logger.error(f"Command failed: {output['Status']}")
            if 'StandardErrorContent' in output:
                self.logger.error(f"Error: {output['StandardErrorContent']}")

            return False

        self.logger.info(f"Command executed successfully: {output['StandardOutputContent']}")
        return True