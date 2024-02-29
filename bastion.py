import boto3

class BastionDefinition(): 
    def __init__(self):
        self.bastion = None
        self.client = boto3.client('ec2')
    
    def find_bastion_instance(self) -> str:
        response = self.client.describe_instances()
        for reservation in response["Reservations"]:
            for instance in reservation["Instances"]:
                for tag in instance["Tags"]:
                    if tag["Key"] == "Name" and "bastion" in tag["Value"].lower():
                        self.bastion = instance["InstanceId"]
                        return self.bastion

        if self.bastion is None:
            raise Exception("No bastion found")

        return self.bastion
    
    def get_bastion_state(self, instance_id: str) -> str:
        response = self.client.describe_instance_status(InstanceIds=[instance_id], IncludeAllInstances=True)
        state = response["InstanceStatuses"][0]["InstanceState"]["Name"]
        return state

    def start_bastion(self, instance_id: str) -> bool:
        self.client.start_instances(InstanceIds=[instance_id])
        waiter = self.client.get_waiter('instance_running')
        waiter.wait(InstanceIds=[instance_id])
        return True
    
    def stop_bastion(self, instance_id: str) -> bool:
        self.client.stop_instances(InstanceIds=[instance_id])
        waiter = self.client.get_waiter('instance_stopped')
        waiter.wait(InstanceIds=[instance_id])
        return True
    
    def bastion_public_ip(self, instance_id: str) -> str:
        response = self.client.describe_instances(InstanceIds=[instance_id])
        return response["Reservations"][0]["Instances"][0]["PublicIpAddress"]