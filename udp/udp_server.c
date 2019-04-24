// Server side implementation of UDP client-server model
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <arpa/inet.h>
#include <netinet/in.h>

#define MAXLINE 1024

// Driver code
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
	char * addr = argv[1];
	int port = atoi(argv[2]);

	int sockfd;
	char buffer[MAXLINE];
	char *hello = "Hello from server";
	struct sockaddr_in servaddr, cliaddr;

	// Creating socket file descriptor
	if ( (sockfd = socket(AF_INET, SOCK_DGRAM, 0)) < 0 ) {
		perror("socket creation failed");
		exit(EXIT_FAILURE);
	}

	memset(&servaddr, 0, sizeof(servaddr));
	memset(&cliaddr, 0, sizeof(cliaddr));

	// Filling server information
	servaddr.sin_family = AF_INET; // IPv4
	servaddr.sin_port = htons(port);
	// servaddr.sin_addr.s_addr = inet_addr(addr);
	inet_pton(AF_INET, addr, &servaddr.sin_addr);

	// Bind the socket with the server address
	if ( bind(sockfd, (const struct sockaddr *)&servaddr,
			sizeof(servaddr)) < 0 )
	{
		perror("bind failed");
		exit(EXIT_FAILURE);
	}

	int n;
	socklen_t len = sizeof(cliaddr);

	printf("Before recvfrom client sockaddr_in\n");
	printf("sin_family: %i\n", cliaddr.sin_family);
	printf("sin_port: %i\n", cliaddr.sin_port);
	printf("sin_addr.s_addr: %i\n", cliaddr.sin_addr.s_addr);
	printf("sin_zero: %s\n", cliaddr.sin_zero);
	n = recvfrom(sockfd, (char *)buffer, MAXLINE,
				MSG_WAITALL, ( struct sockaddr *) &cliaddr,
				&len);
	buffer[n] = '\0';
	printf("Received from client: %s\n", buffer);
	printf("After recvfrom client sockaddr_in\n");
	printf("sin_family: %i\n", cliaddr.sin_family);
	printf("sin_port: %i\n", cliaddr.sin_port);
	printf("sin_addr.s_addr: %i\n", cliaddr.sin_addr.s_addr);
	printf("sin_zero: %s\n", cliaddr.sin_zero);

	// // Filling server information
	// cliaddr.sin_family = AF_INET;
	// cliaddr.sin_port = htons(port);
	// cliaddr.sin_addr.s_addr = inet_addr(addr);

	printf("Client : %s\n", buffer);
	sendto(sockfd, (const char *)hello, strlen(hello),
		MSG_CONFIRM, (const struct sockaddr *) &cliaddr,
			len);
	printf("Hello message sent.\n");

	return 0;
}
