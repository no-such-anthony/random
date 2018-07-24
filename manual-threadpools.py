#!/usr/bin/env python
from datetime import datetime
from netmiko import ConnectHandler
import threading
import time
from queue import Queue
import django
django.setup()
from net_system.models import NetworkDevice, Credentials # noqa

def show_version(a_device, output_q):
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
    output_q.put(output_dict)
    remote_conn.disconnect()
    print("terminating thread")

def main():
    net_devices = NetworkDevice.objects.all()
    start_time = datetime.now()
    
    output_q = Queue(maxsize=20)
    
    max_threads = 4
    my_thread_list = []
    
    for a_device in net_devices:
        my_thread = threading.Thread(target=show_version, args=(a_device, output_q))
        my_thread.start()
        my_thread_list.append(my_thread)
        
        if len(my_thread_list) >= max_threads:
            print("pausing threading: max threads reached")
            while 1:
                time.sleep(1)
                finished = set(my_thread_list) - set(threading.enumerate())
                [my_thread_list.remove(thread_obj) for thread_obj in finished] 
                if len(my_thread_list) < max_threads:
                    print("continuing threading")
                    break
    
    # wait for remaining threads
    for some_thread in my_thread_list:
        some_thread.join()
    
    while not output_q.empty():
        my_dict = output_q.get()
        for k, val in my_dict.items():
            print(k)
            print(val)
    
    elapsed_time = datetime.now() - start_time
    print("Elapsed time: {}".format(elapsed_time))

if __name__ == "__main__":
    main()
