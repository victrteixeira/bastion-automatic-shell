from bastion import BastionDefinition
from connection import connect_to_bastion

def start_bastion():
    try:
        bastion = BastionDefinition()
        connect_to_bastion(bastion)
    except Exception as e:
        print(f"Error: {str(e)}")
        return

if __name__ == "__main__":
    start_bastion()