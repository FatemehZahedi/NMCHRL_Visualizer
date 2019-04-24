

class UDPServer{
private:
    // UDP/IP socket info
	std::string _addr;
	int _port;
    int _sockfd;

    // Server/Client address info
	struct sockaddr_in _servaddr;
	struct sockaddr_in _cliaddr;
	socklen_t _cliaddrlen;

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
    void ReconnectIfNecessary();
	template<typename T>
	void Send(T* data, int ndata);
};
