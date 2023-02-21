import re
import os
import glob
import json
import time
import requests
import threading

import fcntl
import socket
import struct

from math import sqrt
from random import seed, randint
from datetime import datetime

#####  our functions  ####
import lib.common as com
#########################


global first_time_set
global last_time_set
global header
global server_url
global sd_keys
global nfps
global people_counting_enabled
global aforo_enabled
global social_distance_enabled
global social_distance_url
global people_counting_url
global plate_detection_url

header = None

first_time_set = set()
last_time_set = set()


##### GENERIC FUNCTIONS


def log_error(msg, _quit = True):
    print("-- PARAMETER ERROR --\n"*5)
    print(" %s \n" % msg)
    print("-- PARAMETER ERROR --\n"*5)
    if _quit:
        quit()
    else:
        return False


def api_get_number_of_frames_per_second():
    '''
    TODO: function not yet defined
    '''
    return None


def file_exists(file_name):
    try:
        with open(file_name) as f:
            return file_name
    except OSError as e:
        return False


def open_file(file_name, option='a+'):
    if file_exists(file_name):
        return open(file_name, option)
    return False


def create_file(file_name, content = None):

    if file_exists(file_name):
        os.remove(file_name)
        if file_exists(file_name):
            raise Exception('unable to delete file: %s' % file_name)

    if content:
        with open(file_name, 'w+') as f:
            f.write(content)
    else:
        with open(file_name, 'w+') as f:
            f.close()

    return True


def get_number_of_frames_per_second():
    global nfps

    nfps = api_get_number_of_frames_per_second()

    if nfps is None:
        return 16

    return nfps


def get_supported_actions():
    return ('GET', 'POST', 'PUT', 'DELETE')


