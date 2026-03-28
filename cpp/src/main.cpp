#include <iostream>
#include <thread>
#include <chrono>
#include <csignal>
#include <atomic>
#include "cuda_workload.h"

void socketThread(int port);

extern std::atomic<bool> running;

void signalHandler(int signal) {
    std::cout << "\n[GPU Monitor] Shutting down..." << std::endl;
    running = false;
}

int main() {
    std::signal(SIGINT, signalHandler);

    std::cout << "[GPU Monitor] Starting on port 8080..." << std::endl;

    std::thread sockThread(socketThread, 8080);

    std::cout << "[GPU Monitor] Launching CUDA workload..." << std::endl;

    while (running) {
        launchWorkload(1000);
    }

    sockThread.join();

    std::cout << "[GPU Monitor] Done." << std::endl;
    return 0;
}