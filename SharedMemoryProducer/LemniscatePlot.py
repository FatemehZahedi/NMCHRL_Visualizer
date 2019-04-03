import matplotlib.pyplot as plt
import numpy as np

a = 2
freq = 3
time = np.linspace(0, 2*np.pi, int(1000/freq))

x = list(map(lambda t: a*np.cos(t)/(1+np.sin(t)**2), time))
y = list(map(lambda t: a*np.sin(t)*np.cos(t)/(1+np.sin(t)**2), time))


plt.plot(x, y, 'c')
plt.show()
