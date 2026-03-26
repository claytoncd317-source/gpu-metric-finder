#include <iostream>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>
#include <string>
#include <thread>
#include <mutex>
#include <chrono>
#include <sstream>
#include <atomic>
#include <cstring>

struct GPUMetrics {
    float gpu_util;
    float vram_used_mb;
    float vram_total_mb;
    float temperature;
    float power_w;
    float power_limit_w;
};

GPUMetrics currentMetrics = {};
std::mutex metricsMutex;
std::atomic<bool> running(true);

void socketThread(int port) {
    int server_fd = socket(AF_INET, SOCK_STREAM, 0);
    if (server_fd < 0) {
        std::cerr << "Failed to create socket" << std::endl;
        close(server_fd);
        return;
    }

    int opt = 1;
    setsockopt(server_fd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));

    sockaddr_in address = {};
    address.sin_family = AF_INET;
    address.sin_addr.s_addr = INADDR_ANY;
    address.sin_port = htons(port);


    if (bind(server_fd, (sockaddr*)&address, sizeof(address))<0) {
        std::cerr << "Failed to bind socket" << strerror(errno) << std:: endl;
        close(server_fd);
        return;
    }

    if (listen(server_fd, 1) < 0) {
        std::cerr <<"Failed to listen on socket: " << strerror(errno) << std:: endl;
        close(server_fd);
        return;
    }

}