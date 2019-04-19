import matplotlib.pyplot as plt
import numpy as np

a = 2
b = 2*np.sqrt(2)
freq = 3
time = np.linspace(0, 2*np.pi, int(1000/freq))

# x1 = list(map(lambda t: a*np.cos(t)/(1+np.sin(t)**2), time))
# y1 = list(map(lambda t: b*np.sin(t)*np.cos(t)/(1+np.sin(t)**2), time))
# x = np.sin(np.linspace(0, 2*np.pi, 1000))
# y = np.sin(np.linspace(0, 4*np.pi, 1000))
T = np.linspace(0, 2*np.pi, int(1000/freq))
x = list(map(lambda t: a*np.cos(t)/(1+np.sin(t)**2), T))
y = list(map(lambda t: b*np.sin(t)*np.cos(t)/(1+np.sin(t)**2), T))

plt.plot(x, y, 'c')
plt.show()
