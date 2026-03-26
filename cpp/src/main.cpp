#include <iostream>
#include <thread>
#include <chrono>
#include <csignal>
#include "cuda_workload.h"
#include <iostream>
#include <thread>
#include <chrono>
#include <csignal>
#include <atomic>
#include "cuda_workload.h"

// Forward declaration of socketThread from socket_server.cpp
void socketThread(int port);

// Global flag — shared with socket_server.cpp via extern
extern std::atomic<bool> running;

void signalHandler(int signal) {
    std::cout << "\n[GPU Monitor] Shutting down..." << std::endl;
    running = false;
}

int main() {
    std::signal(SIGINT, signalHandler);

    std::cout << "[GPU Monitor] Starting on port 8080..." << std::endl;

    // Launch socket thread
    std::thread sockThread(socketThread, 8080);

    std::cout << "[GPU Monitor] Launching CUDA workload..." << std::endl;

    // Main loop — keep hammering the GPU until Ctrl+C
    while (running) {
        launchWorkload(1000);
    }

    // Clean shutdown
    sockThread.join();

    std::cout << "[GPU Monitor] Done." << std::endl;
    return 0;
}