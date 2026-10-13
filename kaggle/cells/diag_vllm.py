# DIAGNOSTIC (run in the same session, after stopping cell 4): why did the vLLM server stop?
# Prints whether the server process is alive, its exit code, GPU memory, and the end of its log (errors first).
import subprocess, re
p = server_instance.process
print('vLLM process alive:', p is not None and p.poll() is None, '| exit code:', None if p is None else p.poll())
print(subprocess.run(['nvidia-smi', '--query-gpu=index,memory.used,memory.total', '--format=csv'],
                     capture_output=True, text=True).stdout)
log = open(server_instance.log_path, encoding='utf-8', errors='replace').read().splitlines()
print('log lines:', len(log), '| file:', server_instance.log_path)
bad = [l for l in log if re.search(r'Error|ERROR|Traceback|OOM|out of memory|Killed|exception', l)]
print('---- error-looking lines (last 25) ----')
print('\n'.join(bad[-25:]))
print('---- last 40 lines ----')
print('\n'.join(log[-40:]))
