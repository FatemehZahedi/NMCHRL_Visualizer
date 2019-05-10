import socket
import sys
import numpy as np
import time
import select

def main(argv):

    if (len(argv) != 2):
        print("2 Command Line Arguments Required")
        print("1. UDP Address")
        print("2. UDP Port")
        print("Example: python3 udp_server.py 192.168.0.100 8000")
        return

    addr = argv[0]
    port = argv[1]
    try:
        socket.inet_aton(addr)
    except:
        print("Error: UDP Address not acceptable")
        print(addr)
        return
    try:
        port = int(port)
    except:
        print("Error: UDP Port not acceptable")
        return

    # create socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # bind the socket to the port
    server_address = (addr, port)
    sock.bind(server_address)
    print("Server bound to {} {}".format(addr, port))

    # wait for client
    cli_msg, client_address = sock.recvfrom(4096)
    print("received {} bytes from {}".format(len(cli_msg), client_address))

    # bounds
    # x = [-0.18, 0.18]
    # y = [ 0.58, 0.94]

    # create dataset to loop through

    # mode 1
    des_x = np.zeros(5000)
    des_y = np.ones(5000)*(0.94+0.58)/2
    des_r = np.ones(5000)*(0.94-0.58)/15

    user_x = np.linspace(-0.15, 0, 5000)
    user_y = np.linspace(0.60, (0.94+0.58)/2, 5000)

    mode1 = np.zeros((5000, 16))
    mode1[:,0] = 1
    mode1[:,1] = des_x
    mode1[:,2] = des_y
    mode1[:,3] = des_r
    mode1[:,4] = user_x
    mode1[:,5] = user_y

    # mode 2
    exp_x = np.ones(5000)*(-0.1)
    exp_y = np.ones(5000)*(0.94+0.58)/2

    user_x2 = np.linspace(0, -0.1, 5000)
    user_y2 = np.ones(5000)*(0.94+0.58)/2

    mode2 = np.zeros((5000, 16))
    mode2[:,0] = 2
    mode2[:,1] = des_x
    mode2[:,2] = des_y
    mode2[:,3] = des_r
    mode2[:,4] = user_x2
    mode2[:,5] = user_y2
    mode2[:,6] = exp_x
    mode2[:,7] = exp_y

    # concatenate data
    data = np.concatenate((mode1, mode2), axis=0)

    while True:
        nRows, nCols = data.shape
        for iRow in range(0,nRows):
            # res = select.select([sock], [], [], 0)
            # if (len(res) !=0):
            #     cli_msg, client_address = sock.recvfrom(4096, socket.MSG_DONTWAIT)
            sock.sendto(data[iRow,:].tobytes(), client_address)
            time.sleep(0.001) # sleep for 1ms

if __name__ == "__main__":
    main(sys.argv[1:])
