import time
import subprocess
import select
import paramiko
import sys
import botocore.exceptions

from enum import Enum, auto
from paramiko.ssh_exception import NoValidConnectionsError, SSHException

from v1.ec2_utils import BastionDefinition

class ServiceType(Enum):
    SSH = auto()
    SSM = auto()
class ConnectorDefinition(BastionDefinition):
    def __init__(self):
        super().__init__()
        paramiko.util.log_to_file('/tmp/paramiko.log')
        self.ssh_client = paramiko.SSHClient()
        self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.services = ['ssh', 'ssm']
        self.timeouts = {
            'ssh': 10*60,
            'ssm': 60*60
        }

    def handle_ssh_interaction(self, key_path: str, username: str, interactive: bool, command: str, bastion_name: str, wait_ssh: int):
        if interactive is False and command is None:
            self.logger.error("You must provide a command to execute when not using interactive mode.")
            sys.exit(1)

        instance_id = self.ensure_instance_operational(ServiceType.SSH, bastion_name, wait_ssh)
        host = self.get_instance_public_ip(instance_id)
        self.ssh_instance_connection_handler(host=host, username=username, key_path=key_path)

        if command is not None and interactive is False:
            self.run_ssh_command_and_exit(command)
        elif interactive is True and command is None:
            self.ssh_interactive_session_handler(instance_id)

    def handle_ssm_interaction(self, interactive: bool, command: str, bastion_name: str):
        if interactive is False and command is None:
            self.logger.error("You must provide a command to execute when not using interactive mode.")
            sys.exit(1)

        instance_id = self.ensure_instance_operational(ServiceType.SSM, bastion_name)

        if interactive is True and command is None:
            self.start_interactive_ssm_session(instance_id)
        elif command is not None and interactive is False:
            self.run_ssm_command_and_exit(command, instance_id)

    # ======= Utils
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
    
    def ensure_instance_operational(self, service: ServiceType, bastion_name: str, wait_ssh: int) -> str:
        if not self.validate_aws_configuration(self.client):
            self.logger.critical("AWS configuration is not properly set up. Exiting.")
            sys.exit(1)

        instance_id = self.find_instance_by_name(bastion_name)
        instance_state = self.get_instance_state(instance_id)

        if instance_state == 'stopped':
            self.logger.info("Bastion stopped, starting it")
            self.start_instance(instance_id)
            if service == ServiceType.SSH:
                self.logger.info(f"Waiting {wait_ssh} seconds for SSH service to initialize.")
                time.sleep(wait_ssh)
            self.logger.info("Bastion is now running.")
        
        return instance_id
    
    # ======= SSH
    def ssh_instance_connection_handler(self, host: str, username: str, key_path: str):
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

    def ssh_interactive_session_handler(self, bastion_id: str):
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

    def run_ssh_command_and_exit(self, command: str):
        self.logger.info(f"Running command '{command}' using SSH connection.")
        try:
            _, stdout, stderr = self.ssh_client.exec_command(command)
            output = stdout.read().decode()
            error = stderr.read().decode()

            exit_status = stdout.channel.recv_exit_status()

            if exit_status != 0:
                self.logger.error(f"Command failed with exit status: {exit_status} and error: {error}")
                sys.exit(exit_status)

            self.logger.info(f"Command executed successfully: {output}")
            self.ssh_client.close()
            sys.exit(0)
        except paramiko.ssh_exception.ChannelException as e:
            self.logger.error(f"Channel Error Happened: {e}")
            sys.exit(1)

    # ======= AWS SSM Agent
    def start_interactive_ssm_session(self, instance_id: str):
        self.logger.info(f"Starting interactive shell using secure SSM Agent connection for instance '{instance_id}'.")
        process_exit_code = self.ssm_session_handler(instance_id)
        if process_exit_code != 0:
            self.logger.error(f"SSM session ended with exit_code: {process_exit_code}")
            sys.exit(process_exit_code)

        self.logger.info(f"SSM session ended successfully")
        sys.exit(process_exit_code)

    def run_ssm_command_and_exit(self, command: str, instance_id: str):
        self.logger.info(f"Running command {command} using secure SSM Agent connection for instance '{instance_id}'.")
        process_exit_code = self.ssm_command_handler(command, instance_id)
        if process_exit_code != 0:
            self.logger.error(f"Command failed with exit_code: {process_exit_code}")
            sys.exit(process_exit_code)

        self.logger.info(f"Command executed successfully")
        sys.exit(process_exit_code)

    def ssm_session_handler(self, instance_id: str) -> int:
        command = ["aws", "ssm", "start-session", "--target", instance_id]
        last_input_time = time.time()

        try:
            process = subprocess.Popen(command)
            while True:
                exit_code = process.poll()
                if exit_code is not None:
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
        except (ValueError, subprocess.CalledProcessError) as e:
            self.logger.error(f"Failed to start session: {e}")
            sys.exit(1)

    def ssm_command_handler(self, command: str, instance_id: str) -> int:
        response = self.ssm.send_command(
            InstanceIds=[instance_id],
            DocumentName="AWS-RunShellScript",
            Comment="Automated command sent by V1 CLI",
            Parameters={"commands": [command]}
        )

        command_id = response["Command"]["CommandId"]

        max_retries = 12
        retry_count = 0
        wait_interval = 5

        while retry_count < max_retries:
            output = self.ssm.get_command_invocation(
                CommandId=command_id,
                InstanceId=instance_id
            )

            if output["Status"] == "Success":
                self.logger.info(f"Command executed successfully: {output['StandardOutputContent'].strip()}")
                return 0

            if output["Status"] in ["Failed", "Cancelled", "TimedOut"]:
                if 'StandardErrorContent' in output:
                    self.logger.error(f"Error: {output['StandardErrorContent']}")
                return 1
        
            time.sleep(wait_interval)
            retry_count += 1

        self.logger.error("Command status check timed out.")
        return 1
