from bastion import BastionDefinition
from connection import connect_to_bastion

def start_bastion():
    bastion = BastionDefinition()
    connect_to_bastion(bastion)

if __name__ == "__main__":
    start_bastion()