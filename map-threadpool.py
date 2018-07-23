#!/usr/bin/env python
from datetime import datetime
from netmiko import ConnectHandler
from multiprocessing.dummy import Pool as ThreadPool
#from pprint import pprint
import django
django.setup()
from net_system.models import NetworkDevice, Credentials # noqa

def show_version(a_device):
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
    

def main():
    net_devices = NetworkDevice.objects.all()
    start_time = datetime.now()
    
    pool = ThreadPool(4)
    a_device_list = [a_device for a_device in net_devices]
    results = pool.map(show_version, a_device_list)
    #pprint(results)
    
    for result in results:
        for k, val in result.items():
            print(k)
            print(val)
    
    elapsed_time = datetime.now() - start_time
    print("Elapsed time: {}".format(elapsed_time))

if __name__ == "__main__":
    main()
