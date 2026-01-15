#include <cstdio>
#include <thread>

int main(int argc, char **argv)
{ 
    //printf("Hello from Morello!!\n");
    printf("sizeof(std::thread::id) = %lu\n", sizeof(std::thread::id));

	return 0;
}

