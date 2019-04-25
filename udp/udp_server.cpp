
// Server side implementation of UDP client-server model
#include <arpa/inet.h>
#include <netdb.h>
#include <netinet/in.h>
#include <string>
#include <string.h>
#include <sys/select.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <sys/types.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <vector>

using std::vector;

#define _USE_MATH_DEFINES
#include <cmath>

class UDPServer{
private:
    // UDP/IP socket info
	std::string _addr;
	int _port;
    int _sockfd;

    // Server/Client address info
	struct sockaddr_in _servaddr;
	struct sockaddr_in _cliaddr;
	socklen_t _cliaddrlen = sizeof(_cliaddr);

    // Recv/send limit
    const int _maxlen = 1024;

    // Connection State
    bool _connected = false;

    // select(2) related data
    fd_set _readset;
    struct timeval _select_timeout = {.tv_sec = 0, .tv_usec = 0};

public:
    // Class Methods
	UDPServer(std::string addr, int port);
	std::string GetAddress();
	int GetPort();
	bool IsConnected() const;
	void ConnectClient();
    void ConnectIfNecessary();
	template<typename T>
	void Send(T* data, int ndata);
};

UDPServer::UDPServer(std::string addr, int port): _port(port), _addr(addr){

	// Initialize socket
	_sockfd = socket(AF_INET, SOCK_DGRAM, 0);
	if (_sockfd < 0){
		perror("socket creation failed");
		exit(EXIT_FAILURE);
	}

	// Reset and fill server address structs
	memset(&_servaddr, 0, sizeof(_servaddr));
	memset(&_cliaddr, 0, sizeof(_cliaddr));

	_servaddr.sin_family = AF_INET;
	_servaddr.sin_addr.s_addr = INADDR_ANY;
	_servaddr.sin_port = htons(port);

	// Bind the socket with the server address
	if (bind(_sockfd, (const struct sockaddr *)&_servaddr,sizeof(_servaddr)) < 0)
	{
		perror("bind failed");
		exit(EXIT_FAILURE);
	}
}

void UDPServer::ConnectIfNecessary(){
    /*
    select(2) system call monitors if there is an incoming messge from the client
    If there is, select(2) will return a number greater than 0.  We will then connect
    run ConnectClient() which reads in the message and gets the client's ip info
    so the server can send messages to it
    */
    FD_ZERO(&_readset);
    FD_SET(_sockfd, &_readset);
    int ret = select(_sockfd+1, &_readset, NULL, NULL, &_select_timeout);
    if (ret > 0){
        ConnectClient();
    }
}

std::string UDPServer::GetAddress(){
    // return server's ip address
	return _addr;
}

int UDPServer::GetPort(){
    // return server's port
	return _port;
}

bool UDPServer::IsConnected() const{
    // return server-client connection status
    return _connected;
}

void UDPServer::ConnectClient(){
    /*
    recvfrom() system call reads the message into the buffer and fills the _cliaddr
    struct with the client's ip info.  The message in the buffer is not important.
    We only do this so we get the client's ip address info
    */
	char buffer[_maxlen];
	int n;
	n = recvfrom(_sockfd, (char *)buffer, _maxlen,
				MSG_WAITALL, ( struct sockaddr *) &_cliaddr, &_cliaddrlen);
	_connected = true;
}

template<typename T>
void UDPServer::Send(T* data, int ndata){
    // Connect/Reconnect to client if necessary (get's clients ip address info)
    ConnectIfNecessary();
    // Send data if the server is connected to a client
	if (_connected){
		sendto(_sockfd, (const T *) data, sizeof(data)*ndata,
  				 MSG_DONTWAIT, (const struct sockaddr *) &_cliaddr, _cliaddrlen);
	}
}






vector<double> linspace(double start, double stop, int n) {
    vector<double> array;
    double step = (stop-start)/(n-1);

    while(start <= stop) {
        array.push_back(start);
        start += step;           // could recode to better handle rounding errors
    }
    return array;
}

int main(int argc, char * argv[]) {
    if (argc != 3){
		// error if incorrect command line arguments were inputted
		printf("Command line arguments must be\n");
		printf("1. IP address (of server) - ex: 192.168.0.100\n");
		printf("2. port: - ex: 8080\n");
		printf("\n\n Full example:   ./executable 192.168.0.100 8080\n");
		exit(1);
	}

	// assign command line inputs to addr, port variables
    std::string addr(argv[1]);
	int port = atoi(argv[2]);
	printf("Address: %s\n", addr.c_str());
	printf("Port: %d\n", port);

	// Generate x,y lemniscate data
	double a = 2;
	double b = 2*sqrt(2);
	double t1 = 0;
	double t2 = 2*M_PI;
	double n = 3000;
	vector<double> t = linspace(t1, t2, n);
	vector<double> x = t;
	vector<double> y = t;
	for (int i=0; i<t.size(); i++){
		x[i] = a*cos(t[i])/(1+ pow(sin(t[i]), 2));
		y[i] = b*sin(t[i])*cos(t[i])/(1+ pow(sin(t[i]), 2));
	}

	// Create UDP Server and Connect to Client
	UDPServer server(addr, port);

	// Send Data
	double data[2];
	int i = 0;
	while (1){
		data[0] = x[i];
		data[1] = y[i];
		server.Send(data, 2);
		i = (i+1)%((int) n);
		usleep(1000);
	}

	return 0;
}
