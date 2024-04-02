# Bastion Manager: Securely Manage AWS EC2 Bastion Instances

The Bastion Manager script provides a robust solution for managing AWS EC2 instances used as bastion hosts. This tool automates the process of starting and stopping bastion instances, thereby enhancing security by ensuring these critical resources are only active when needed. By facilitating both SSH and SSM connections, the script offers a versatile way to securely connect to private instances within a VPC, minimizing the risk of unauthorized access to these gateways.

## Features

- **Automated Management**: Automatically start and stop EC2 instances serving as bastion hosts to tighten security and reduce exposure to potential threats.
- **Connection Flexibility**: Supports establishing secure SSH and SSM connections for interactive sessions or executing single commands, catering to various operational needs.
- **Operational Intelligence**: Checks the current state of the bastion instance, allowing users to make informed decisions on starting or stopping the instance based on its status.

## Getting Started

### Prerequisites

- AWS CLI installed and configured with the necessary permissions to manage EC2 and SSM.
- Python 3.x and pip installed on your machine.
- SSM Agent installed on the bastion instance for SSM connections. Ensure your local machine is configured to use AWS SSM for interactive sessions.

### Setup

1. **Create a Virtual Environment**: Isolate the project dependencies by creating a virtual environment.

    ```bash
    python -m venv v1cli-env
    source v1cli-env/bin/activate
    ```

2. **Install Requirements**: Install the project dependencies using pip.
    ```bash
    pip install -r requirements.txt
    ```

### Running the CLI
To get started with the Bastion Manager CLI, you can use the following commands:

- To learn about the CLI:
    ```bash
    python main.py connect about
    ```

- For help on establishing an SSH or SSM connection:
    ```bash
    python main.py connect ssh --help
    python main.py connect ssm --help
    ```
These commands provide detailed instructions on how to initiate connections or manage your bastion instances effectively.

### Interactive and Single Command Sessions

*SSH and SSM Interactive Sessions*: Establish an interactive shell session to manage your instances directly.

*Executing Single Commands*: Quickly run commands on your instances without starting an interactive session, ideal for automation tasks.

### Managing Instance State

Before connecting, the script checks if the target bastion instance is running. If not, it offers options to start it, ensuring that you can always connect when needed. Once your work is done, you can choose to stop the instance, thereby reducing the attack surface and potential costs.

## Important Notes
- SSM Agent: To use the SSM Interactive session feature, ensure the SSM Agent is installed on your bastion instance. Your local machine must also be configured to support SSM sessions.

- Security Best Practices: Always follow AWS security best practices for managing EC2 instances and access credentials.

- By adhering to these guidelines and utilizing the Bastion Manager script, you can enhance your infrastructure's security while maintaining the flexibility needed for efficient administration.