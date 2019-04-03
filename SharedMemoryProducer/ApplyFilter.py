import matplotlib.pyplot as plt
import numpy as np
import copy

a = 2
freq = 3
time = np.linspace(0, 2*np.pi, int(1000/freq))

x = list(map(lambda t: a*np.cos(t)/(1+np.sin(t)**2), time))
y = list(map(lambda t: a*np.sin(t)*np.cos(t)/(1+np.sin(t)**2), time))

noise_std = 0.02
x_noisy = np.array(x) + np.random.normal(0, noise_std, np.array(x).shape)
y_noisy = np.array(y) + np.random.normal(0, noise_std, np.array(y).shape)

b = np.array([0.004824343,0.019297373,0.028946060,0.019297373,0.004824343])
a = np.array([1.000000,-2.369513,2.313988,-1.054665,0.187379])


coordinates_unfiltered = np.ones((2,b.shape[0]))
coordinates_unfiltered[0,:] = coordinates_unfiltered[0,:]*x_noisy[0]
coordinates_unfiltered[1,:] = coordinates_unfiltered[1,:]*y_noisy[0]

coordinates_filtered = copy.copy(coordinates_unfiltered)


data_filtered = np.zeros((2,x_noisy.shape[0]))


for i in range(0, len(x)):
    # shift data
    coordinates_unfiltered[:, 1:] = coordinates_unfiltered[:, 0:-1]
    coordinates_filtered[:, 1:] = coordinates_filtered[:, 0:-1]

    # add new unfiltered data
    coordinates_unfiltered[:,0] = [x_noisy[i], y_noisy[i]]

    # apply filter and add to filtered data
    coordinates_filtered[0,0] = (b.dot(coordinates_unfiltered[0,:])
                            - a[1:].dot(coordinates_filtered[0,1:]))/a[0]
    coordinates_filtered[1,0] = (b.dot(coordinates_unfiltered[1,:])
                            - a[1:].dot(coordinates_filtered[1,1:]))/a[0]

    data_filtered[:,i] = coordinates_filtered[:,0]


plt.plot(x,y, 'c')
plt.plot(x_noisy, y_noisy, 'm')
plt.plot(data_filtered[0,:], data_filtered[1,:], 'g')
plt.show()
