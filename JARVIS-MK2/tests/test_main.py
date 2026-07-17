import subprocess
import time
import signal
import sys

proc = subprocess.Popen([sys.executable, 'main.py'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
time.sleep(2)
proc.send_signal(signal.SIGINT)
stdout, stderr = proc.communicate()
print("STDOUT:")
print(stdout.decode())
print("STDERR:")
print(stderr.decode())