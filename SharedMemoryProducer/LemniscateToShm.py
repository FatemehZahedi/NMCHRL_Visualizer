import numpy as np
import sysv_ipc
import time
import os
from functools import partial
from threading import Timer

# Globals
index = 0
a = 2
b = 2*np.sqrt(2)
freq = 2
T = np.linspace(0, 2*np.pi, int(1000/freq))

x = list(map(lambda t: a*np.cos(t)/(1+np.sin(t)**2), T))
y = list(map(lambda t: b*np.sin(t)*np.cos(t)/(1+np.sin(t)**2), T))



class Interval(object):

    def __init__(self, interval, function, args=[], kwargs={}):
        """
        Runs the function at a specified interval with given arguments.
        """
        self.interval = interval
        self.function = partial(function, *args, **kwargs)
        self.running  = False
        self._timer   = None

    def __call__(self):
        """
        Handler function for calling the partial and continuting.
        """
        self.running = False  # mark not running
        self.start()          # reset the timer for the next go
        self.function()       # call the partial function

    def start(self):
        """
        Starts the interval and lets it run.
        """
        if self.running:
            # Don't start if we're running!
            return

        # Create the timer object, start and set state.
        self._timer = Timer(self.interval, self)
        self._timer.start()
        self.running = True

    def stop(self):
        """
        Cancel the interval (no more function calls).
        """
        if self._timer:
            self._timer.cancel()
        self.running = False
        self._timer  = None

def CoordinateToShm(memory):
    global index
    coordinates = np.array([np.single(x[index]), np.single(y[index])], dtype=np.single)
    coordinatebytes = coordinates.tobytes()
    memory.write(coordinatebytes)
    index = int(index + 1) % len(x)

def main():
    # Create shared memory file
    dir = os.getcwd()
    file = "shm"
    shmfile = os.path.join(dir, file)
    f = open(shmfile,"w+")
    f.close()

    # Attach shared memory to process
    key = sysv_ipc.ftok(shmfile, 255)
    shm = sysv_ipc.SharedMemory(key, sysv_ipc.IPC_CREAT, size=256)


    # Interval Timer
    interval = Interval(0.001, CoordinateToShm, args=[shm]) #run every ms
    print("shmfile: {}".format(shmfile))
    print("Starting Interval, press CTRL+C to stop.")
    interval.start()

    while True:
        try:
            time.sleep(0.1)
        except KeyboardInterrupt:
            print("Shutting down")
            interval.stop()
            shm.detach()
            shm.remove()
            break



main()