def getHwAddr(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    info = fcntl.ioctl(s.fileno(), 0x8927,  struct.pack('256s', bytes(ifname, 'utf-8')[:15]))
    return ':'.join('%02x' % b for b in info[18:24])


def get_ip_address(ifname):
    return [l for l in ([ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if not ip.startswith("127.")][:1], [[(s.connect(("8.8.8.8", 53)), s.getsockname()[0], s.close()) for s in [socket.socket(socket.AF_INET, socket.SOCK_DGRAM)]][0][1]]) if l][0][0]


def get_machine_macaddresses():
    list_of_interfaces = [item for item in os.listdir('/sys/class/net/') if item != 'lo']
    macaddress_list = []

    for iface_name in list_of_interfaces:
        ip = get_ip_address(iface_name)
        if ip:
            macaddress_list.append(getHwAddr(iface_name))
            return macaddress_list


def get_server_info_from_local_file(filename, _quit = True):
    if file_exists(filename):
        with open(filename) as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
            return log_error("data unknow error, data is not a dictionary: {}")
    else:
        return log_error("Unable to read the device configuration from local file: {}".format(filename), _quit)


def parse_parameters_and_values_from_config(config_data):
    # filter config and get only data for this server using the mac to match
    config_data = get_config_filtered_by_local_mac(config_data)

    # filter config and get only data of active services
    return get_config_filtered_by_active_service(config_data)


def get_config_filtered_by_local_mac(config_data):
    '''
    By now we only support one nano server and one interface
    but it can be a big server with multiple interfaces so I
    leave the logic with to handle this option
    '''
    services_data = {}
    for key in config_data.keys():
        if mac_address_in_config(key):
            services_data[key] = config_data[key]
    if services_data:
        return services_data

    log_error("The provided configuration does not match any of server interfaces mac address")


def get_config_filtered_by_active_service(config_data):
    if not isinstance(config_data, dict):
        log_error("Configuration error - Config data must be a dictionary - type: {} / content: {}".format(type(config_data), config_data))
    active_services = {}

    # at this point there should be only one server mac but we still loop in case we have many multiple network interfaces 
    for server_mac in config_data.keys():
        #  we loop over all the different cameras attach to this server
        for camera_mac in config_data[server_mac]:
            # we loop over all the services assigned to the camera
            for service in config_data[server_mac][camera_mac]:
                # if the service is enable we add it to the active services
                if 'enabled' in config_data[server_mac][camera_mac][service] and config_data[server_mac][camera_mac][service]['enabled'] is True:
                    if 'source' not in config_data[server_mac][camera_mac][service]:
                        log_error("Service {} must have a source (video or live streaming)".format(service))

                    # Create new key only for each of the active services
                    new_key_name = 'srv_' + server_mac + "_camera_" + camera_mac + '_' + service
                    active_services[new_key_name] = {service: config_data[server_mac][camera_mac][service]}

    if len(active_services) < 1:
        com.log_error("\nConfiguration does not contain any active service for this server: \n\n{}".format(config_data))

    return active_services


def mac_address_in_config(mac_config):
    for machine_id in com.get_machine_macaddresses():
        if mac_config == machine_id:
            return True
    return False


def send_json(payload, action, url = None, **options):
    set_header()
    global header

    if action not in get_supported_actions() or url is None:
        raise Exception('Requested action: ({}) not supported. valid options are:'.format(action, get_supported_actions()))

    retries = options.get('retries', 2)
    sleep_time = options.get('sleep_time', 1)
    expected_response = options.get('expected_response', 200)
    abort_if_exception = options.get('abort_if_exception', True)

    data = json.dumps(payload)

    # emilio comenta esto para insertar en MongoDB
    # return True

    for retry in range(retries):
        try:
            if action == 'GET':
                r = requests.get(url, data=data, headers=header)
            elif action == 'POST':
                r = requests.post(url, data=data, headers=header)
            elif action == 'PUT':
                r = requests.put(url, data=data, headers=header)
            else:
                r = requests.delete(url, data=data, headers=header)
            return r
        except requests.exceptions.ConnectionError as e:
            time.sleep(sleep_time)
            if retry == retries - 1 and abort_if_exception:
                raise Exception("Unable to Connect to the server after {} retries\n. Original exception: {}".format(retry, str(e)))
        except requests.exceptions.HTTPError as e:
            time.sleep(sleep_time)
            if retry == retries - 1 and abort_if_exception:
                raise Exception("Invalid HTTP response in {} retries\n. Original exception: {}".format(retry, str(e)))
        except requests.exceptions.Timeout as e:
            time.sleep(sleep_time)
            if retry == retries - 1 and abort_if_exception:
                raise Exception("Timeout reach in {} retries\n. Original exception: {}".format(retry, str(e)))
        except requests.exceptions.TooManyRedirects as e:
            time.sleep(sleep_time)
            if retry == retries - 1 and abort_if_exception:
                raise Exception("Too many redirection in {} retries\n. Original exception: {}".format(retry, str(e)))


def is_point_insde_polygon(x, y, polygon_length, polygon):

    p1x,p1y = polygon[0]
    for i in range(polygon_length+1):
        p2x,p2y = polygon[i % polygon_length]
        if y > min(p1y,p2y):
            if y <= max(p1y,p2y):
                if x <= max(p1x,p2x):
                    if p1y != p2y:
                        xinters = (y-p1y)*(p2x-p1x)/(p2y-p1y)+p1x
                    if p1x == p2x or x <= xinters:
                        # returns True if x,y are inside
                        return True
        p1x,p1y = p2x,p2y

    # returns False if x,y are not inside
    return False


##### PEOPLE COUNTING

##### AFORO


#### MASK DETECTION

def set_mask_detection_url(server_url):
    global mask_detection_url
    mask_detection_url = server_url + 'tx/video-maskDetection.endpoint'


def mask_detection(mask_id, no_mask_ids, camera_id, reported_class = 0):
    time_in_epoc = com.get_timestamp()
    data_id = str(time_in_epoc) + '_' + str(mask_id)
    data = {
        'id': data_id,
        'mask': reported_class,
        'camera-id': camera_id,
        '#date-start': time_in_epoc,
        '#date-end': time_in_epoc
        }

    print('Mask detection', data, mask_detection_url, 'PUT')
    x = threading.Thread(target=send_json, args=(data, 'PUT', mask_detection_url,))
    x.start()


#### PLATE DETECTION

def set_plate_detection_url(server_url):
    global plate_detection_url
    plate_detection_url = server_url + 'TO_BE_SETUP______tx/video-plateDetection.endpoint'


