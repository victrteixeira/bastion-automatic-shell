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
    def __init__(self):
        self.bastion = None
        self.client = boto3.client('ec2')
        self.ssm = boto3.client('ssm')
        self.logger = LoggerDefinition.logger()
    
    def find_instance_by_name(self, bastion_name: str = None) -> str:
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
    
    def get_instance_state(self, instance_id: str) -> str: # TODO: Check for errors here
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
        response = self.client.describe_instances(InstanceIds=[instance_id])
        try:
            publicIpAdrr = response["Reservations"][0]["Instances"][0]["PublicIpAddress"]
            return publicIpAdrr
        except Exception as e:
            self.logger.error(f"Error getting bastion public ip: {e}")
            self.logger.warning(f"Check if the selected bastion instance has a public IP address")
            sys.exit(1)

    def list_instance_names(self) -> List[str]:
        instances: List[str] = []
        response = self.client.describe_instances()
        for reservation in response["Reservations"]:
            for instance in reservation["Instances"]:
                for tag in instance["Tags"]:
                    if tag["Key"] == "Name":
                        instances.append(tag["Value"])

        return instances
    
    def select_instance(self, instances: List[str]) -> str:
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