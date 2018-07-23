#!/usr/bin/env python
from datetime import datetime
from netmiko import ConnectHandler
from concurrent.futures import ThreadPoolExecutor, as_completed
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
    
    return(output_dict)
    remote_conn.disconnect()

def main():
    net_devices = NetworkDevice.objects.all()
    start_time = datetime.now()
    
    with ThreadPoolExecutor(max_workers=4) as executor:
        
        #future_sh_ver = {}
        #for a_device in net_devices:
        #   future_sh_ver[executor.submit(show_version, a_device)] = a_device
        
        # start threads
        future_sh_ver = {executor.submit(show_version, a_device):
            a_device for a_device in net_devices}
        
        # wait for thread termination
        for future in as_completed(future_sh_ver):
            a_device = future_sh_ver[future]
            try:
                data = future.result()
            except Exception as exc:
                print('%r generated an exception: %s' % (a_device, exc))
            else:
                for k, val in data.items():
                    print(k)
                    print(val)
    
    elapsed_time = datetime.now() - start_time
    print("Elapsed time: {}".format(elapsed_time))

if __name__ == "__main__":
    main()