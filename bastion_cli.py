import typer
from typing import List

from v1.connection import bastion_connection

app = typer.Typer()

@app.command()
def connect(bastion_name: str = typer.Option(..., "--bastion-name", help="Name of the bastion instance in AWS"),
            key_path: str = typer.Option(..., "--key-path", help="Path to the SSH key in your computer to connect to the bastion"),
            username: str = typer.Option(..., help="Bastion username to connect to the bastion"),
            wait_ssh: int = typer.Option(10, "--wait-ssh", help="Seconds to wait for the SSH service to be ready")):
    bastion_connection(bastion_name, key_path, username, wait_ssh)

@app.command()
def about():
    started = typer.style("started", fg=typer.colors.GREEN, bold=True)
    stopped = typer.style("stopped", fg=typer.colors.RED, bold=True)

    lines: List[str] = [
        "This CLI starts a bastion session to manage the bastion and the resources in the private network. It maintains the bastion stopped when not in use to save costs and for security reasons.",
        f"\nThe bastion is {started} when a user wants to connect to the private network and {stopped} when the user disconnects.",
        "\nYou must setup your AWS credentials before using this CLI. You can do this by running `aws configure` in your terminal.",
        "\nUsage:",
        "    $ python main.py connect --key-path <path_to_ssh_key> --username <bastion_username>"
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