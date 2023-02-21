import os
import lib.common as com
import lib.aforo_values as aforo
import lib.server as srv


CURRENT_DIR = os.getcwd()

# Matriz de frames per second, Se utiliza en tiler
fps_streams = {}

# store global frame counting 
frame_count = {}
saved_count = {}

# stores the configuration within all its process from reading, filtering
# valiating values and add new parameters and format values. 
global scfg
scfg = {}

#Stores actions to execute per camera, each camera can execute multiple services
#the only condition is all are based on the same model
global action
action = {}

# stores header for the server communication exchange
global header
header = None

# stores the order of how the sources are executed and associates an id
# so that we can all it in the tiler function for the specific services
global call_order_of_keys
call_order_of_keys = []


def setup_services():
    global scfg, header, call_order_of_keys, action

    header = srv.set_header()
    scfg = srv.get_server_info(header)
    com.log_debug("Final configuration: \n{}".format(scfg))

    number_sources = 0
    for camera_mac in scfg:
        call_order_of_keys.append(camera_mac)
        number_sources += 1
        for service_id in scfg[camera_mac]:
            if service_id == "source" or service_id == "server_url":
                continue
            for item in scfg[camera_mac][service_id]:
                for service_id_inner in item:
                    for service_name in item[service_id_inner]:
                        if service_name in com.SERVICES:
                            action.update({service_id_inner: service_name})
                            set_action(service_id_inner, service_name, scfg)
    return number_sources


def get_header():
    global header
    return header


def setup_displayed_text(py_nvosd_text_params):
    py_nvosd_text_params.x_offset = 1200
    py_nvosd_text_params.y_offset = 100
    py_nvosd_text_params.font_params.font_name = "Arial"
    py_nvosd_text_params.font_params.font_size = 20
    py_nvosd_text_params.font_params.font_color.red = 1.0
    py_nvosd_text_params.font_params.font_color.green = 1.0
    py_nvosd_text_params.font_params.font_color.blue = 1.0
    py_nvosd_text_params.font_params.font_color.alpha = 1.0
    py_nvosd_text_params.set_bg_clr = 1
    py_nvosd_text_params.text_bg_clr.red = 0.0
    py_nvosd_text_params.text_bg_clr.green = 0.0
    py_nvosd_text_params.text_bg_clr.blue = 0.0
    py_nvosd_text_params.text_bg_clr.alpha = 1.0

    return py_nvosd_text_params


def get_camera_id(index):
    global call_order_of_keys
    return call_order_of_keys[index]


def get_dictionary_from_list(srv_id, scfg):
    camera_mac = srv_id.split('_')[1]
    for dict_element in scfg[camera_mac]['services']:
        if srv_id in dict_element:
            return dict_element[srv_id]


def set_action(srv_camera_id, service_name, scfg):
    '''
    Esta function transfiere la configuration de los parametros hacia los servicios activos por cada camara
    '''

    #if service_name in com.SERVICES:
    execute_actions = False
    com.log_debug('Set "{}" variables for service id: {}'.format(service_name, srv_camera_id))
    if service_name == 'find':
        if service_name == com.SERVICE_DEFINITION[com.SERVICES[service_name]]:
            com.log_error("Servicio de find no definido aun")
        else:
            com.log_error("Servicio '"+service_name+"' no definido")
    elif service_name == 'blackList':
        if service_name in com.SERVICE_DEFINITION[com.SERVICES[service_name]] and BLACKLIST_DB_NAME:
            config_blacklist(srv_camera_id)
            execute_actions = True
        else:
            com.log_error("Servicio '"+service_name+"' no definido")
    elif service_name == 'whiteList':
        if service_name in com.SERVICE_DEFINITION[com.SERVICES[service_name]] and WHITELIST_DB_NAME:
            config_whitelist(srv_camera_id)
            execute_actions = True
        else:
            com.log_error("Servicio '"+service_name+"' no definido")
    elif service_name == 'ageAndGender':
        if service_name in com.SERVICE_DEFINITION[com.SERVICES[service_name]]:
            config_age_and_gender(srv_camera_id)
            execute_actions = True
        else:
            com.log_error("Servicio '"+service_name+"' no definido")
    elif service_name == 'aforo':
        if service_name in com.SERVICE_DEFINITION[com.SERVICES[service_name]]:
            aforo.validate_aforo_values(scfg, service_name, get_dictionary_from_list(srv_camera_id, scfg)['aforo'])
            aforo.set_aforo(scfg, srv_camera_id, service_name)
            aforo.set_initial_last_disappeared(srv_camera_id[7:24])
            execute_actions = True
        else:
            com.log_error("Servicio '"+service_name+"' no definido")

    if execute_actions:
        com.log_debug("Adjusted configuration: ")
        print(scfg)
        return True

    com.log_error('Unable to set up value: {}, must be one of this: {}'.format(service_name, com.SERVICES))

