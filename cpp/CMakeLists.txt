cmake_minimum_required(VERSION 3.18)

project(gpu_monitor LANGUAGES CXX CUDA)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CUDA_STANDARD 17)

set(CMAKE_CUDA_ARCHITECTURES 89)

find_package(CUDAToolkit REQUIRED)

add_executable(gpu_monitor
    src/socket_server.cpp
    src/cuda_workload.cu
    src/main.cpp
)

target_include_directories(gpu_monitor PRIVATE
    include
    ${CUDAToolkit_INCLUDE_DIRS}
)

target_link_libraries(gpu_monitor PRIVATE
    CUDA::cudart
)

set_target_properties(gpu_monitor PROPERTIES
    CUDA_SEPARABLE_COMPILATION ON
)