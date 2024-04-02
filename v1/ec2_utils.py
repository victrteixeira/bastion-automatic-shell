from typing import List
import boto3
import botocore.exceptions
import sys
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter

from v1.logger import LoggerDefinition

class BastionDefinition:
    """
    Defines a class that encapsulates operations related to AWS EC2 bastion instances,
    including finding instances by name, checking and changing instance states, and
    managing instance connectivity.
    """
    def __init__(self):
        """
        Initializes the BastionDefinition instance by setting up AWS clients for EC2 and SSM,
        and configuring a logger for logging purposes.
        """
        self.bastion = None
        self.client = boto3.client('ec2')
        self.ssm = boto3.client('ssm')
        self.logger = LoggerDefinition.logger()
    
    def find_instance_by_name(self, bastion_name: str = None) -> str:
        """
        Searches for an EC2 instance by its name tag. If multiple instances have the same name,
        the first match is used. This function can recursively prompt the user to select an
        instance if the initial name search fails.

        Parameters:
            bastion_name (str, optional): The name of the bastion instance to find. Defaults to None.

        Returns:
            str: The instance ID of the found bastion instance.

        Notes:
            If no instance is found with the given name, the user is prompted to select an instance
            from a list of all instances.
        """
        if bastion_name is not None:
            response = self.client.describe_instances()
            for reservation in response["Reservations"]:
                for instance in reservation["Instances"]:
                    for tag in instance["Tags"]:
                        if tag["Key"] == "Name" and bastion_name.lower() in tag["Value"].lower():
                            self.bastion = instance["InstanceId"]
                            return self.bastion

        if self.bastion is None:
            self.logger.warning(f"No bastion instance found for this name: {bastion_name}.")
            list_instance_names: List[str] = self.list_instance_names()
            selected_bastion_name: str = self.select_instance(list_instance_names)
            return self.find_instance_by_name(selected_bastion_name)

        return self.bastion
    
    def get_instance_state(self, instance_id: str) -> str:
        """
        Retrieves the current state of a specified EC2 instance.

        Parameters:
            instance_id (str): The ID of the instance whose state is to be checked.

        Returns:
            str: The current state of the instance ('running', 'stopped', etc.).

        Raises:
            SystemExit: If the instance state is neither 'stopped' nor 'running', or if an
                        error occurs while fetching the instance state.
        """
        try:
            response = self.client.describe_instance_status(InstanceIds=[instance_id], IncludeAllInstances=True)
            state = response["InstanceStatuses"][0]["InstanceState"]["Name"]

            if state not in ["running", "stopped"]:
                self.logger.error("Bastion is neither stopped or running")
                sys.exit(1)

            return state
        except botocore.exceptions.BotoCoreError as e:
            self.logger.error(f"Error getting bastion state: {e}")
            sys.exit(1)

    def start_instance(self, instance_id: str):
        """
        Starts a specified EC2 instance and waits until it enters the 'running' state.

        Parameters:
            instance_id (str): The ID of the instance to start.

        Raises:
            SystemExit: If an error occurs while starting the instance.
        """
        try:
            self.client.start_instances(InstanceIds=[instance_id])
            self.logger.info(f"Starting bastion instance")
            waiter = self.client.get_waiter('instance_running')
            self.logger.info("Waiting for bastion to enter 'running' state")
            waiter.wait(InstanceIds=[instance_id])
            self.logger.info(f"Bastion instance successfully started")
        except botocore.exceptions.BotoCoreError as e:
            self.logger.error(f"Error starting bastion: {e}")
            sys.exit(1)
        
    def stop_instance(self, instance_id: str) -> bool:
        """
        Stops a specified EC2 instance after confirming with the user. Waits until the
        instance enters the 'stopped' state before returning.

        Parameters:
            instance_id (str): The ID of the instance to stop.

        Returns:
            bool: True if the instance stop process was initiated, False if the user declines
                  to stop the instance.

        Raises:
            SystemExit: If an error occurs while stopping the instance.
        """
        confirm = typer.confirm(f"Do you want to stop the bastion instance: ${instance_id}?")
        if not confirm:
            self.logger.warning("Bastion instance not stopped")
            return True

        try:
            self.client.stop_instances(InstanceIds=[instance_id])
            self.logger.info(f"Stopping bastion instance")
            waiter = self.client.get_waiter('instance_stopped')
            waiter.wait(InstanceIds=[instance_id])
            self.logger.info(f"Bastion instance successfully stopped")
            return True
        except botocore.exceptions.BotoCoreError as e:
            self.logger.error(f"Error stopping bastion: {e}")
            sys.exit(1)
    
    def get_instance_public_ip(self, instance_id: str) -> str:
        """
        Retrieves the public IP address of a specified EC2 instance.

        Parameters:
            instance_id (str): The ID of the instance whose public IP address is to be retrieved.

        Returns:
            str: The public IP address of the instance.

        Raises:
            SystemExit: If an error occurs while fetching the public IP address or if the instance
                        does not have a public IP address.
        """
        response = self.client.describe_instances(InstanceIds=[instance_id])
        try:
            publicIpAdrr = response["Reservations"][0]["Instances"][0]["PublicIpAddress"]
            return publicIpAdrr
        except Exception as e:
            self.logger.error(f"Error getting bastion public ip: {e}")
            self.logger.warning(f"Check if the selected bastion instance has a public IP address")
            sys.exit(1)

    def list_instance_names(self) -> List[str]:
        """
        Lists the names of all EC2 instances based on the 'Name' tag.

        Returns:
            List[str]: A list of instance names.
        """
        instances: List[str] = []
        response = self.client.describe_instances()
        for reservation in response["Reservations"]:
            for instance in reservation["Instances"]:
                for tag in instance["Tags"]:
                    if tag["Key"] == "Name":
                        instances.append(tag["Value"])

        return instances
    
    def select_instance(self, instances: List[str]) -> str:
        """
        Prompts the user to select an EC2 instance from a provided list of instance names. The selection
        is facilitated through an interactive console interface.

        Parameters:
            instances (List[str]): A list of instance names to choose from.

        Returns:
            str: The name of the selected instance.

        Raises:
            SystemExit: If the user exits the selection process.
        """
        console = Console()
        table = Table(title="Instances", show_lines=True, header_style="bold magenta")
        table.add_column("Instance Name", style="dim", justify="center")
        for instance in instances:
            table.add_row(instance)

        console.print(Panel.fit(table, title="Select a bastion instance (type 'exit' to cancel)", border_style="green"))
        completer = WordCompleter(instances + ["exit"], ignore_case=True, sentence=True)
        instance = prompt("Select an instance: ", completer=completer)

        if instance == "exit":
            self.logger.warning("Operation cancelled by user")
            sys.exit(0)

        return instance