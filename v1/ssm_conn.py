import subprocess
import sys
import time

import boto3

from v1.logger import LoggerDefinition

logger = LoggerDefinition().logger()
ssm = boto3.client("ssm")

def ssm_agent_conn(instance_id: str,):
    command = ["aws", "ssm", "start-session", "--target", instance_id]
    try:
        process = subprocess.Popen(command)
        while True:
            if process.poll() is not None: # TODO: Include a timeout to maintain the connection open and running, here and for the SSH as
                return process.returncode
            time.sleep(1)
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to start session: {e}")
        sys.exit(1)

def ssm_agent_command(command: str, instance_id: str) -> bool:
    response = ssm.send_command(
        InstanceIds=[instance_id],
        DocumentName="AWS-RunShellScript",
        Comment="Automated command sent by V1 CLI",
        Parameters={"commands": [command]}
    )

    command_id = response["Command"]["CommandId"]
    time.sleep(2)

    output = ssm.get_command_invocation(
        CommandId=command_id,
        InstanceId=instance_id
    )

    if output["Status"] != "Success":
        logger.error(f"Command failed: {output['Status']}")
        if 'StandardErrorContent' in output:
            logger.error(f"Error: {output['StandardErrorContent']}")

        return False

    logger.info(f"Command executed successfully: {output['StandardOutputContent']}")
    return True