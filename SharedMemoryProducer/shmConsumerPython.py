import sysv_ipc
import mmap
import sys
import os
import numpy as np

def main():
    filepath = '/home/tannerbitz/Documents/shmfile'

    key = sysv_ipc.ftok(filepath, 255)
    # Open shared memory.
    #   - flags=0 attempts to open an existing shared memory segment
    #   - mode
    shm = sysv_ipc.SharedMemory(key)

    int_bytestr = shm.read(4);

    nFloats = int.from_bytes(int_bytestr, byteorder='little', signed=False)

    float_bytestr = shm.read(nFloats*4, offset=4)

    we_all_float_on = np.frombuffer(float_bytestr, dtype=np.single)
    print(we_all_float_on)



main()
