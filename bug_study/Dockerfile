# Base image with CUDA 13.0 and cuDNN for Ubuntu 24.04
FROM nvidia/cuda:13.0.0-cudnn-devel-ubuntu24.04

# Set non-interactive frontend to avoid apt prompts
ENV DEBIAN_FRONTEND=noninteractive

# Update apt and install dependencies
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    cmake \
    curl \
    libcurl4-openssl-dev \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Clone the repository
RUN git clone https://github.com/ggml-org/llama.cpp/ /app/llama.cpp

# Set working directory
WORKDIR /app/llama.cpp

# --- FIX FOR LINKER ERROR (BUILD TIME ONLY) ---
# 1. Symlink libcuda.so to libcuda.so.1 inside the stubs directory
# 2. Add the stubs directory to LD_LIBRARY_PATH so the linker finds it during build
RUN ln -s /usr/local/cuda/lib64/stubs/libcuda.so /usr/local/cuda/lib64/stubs/libcuda.so.1
ENV LD_LIBRARY_PATH=/usr/local/cuda/lib64/stubs:${LD_LIBRARY_PATH}

# Configure the build with CUDA support
RUN cmake -B build -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=90

# Build the project
RUN cmake --build build --config Release -j $(nproc)

# --- REMOVE STUBS FROM RUNTIME LD_LIBRARY_PATH ---
# The stubs are only needed for building, not runtime
# At runtime, the real NVIDIA drivers will be injected by the container runtime
ENV LD_LIBRARY_PATH=/usr/local/cuda/lib64:/usr/local/cuda/extras/CUPTI/lib64

# Expose the default server port
EXPOSE 8080

# Create a directory to mount the volume
RUN mkdir /models

# Set the entrypoint to the server binary
ENTRYPOINT ["./build/bin/llama-server"]

# Default command:
# Overridden by just launch_server recipe in bugs.just
CMD ["--help"]