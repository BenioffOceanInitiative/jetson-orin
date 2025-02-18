import subprocess as sp
from pathlib import Path

def get_remote_origin():
    ''' Get the remote origin URL , NON ASYNC FUNCTION'''
    working_dir ="/home/dan/BOI/jetson-orin-hardware-setup/orin_refactor"
    output = sp.check_output(['git', 'config', '--get', 'remote.origin.url'], cwd=working_dir)
    if output is None:
        print("Error getting remote origin")
        return None
    repo = Path(output.decode().strip())
    print(repo)
    status = sp.check_output(['git','status','-uno'],cwd=working_dir)
    message = status.decode().strip()
    if "Your branch is up to date" in message:
        print("Up to date, no need to pull")
    else:
        print(message)
print(get_remote_origin())
