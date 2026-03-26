#include <cuda_runtime.h>
#include <cuda_fp16.h>
#include <stdio.h>

#define CUDA_CHECK(call) \
    do { \
        cudaError_t err = call; \
        if (err != cudaSuccess) { \
            printf("CUDA error at %s:%d - %s\n", __FILE__, __LINE__, cudaGetErrorString(err)); \
        } \
    } while(0)

__global__ void stressKernel(float* data, int size, int iterations) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= size) return;
    float val = data[idx];
    for (int i = 0; i < iterations; i++) {
        val = val * val + 0.1f;
    }
    data[idx] = val;
}

extern "C" void launchWorkload(int iterations) {
    const int size = 1 << 20;
    float* d_data = nullptr;
    CUDA_CHECK(cudaMalloc(&d_data, size * sizeof(float)));
    CUDA_CHECK(cudaMemset(d_data, 0, size * sizeof(float)));
    int blockSize = 256;
    int gridSize = (size + blockSize - 1) / blockSize;
    stressKernel<<<gridSize, blockSize>>>(d_data, size, iterations);
    CUDA_CHECK(cudaDeviceSynchronize());
    CUDA_CHECK(cudaFree(d_data));
}