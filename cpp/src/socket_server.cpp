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
std::mutex  metricsMutex;
std::atomic<bool> running(true);

void socketThread(int port) {
    int server_fd = socket(AF_INET, SOCK_STREAM, 0);
    if (server_fd < 0) {
        std::cerr << "[GPU Monitor] Failed to create socket: " << strerror(errno) << std::endl;
        return;
    }

    int opt = 1;
    setsockopt(server_fd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));

    sockaddr_in address = {};
    address.sin_family      = AF_INET;
    address.sin_addr.s_addr = INADDR_ANY;
    address.sin_port        = htons(port);

    if (bind(server_fd, (sockaddr*)&address, sizeof(address)) < 0) {
        std::cerr << "[GPU Monitor] Failed to bind socket: " << strerror(errno) << std::endl;
        close(server_fd);
        return;
    }

    if (listen(server_fd, 1) < 0) {
        std::cerr << "[GPU Monitor] Failed to listen on socket: " << strerror(errno) << std::endl;
        close(server_fd);
        return;
    }

    std::cout << "[GPU Monitor] Socket server listening on port " << port << std::endl;

    while (running) {
        sockaddr_in client_addr = {};
        socklen_t   client_len  = sizeof(client_addr);

        int client_fd = accept(server_fd, (sockaddr*)&client_addr, &client_len);
        if (client_fd < 0) {
            if (!running) break;
            std::cerr << "[GPU Monitor] accept() failed: " << strerror(errno) << std::endl;
            continue;
        }

        std::cout << "[GPU Monitor] Python client connected." << std::endl;

        while (running) {
            GPUMetrics m;
            {
                std::lock_guard<std::mutex> lock(metricsMutex);
                m = currentMetrics;
            }

            std::ostringstream json;
            json << "{"
                 << "\"gpu_util\":"      << m.gpu_util      << ","
                 << "\"vram_used_mb\":"  << m.vram_used_mb  << ","
                 << "\"vram_total_mb\":" << m.vram_total_mb << ","
                 << "\"temperature\":"   << m.temperature   << ","
                 << "\"power_w\":"       << m.power_w       << ","
                 << "\"power_limit_w\":" << m.power_limit_w
                 << "}\n";

            std::string msg = json.str();
            ssize_t sent = send(client_fd, msg.c_str(), msg.size(), 0);
            if (sent <= 0) {
                std::cout << "[GPU Monitor] Python client disconnected." << std::endl;
                break;
            }

            std::this_thread::sleep_for(std::chrono::milliseconds(1000));
        }

        close(client_fd);
    }

    close(server_fd);
    std::cout << "[GPU Monitor] Socket server stopped." << std::endl;
}