#!/usr/bin/env python
"""
Proof of Concept Netflow v9 collector for WLC <= 8.1

Needs work.

Modified from the code on http://codestacking.blogspot.com/2017/02/netflow-version-9-collector-in-python.html

"""

import struct, socket
from socket import inet_ntoa
from pprint import pprint
import binascii

templates=[]

option_field = {
    '1': {
        'name': 'SYSTEM',
        'data_type': 'ipv4'        
    },
    '95': {
        'name': 'APPLICATION_ID',
        'data_type': 'hex'
    },
    '96': {
        'name': 'APPLICATION_NAME',
        'data_type': 'str'
    }
}
template_field = {
    '365': {
        'name': 'staMacAddress',
        'data_type': 'mac'
    },
    '366': {
        'name': 'staIPv4Address',
        'data_type': 'ipv4'
    },
    '95': {
        'name': 'APPLICATION_ID',
        'data_type': 'hex'
    },
    '147': {
        'name': 'wlanSSID',
        'data_type': 'str'
    },
    '61': {
        'name': 'DIRECTION',
        'data_type': 'int'
    },
    '1': {
        'name': 'BYTES',
        'data_type': 'int'
    },
    '2': {
        'name': 'PKTS',
        'data_type': 'int'
    },
    '98': {
        'name': 'postIpDiffServCodePoint',
        'data_type': 'int'
    },
    '195': {
        'name': 'IP_DSCP',
        'data_type': 'int'
    },
    '367': {
        'name': 'wtpMacAddress',
        'data_type': 'mac'
    }
}

def parse(data, field_type, field_length):
    if field_type == 'mac':
        rdata = str(binascii.hexlify(data), 'utf-8')
        return rdata
    if field_type == 'str':
        rdata = str(data, 'utf-8').rstrip('\x00')
        return rdata
    if field_type == 'hex':
        rdata = str(binascii.hexlify(data), 'utf-8')
        return rdata
    if field_type == 'ipv4':
        rdata = socket.inet_ntoa(data)
        return rdata
    if field_type == 'int':
        rdata = int(str(binascii.hexlify(data), 'utf-8'), 16)
        return rdata
    return '1234'

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(('10.0.69.30', 30001))
while True:
    buf, addr = sock.recvfrom(1500)
    (version, count) = struct.unpack('!HH',buf[0:4])
    if version != 9:
        print("Not NetFlow v9!")
        continue
    (sys_uptime, unix_secs, flow_sequence, source_id) = struct.unpack('!IIII', buf[4:20])
    print(  
        "Headers: ",
        "\nNetFlow Version: " + str(version), 
        "\nFlow Count: " + str(count), 
        "\nSystem Uptime: " + str(sys_uptime), 
        "\nEpoch Time in seconds: " + str(unix_secs), 
        "\nSequence counter of total flow: " + str(flow_sequence), 
        "\nSourceID: " + str(source_id)
        )
    data = buf[20:]
    while len(data) > 0:
        print('-'*40)
        (flowset_id, flowset_length) = struct.unpack('!HH', data[0:4])
        print( 
            "FlowSet ID: " + str(flowset_id),
            "\nFlowSet Length: " + str(flowset_length)
        )
        flowset_data = data[4:flowset_length]
        data = data[flowset_length:]
        if flowset_id == 0:
            # data template found.
            template={}
            (template_id, template_field_length) = struct.unpack('!HH',flowset_data[0:4])
            flowset_data=flowset_data[4:]
            template['id']= template_id
            template['description']=[]
            template['data_length']=0
            template['address']=addr[0]
            for i in range(0,template_field_length*4,4):
                template_element={}
                template_element['field_type'] = struct.unpack('!H', flowset_data[i:i+2])[0]
                template_field_length = struct.unpack('!H', flowset_data[i+2:i+4])[0]
                template_element['field_length']=template_field_length
                template['data_length'] += template_field_length
                template['description'].append(template_element)
            for temp in templates:
                if temp["id"]== template_id:
                    #update dict
                    templates.remove(temp)
                    break
            templates.append(template)
            pprint(template)

        if flowset_id == 1: 
            # options template found.
            template={}
            (template_id, option_scope_length) = struct.unpack('!HH',flowset_data[0:4])
            option_length = struct.unpack('!H',flowset_data[4:6])[0]
            flowset_data=flowset_data[6:]
            template['id']= template_id
            template['description']=[]
            template['data_length']=0
            template['address']=addr[0]
            for i in range(0, option_length+1, 4):
                template_element={}
                template_element['field_type'] = struct.unpack('!H', flowset_data[i:i+2])[0]
                template_field_length = struct.unpack('!H', flowset_data[i+2:i+4])[0]
                template_element['field_length'] = template_field_length
                template['data_length'] += template_field_length
                template['description'].append(template_element)
            for temp in templates:
                if temp["id"]== template_id:
                    #update dict
                    templates.remove(temp)
                    break
            templates.append(template)
            pprint(template)
            #Anything remaining is likely padding?
            #flowset_data=flowset_data[option_length:]

        if flowset_id == 261:
            # parse flow data
            # first check if template present
            my_template = None
            for template in templates:
                if flowset_id == template["id"] and addr[0] == template['address']: #check if template from same ip exist
                    my_template = template
                    break
            if not my_template:
                print("No suitable template found")
            else:
                nf_data=[]
                template_total_data_length = my_template['data_length']
                while len(flowset_data) >= template_total_data_length:
                    for field in my_template['description']:
                        field_name = template_field[str(field['field_type'])]['name']
                        field_type = template_field[str(field['field_type'])]['data_type']
                        field_length = field['field_length']
                        ext_data = parse(flowset_data[:field_length],field_type,field_length)
                        nf_data.append({field_name:ext_data})
                        flowset_data = flowset_data[field_length:]
                pprint(nf_data)

        if flowset_id == 256:
            # parse flow data
            # first check if template present
            my_template = None
            for template in templates:
                if flowset_id == template["id"] and addr[0] == template['address']: #check if template from same ip exist
                    my_template = template
                    break
            if not my_template:
                print("No suitable template found")
            else:
                nf_data=[]
                template_total_data_length = my_template['data_length']
                while len(flowset_data) >= template_total_data_length:
                    for field in my_template['description']:
                        field_name = option_field[str(field['field_type'])]['name']
                        field_type = option_field[str(field['field_type'])]['data_type']
                        field_length = field['field_length']
                        ext_data = parse(flowset_data[:field_length],field_type,field_length)
                        nf_data.append({field_name:ext_data})
                        flowset_data = flowset_data[field_length:]
                pprint(nf_data)

    print('='*40)
