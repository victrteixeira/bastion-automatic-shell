import typer
from typing import List

from v1.connector import ConnectorDefinition

app = typer.Typer()
connect_app = typer.Typer()
app.add_typer(connect_app, name="connect")

@connect_app.command("ssh")
def connect_ssh(
            key_path: str = typer.Option(..., "--key-path", "-k", help="Path to the SSH key in your computer to connect to the bastion"),
            username: str = typer.Option(..., "--username", "-u", help="Bastion username to connect to the bastion"),
            interactive: bool = typer.Option(False, "--interactive-shell", "-it", help="Start an interactive session with the bastion using SSH"),
            command: str = typer.Option(None, "--command", "-c", help="Command to run in the SSH session"),
            bastion_name: str = typer.Option(None, "--bastion-name", help="Name of the bastion instance in AWS"),
            wait_ssh: int = typer.Option(20, "--wait-ssh", help="Seconds to wait for the SSH service to be ready")):
    ssh = ConnectorDefinition()
    ssh.handle_ssh_interaction(key_path, username, interactive, command, bastion_name, wait_ssh)

@connect_app.command("ssm")
def connect_ssm(
            interactive: bool = typer.Option(False, "--interactive-shell", "-it", help="Start an interactive session with the bastion using SSM Agent Connection"),
            command: str = typer.Option(None, "--command", "-c", help="Command to run in the SSM session"),
            bastion_name: str = typer.Option(None, "--bastion-name", help="Name of the bastion instance in AWS")):
    ssm = ConnectorDefinition()
    ssm.handle_ssm_interaction(interactive, command, bastion_name)

@connect_app.command("about")
def about():
    started = typer.style("started", fg=typer.colors.GREEN, bold=True)
    stopped = typer.style("stopped", fg=typer.colors.RED, bold=True)
    features = typer.style("features", fg=typer.colors.BLUE, bold=True)

    lines: List[str] = [
        "This CLI starts a instance session to manage it and the resources in the private network. It maintains the instance stopped, when not in use, if you want, to save costs and for security reasons.",
        f"\nThe instance is {started} when a user wants to connect to the private network and {stopped} when the user disconnects.",
        "\nYou must setup your AWS credentials before using this CLI. You can do this by running `aws configure` in your terminal.",
        "\nYou must have the Session Manager Plugin installed in your computer to use the SSM feature.",
        f"\nThis CLI has two main {features}:",
        "    - Connect to an instance using SSH or SSM, which starts an interactive session with the instance",
        "    - Run a single command in the instance using SSH or SSM",
        "\nUsage:",
        "    $ python main.py connect --help",
        "The CLI understands you already have the instances ready in your AWS account to handle SSH or SSM connections.",
    ]

    for line in lines:
        if line.startswith("\nYou"):
            typer.echo(typer.style(line, fg=typer.colors.YELLOW))
        elif "Usage:" in line:
            typer.echo(typer.style(line, fg=typer.colors.BLUE, bold=True))
        elif line.startswith("    $"):
            typer.echo(typer.style(line, fg=typer.colors.GREEN))
        else:
            typer.echo(line)