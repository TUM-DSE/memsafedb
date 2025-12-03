#include <boost/lockfree/queue.hpp>
#include <iostream>
#include <vector>
#include <thread>
#include <cstdint>
#ifdef MTE
#include <mte.hpp>
#endif

#include <boost/atomic.hpp>
struct counter {
  boost::atomic_int cnt;
  char padding[64-sizeof(boost::atomic_int)];
};

counter* consumer_counts;
counter* producer_counts;

boost::lockfree::queue<uint64_t, boost::lockfree::fixed_sized<true>, boost::lockfree::capacity<65534>> queue;
uint64_t iterations = 0;

using namespace std;
using namespace std::chrono;

void producer(int id){
  for ( int i = 0; i != iterations; ++i ) {
    int value = ++(producer_counts[id].cnt);
    while ( !queue.push( value ) )
      ;
  }
}

boost::atomic<bool> done(false);
void consumer(int id){
  int value;
  while (!done) {
    while (queue.pop(value))
      ++(consumer_counts[id].cnt);
  }
  while (queue.pop(value))
    ++(consumer_counts[id].cnt);
}

int main(int argc, char* argv[])
{
#ifdef MTE
  init_process(MTE_MODE_SYNC);
#endif
  if(argc != 3){
    printf("queue_bench [nb_items] [nb_threads]\n");
  }
  iterations = stoul(argv[1]);
  int nb_threads = stoi(argv[2]);
  const int producer_thread_count = nb_threads;
  const int consumer_thread_count = nb_threads;
  iterations /= producer_thread_count;
  consumer_counts = (counter*)malloc(consumer_thread_count * sizeof(counter));
  memset(consumer_counts, 0, consumer_thread_count*sizeof(counter));
  producer_counts = (counter*)malloc(producer_thread_count * sizeof(counter));
  memset(producer_counts, 0, producer_thread_count*sizeof(counter));

  vector<thread> producer_threads;
  vector<thread> consumer_threads;

  for ( int i = 0; i != consumer_thread_count; ++i )
    consumer_threads.emplace_back([&, i]{ consumer(i); });
  
  high_resolution_clock::time_point t1 = high_resolution_clock::now();
  
  for ( int i = 0; i != producer_thread_count; ++i )
    producer_threads.emplace_back([&, i] { producer(i); });

  for (auto &t: producer_threads)
    t.join();
  done = true;
  for (auto &t: consumer_threads)
    t.join();
  high_resolution_clock::time_point t2 = high_resolution_clock::now();
  duration<double> time_span = duration_cast<duration<double>>(t2 - t1);
  cout << "Processing " << iterations*producer_thread_count << " items with " << producer_thread_count+consumer_thread_count << " threads took: " << time_span.count() << "\n";
}

