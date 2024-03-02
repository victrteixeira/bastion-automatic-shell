import boto3
import botocore.exceptions

from v1.logger import LoggerDefinition

# TODO: Check the try/except blocks usage here
class BastionDefinition(): 
    def __init__(self):
        self.bastion = None
        self.client = boto3.client('ec2')
        self.logger = LoggerDefinition().logger()
    
    def find_bastion_instance(self) -> str: # TODO: Check for errors here
        response = self.client.describe_instances()
        for reservation in response["Reservations"]:
            for instance in reservation["Instances"]:
                for tag in instance["Tags"]:
                    if tag["Key"] == "Name" and "bastion" in tag["Value"].lower():
                        self.bastion = instance["InstanceId"]
                        return self.bastion

        if self.bastion is None:
            self.logger.error(f"No bastion found")
            raise Exception("No bastion found")

        return self.bastion
    
    def get_bastion_state(self, instance_id: str) -> str: # TODO: Check for errors here
        response = self.client.describe_instance_status(InstanceIds=[instance_id], IncludeAllInstances=True)
        state = response["InstanceStatuses"][0]["InstanceState"]["Name"]
        return state

    def start_bastion(self, instance_id: str):
        try:
            self.client.start_instances(InstanceIds=[instance_id])
            self.logger.info(f"Starting bastion instance")
            waiter = self.client.get_waiter('instance_running')
            waiter.wait(InstanceIds=[instance_id])
            self.logger.info(f"Bastion instance successfully started")
        except botocore.exceptions.BotoCoreError as e:
            self.logger.error(f"Error starting bastion: {e}")
            raise
        
    def stop_bastion(self, instance_id: str):
        try:
            self.client.stop_instances(InstanceIds=[instance_id])
            self.logger.info(f"Stopping bastion instance")
            waiter = self.client.get_waiter('instance_stopped')
            waiter.wait(InstanceIds=[instance_id])
            self.logger.info(f"Bastion instance successfully stopped")
        except botocore.exceptions.BotoCoreError as e:
            self.logger.error(f"Error stopping bastion: {e}")
            raise
    
    def bastion_public_ip(self, instance_id: str) -> str: # TODO: Check for errors here
        response = self.client.describe_instances(InstanceIds=[instance_id])
        publicIpAdrr = response["Reservations"][0]["Instances"][0]["PublicIpAddress"]
        return publicIpAdrr