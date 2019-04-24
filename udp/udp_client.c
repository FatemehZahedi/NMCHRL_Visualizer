// Client side implementation of UDP client-server model
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
	printf("Address: %s\n", addr);
	printf("Port: %d\n", port);

	int sockfd;
	char buffer[MAXLINE];
	char *hello = "Hello from client";
	struct sockaddr_in	 servaddr;

	// Creating socket file descriptor
	if ( (sockfd = socket(AF_INET, SOCK_DGRAM, 0)) < 0 ) {
		perror("socket creation failed");
		exit(EXIT_FAILURE);
	}

	memset(&servaddr, 0, sizeof(servaddr));

	// Filling server information
	servaddr.sin_family = AF_INET;
	servaddr.sin_port = htons(port);
	// servaddr.sin_addr.s_addr = inet_addr(addr);
	inet_pton(AF_INET, addr, &servaddr.sin_addr);

	int n, len;

	sendto(sockfd, (const char *)hello, strlen(hello),
		MSG_CONFIRM, (const struct sockaddr *) &servaddr,
			sizeof(servaddr));
	printf("Hello message sent.\n");

	n = recvfrom(sockfd, (char *)buffer, MAXLINE,
				MSG_WAITALL, (struct sockaddr *) &servaddr,
				&len);
	buffer[n] = '\0';
	printf("Server : %s\n", buffer);

	close(sockfd);
	return 0;
}
