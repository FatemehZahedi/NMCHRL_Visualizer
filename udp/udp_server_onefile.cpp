// Server side implementation of UDP client-server model
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>
#include <sys/select.h>
#include <sys/time.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <netdb.h>
#include <arpa/inet.h>
#include <netinet/in.h>
#include <string>
#include <iostream>
#include <fstream>
#include <vector>


#define _USE_MATH_DEFINES
#include <cmath>

using std::vector;

vector<double> linspace(double start, double stop, int n) {
    vector<double> array;
    double step = (stop-start)/(n-1);

    while(start <= stop) {
        array.push_back(start);
        start += step;           // could recode to better handle rounding errors
    }
    return array;
}


class UDPServer{
private:
	std::string _addr;
	int _port;
	struct sockaddr_in _servaddr;
	struct sockaddr_in _cliaddr;
	socklen_t _cliaddrlen;
	int _sockfd;
    fd_set _readset;
	const int _maxlen = 1024;
	bool _connected = false;
    struct timeval _select_timeout = {.tv_sec = 0, .tv_usec = 0};

public:
	UDPServer(std::string addr, int port);
	std::string GetAddress();
	int GetPort();
	bool IsConnected() const;
	void ConnectClient();
    void ReconnectIfNecessary();
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
	_servaddr.sin_addr.s_addr = inet_addr(addr.c_str());
	_servaddr.sin_port = htons(port);

	// Bind the socket with the server address
	if (bind(_sockfd, (const struct sockaddr *)&_servaddr,sizeof(_servaddr)) < 0)
	{
		perror("bind failed");
		exit(EXIT_FAILURE);
	}
}

void UDPServer::ReconnectIfNecessary(){
    FD_ZERO(&_readset);
    FD_SET(_sockfd, &_readset);
    int ret = select(_sockfd+1, &_readset, NULL, NULL, &_select_timeout);
    if (ret > 0){
        ConnectClient();
    }
}

std::string UDPServer::GetAddress(){
	return _addr;
}

int UDPServer::GetPort(){
	return _port;
}

bool UDPServer::IsConnected() const{
	return _connected;
}

void UDPServer::ConnectClient(){
	char buffer[_maxlen];
	int n;
	n = recvfrom(_sockfd, (char *)buffer, _maxlen,
							 MSG_WAITALL, ( struct sockaddr *) &_cliaddr, &_cliaddrlen);
	buffer[n] = '\0';
	_connected = true;
	printf("Client: %s\n", buffer);
	printf("Client Connected\n");
}

template<typename T>
void UDPServer::Send(T* data, int ndata){
	if (_connected){
		sendto(_sockfd, (const T *) data, sizeof(data)*ndata,
  				 MSG_DONTWAIT, (const struct sockaddr *) &_cliaddr, _cliaddrlen);
	}
}


// Driver code
int main() {

	std::string addr;
	int port;

	std::cout << "Enter IP Address" << std::endl;
	std::cin >> addr;

	std::cout << "Enter Port" << std::endl;
	std::cin >> port;

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
	server.ConnectClient();

	// Send Data
	double data[2];
	int i = 0;
	while (1){
		data[0] = x[i];
		data[1] = y[i];
        server.ReconnectIfNecessary();
		server.Send(data, 2);
		i = (i+1)%((int) n);
		usleep(1000);
	}

	return 0;
}
