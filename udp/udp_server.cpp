// Server side implementation of UDP client-server model
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <arpa/inet.h>
#include <netinet/in.h>

#define PORT	 8080
#define MAXLINE 1024


class UDPServer{
private:
	std::string _addr;
	int _port = 8080;
	struct addrinfo _servaddr;
	struct addrinfo * _pservaddr;
	int _sockfd;
	const int _maxlen = 1024;

public:
	UDPServer(int port);

};

UDPServer::UDPServer(std::string addr, int port): _port(port), _addr(addr){
	// Reset and fill server address structs
	memset(&_servaddr, 0, sizeof(_servaddr));
	_servaddr.ai_family = AF_UNSPEC;
	_servaddr.ai_socktype = SOCK_DGRAM;
	_servaddr.ai_protocol = IPPROTO_UDP;
	int res = getaddrinfo(addr.c_str(), port, &_servaddr, )

	// Initialize socket
	sockfd = socket(AF_INET, SOCK_DGRAM, 0);
	if (sockfd < 0){
		perror("socket creation failed");
		exit(EXIT_FAILURE);
	}

	// Bind the socket with the server address
	if ( bind(sockfd, (const struct sockaddr *)&servaddr,
	sizeof(servaddr)) < 0 )
	{
		perror("bind failed");
		exit(EXIT_FAILURE);
	}
}

// Driver code
int main() {
	char buffer[MAXLINE];
	char *hello = "Hello from server";


	int n;
	socklen_t len;

	// printf("Before recvfrom client sockaddr_in\n");
	// printf("sin_family: %i\n", cliaddr.sin_family);
	// printf("sin_port: %i\n", cliaddr.sin_port);
	// printf("sin_addr.s_addr: %i\n", cliaddr.sin_addr.s_addr);
	// printf("sin_zero: %s\n", cliaddr.sin_zero);
	n = recvfrom(sockfd, (char *)buffer, MAXLINE,
				MSG_WAITALL, ( struct sockaddr *) &cliaddr,
				&len);
	buffer[n] = '\0';

	// printf("After recvfrom client sockaddr_in\n");
	// printf("sin_family: %i\n", cliaddr.sin_family);
	// printf("sin_port: %i\n", cliaddr.sin_port);
	// printf("sin_addr.s_addr: %i\n", cliaddr.sin_addr.s_addr);
	// printf("sin_zero: %s\n", cliaddr.sin_zero);


	printf("Client : %s\n", buffer);
	sendto(sockfd, (const char *)hello, strlen(hello),
		MSG_CONFIRM, (const struct sockaddr *) &cliaddr,
			len);
	printf("Hello message sent.\n");

	return 0;
}
