"""Defense against accidental outcome reads in the trusted baseline worker.

Python audit hooks are not an adversarial OS sandbox. Only versioned trusted
predictor code executes here, with no plugins, tools, arbitrary code or models.
"""
import os
import sys


def worker_environment():
    return {'PATH':os.defpath,'PYTHONHASHSEED':'0','PYTHONNOUSERSITE':'1',
            'PYTHONPATH':str(__import__('pathlib').Path(__file__).resolve().parents[2])}


def deny_external_io():
    def guard(event,args):
        if event in ('open','os.listdir','os.scandir','os.chdir','os.system','subprocess.Popen',
                     'socket.__new__','socket.connect','socket.getaddrinfo','ctypes.dlopen') or event.startswith('os.exec'):
            raise PermissionError('predictor external I/O denied')
    sys.addaudithook(guard)
