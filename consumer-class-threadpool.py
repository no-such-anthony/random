#!/usr/bin/env python
from datetime import datetime
from netmiko import ConnectHandler
import threading
from queue import Queue
#from pprint import pprint
import django
django.setup()
from net_system.models import NetworkDevice, Credentials # noqa

#based on http://chriskiehl.com/article/parallelism-in-one-line/
#obviously not the map method found there

class Consumer(threading.Thread):
    def __init__(self, input_queue, output_queue):
        threading.Thread.__init__(self)
        self._input_q = input_queue
        self._output_q = output_queue
        
    def run(self):
        while True:
            a_device = self._input_q.get()
            if isinstance(a_device, str) and a_device == 'quit':
                break
            response = self.show_version(a_device)
            self._output_q.put(response)
        print('Bye byes!')


    def show_version(self, a_device):
        output_dict = {}
        creds = a_device.credentials
        remote_conn = ConnectHandler(device_type=a_device.device_type,
                                     ip=a_device.ip_address,
                                     username=creds.username,
                                     password=creds.password,
                                     port=a_device.port,
                                     secret='')
        output = ('#'*60) + "\n"
        output += remote_conn.send_command_expect("show version") + "\n"
        output += ('#'*60) + "\n"
        output_dict[a_device.device_name] = output
        remote_conn.disconnect()
        return(output_dict)
    
def build_worker_pool(input_queue, output_queue, size):
  workers = []
  for _ in range(size):
    worker = Consumer(input_queue, output_queue)
    worker.start() 
    workers.append(worker)
  return workers

def main():
    net_devices = NetworkDevice.objects.all()
    start_time = datetime.now()
    
    input_queue = Queue()
    output_queue = Queue()
    worker_threads = build_worker_pool(input_queue, output_queue, 4)

    # Add the devices to process
    for a_device in net_devices:
        input_queue.put(a_device)  
    # Add the poison pill
    for worker in worker_threads:
        input_queue.put('quit')
    for worker in worker_threads:
        worker.join()
        
    while not output_queue.empty():
        my_dict = output_queue.get()
        for k, val in my_dict.items():
            print(k)
            print(val)

    elapsed_time = datetime.now() - start_time
    print("Elapsed time: {}".format(elapsed_time))

if __name__ == "__main__":
    main()