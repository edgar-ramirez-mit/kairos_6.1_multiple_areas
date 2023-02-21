import lib.common as com
import threading

import lib.json_methods as jsm


########## AFORO ##########
# stores the configuration parameters and values of all the defined 
global aforo_list
aforo_list = {}

# almacena datos de entradas salidas por camara
global entradas_salidas
entradas_salidas = {}

# almacena los datos de los id desaparecidos por camera
global initial_last_disappeared
initial_last_disappeared = {}


def setup_displayed_reference_line(py_nvosd_line_params, aforo_info):
    py_nvosd_line_params.x1 = aforo_info['reference_line']['line_coordinates'][0][0]
    py_nvosd_line_params.y1 = aforo_info['reference_line']['line_coordinates'][0][1]
    py_nvosd_line_params.x2 = aforo_info['reference_line']['line_coordinates'][1][0]
    py_nvosd_line_params.y2 = aforo_info['reference_line']['line_coordinates'][1][1]
    py_nvosd_line_params.line_width = aforo_info['reference_line']['line_width']
    py_nvosd_line_params.line_color.red = aforo_info['reference_line']['line_color'][0]
    py_nvosd_line_params.line_color.green = aforo_info['reference_line']['line_color'][1]
    py_nvosd_line_params.line_color.blue = aforo_info['reference_line']['line_color'][2]
    py_nvosd_line_params.line_color.alpha = aforo_info['reference_line']['line_color'][3]

    return py_nvosd_line_params


def setup_displayed_rectangle(py_nvosd_rect_params, aforo_info):
    '''
    # setup del rectangulo de Ent/Sal                        #TopLeftx, TopLefty --------------------
    # de igual manera que los parametros de linea,           |                                      |
    # los valores del rectangulo se calculan en base a       |                                      |
    # los valoes del archivo de configuracion                v                                      |
    #                                                        #Height -------------------------> Width
    '''

    TopLeftx      = aforo_info['reference_line']['area_of_interest']['area_rectangle'][0]
    TopLefty      = aforo_info['reference_line']['area_of_interest']['area_rectangle'][1]
    Width         = aforo_info['reference_line']['area_of_interest']['area_rectangle'][2]
    Height        = aforo_info['reference_line']['area_of_interest']['area_rectangle'][3]
    x_plus_width  = TopLeftx + Width
    y_plus_height = TopLefty + Height
    rectangle = [TopLeftx, TopLefty, Width, Height, x_plus_width, y_plus_height]

    py_nvosd_rect_params.left = TopLeftx
    py_nvosd_rect_params.height = Height
    py_nvosd_rect_params.top = TopLefty
    py_nvosd_rect_params.width = Width
    py_nvosd_rect_params.border_width = 4
    py_nvosd_rect_params.border_color.red = 0.0
    py_nvosd_rect_params.border_color.green = 0.0
    py_nvosd_rect_params.border_color.blue = 1.0
    py_nvosd_rect_params.border_color.alpha = 1.0

    return py_nvosd_rect_params, rectangle



def set_initial_last_disappeared(key_id):
    global initial_last_disappeared

    if key_id not in initial_last_disappeared:
        initial_last_disappeared.update({key_id: [{}, {}, []]})

    set_entrada_salida(key_id, 0, 0)


def get_initial_last(camera_id):
    global initial_last_disappeared

    if camera_id in initial_last_disappeared:
        return initial_last_disappeared[camera_id][0], initial_last_disappeared[camera_id][1]


def set_disappeared(key_id, value = None):
    global initial_last_disappeared

    if value is None:
        initial_last_disappeared[key_id][2] = []
    else:
        initial_last_disappeared[key_id][2] = value


def get_disappeared(key_id):
    global initial_last_disappeared

    if key_id in initial_last_disappeared:
        return initial_last_disappeared[key_id][2]
    return None


def get_aforo(camera_id, key = None, second_key = None):
    global aforo_list

    #information con el camara_id especifico no existe
    if camera_id not in aforo_list:
        return {'enabled': False}, {}

    #si no se especifica una llave en particular, regresamos toda la informacion
    if key is None:
        return aforo_list[camera_id]['enabled'], aforo_list[camera_id]
    else:
        if second_key is None:
            return aforo_list[camera_id]['enabled'], aforo_list[camera_id][key]
        else:
            return aforo_list[camera_id]['enabled'], aforo_list[camera_id][key][second_key]


def setup_display_variables(camera_id, display_meta, py_nvosd_line_params, py_nvosd_rect_params):
    is_aforo_enabled, aforo_info = get_aforo(camera_id)

    if is_aforo_enabled:
        #------------------------------------- display info
        display_meta.num_lines = 1      # numero de lineas
        display_meta.num_rects = 1      # numero de rectangulos  

        # Setup de la linea de Ent/Sal
        # los valos de las coordenadas tienen que ser obtenidos del archivo de configuracion
        # en este momento estan hardcode


        '''
        if aforo_info['reference_line']['line_coordinates']:
            py_nvosd_line_params = setup_displayed_reference_line(py_nvosd_line_params, aforo_info)
        else:
            aforo_info['reference_line']['outside_area'] = None

        rectangle = []
        if aforo_info['reference_line']['area_of_interest']['area_rectangle']:
            py_nvosd_rect_params, rectangle = setup_displayed_rectangle(py_nvosd_rect_params, aforo_info)

        return is_aforo_enabled, aforo_info, display_meta, py_nvosd_line_params, py_nvosd_rect_params, rectangle
        '''

    return False, {}, display_meta, py_nvosd_line_params, py_nvosd_rect_params, []


def set_entrada_salida(key_id, entrada, salida):
    global entradas_salidas

    if key_id not in entradas_salidas:
        entradas_salidas.update({key_id: [entrada, salida]})
    else:
        entradas_salidas[key_id] = [entrada, salida]


def get_entrada_salida(camera_id):
    global entradas_salidas

    if camera_id not in entradas_salidas:
        return 0, 0
    return entradas_salidas[camera_id][0], entradas_salidas[camera_id][1]


def validate_aforo_values(data, service_name, aforo_dict):

    if 'endpoint' not in aforo_dict:
        com.log_error("Missing parameter 'endpoint' for service Aforo")
    else:
        if not isinstance(aforo_dict['endpoint'], str):
            com.log_error("Parameter 'endpoint' most be string")

    if 'reference_line' not in aforo_dict:
        com.log_error("Missing parameter 'reference_line' for service Aforo")
    else:
        if not isinstance(aforo_dict['reference_line'], list):
            com.log_error("reference_line, most be a list of directories")

        for item in aforo_dict['reference_line']:
            if 'line_coordinates' not in item:
                com.log_error("line_coordinates, not defined")
            if not isinstance(item['line_coordinates'], list):
                com.log_error("line_coordinates, should be a list")
            
            for coordinate in item['line_coordinates']:
                if not isinstance(coordinate,list):
                    com.log_error("line_coordinates, elements should be list type")
                if len(coordinate) != 2:
                    com.log_error("line_coordinates, every element is a list representing a coordinates in the layer x,y")
                for element in coordinate:
                    if not isinstance(element, int):
                        com.log_error("line_coordinates, every coordinates x,y should be an integer - {}".format(type(element)))
                    if element < 0:
                        com.log_error("line_coordinates, every coordinates x,y should be an integer positive: {}".format(element))

            if 'outside_area' not in item:
                com.log_error("'outside_area' must be defined as part of the reference_line values")

            if not isinstance(item['outside_area'], int):
                com.log_error("outside_area should be integer")

            if item['outside_area'] not in [1,2]:
                com.log_error("outside_area value most 1 or 2")

            if 'line_width' not in item:
                default_witdth = 3
                item['line_width'] = default_witdth;
                com.log_debug("Parameter 'line_color' was not defined. Using default value: "+str(default_witdth))

            if 'line_color' not in item:
                default_color = [222,221,100,99]
                item['line_color'] = default_color;
                com.log_debug("Parameter 'line_color' was not defined. Using default value: "+default_color)

            for color in item['line_color']:
                try:
                    color_int = int(color)
                except Exception as e:
                    com.log_error("color values should be integers within 0-255")
                if color_int < 0 or color_int > 255:
                    com.log_error("color values should be integers within 0-255")

            if 'area_of_interest' in item:
                for key in item['area_of_interest']:
                    try:
                        element_int = int(item['area_of_interest'][key])
                    except ValueError:
                        com.log_error("Value of parameter: '{}' should be integer: {}".format(key), item['area_of_interest'][key])

                    if element_int < 0:
                        com.log_error("Value of parameter: '{}' should be integer positive - {}".format(key, element_int))

            for parameter in ['padding_right', 'padding_left', 'padding_top', 'padding_bottom']:
                if parameter not in item['area_of_interest']:
                    item['area_of_interest'][parameter] = 0


def check_if_object_is_in_area2(object_coordinates, reference_line, m, b):
    '''
    * returns True if object is in Area2
    * returns False if object is in Area1
    * si m es None la pendiente es infinita es decir recta vertical a 90 grados con respecto de la horizontal
    * si m es 0 recta a horizontal
    '''
    if m is None:
        '''
        # object_coordinates[0] ->  x
        # reference_line[0][0]  ->  x1
        # if x > x1 then is in Area2, else in Area1
        '''
        if object_coordinates[0] > reference_line[0][0]:
            return True
        return False
    elif m == 0:
        '''
        # object_coordinates[1] -  y
        # reference_line[0][1]  -  y1
        # if y > y1 then is in Area2, else in Area1
        '''
        if object_coordinates[1] > reference_line[0][1]:
            return True
        return False
    else:
        '''
        # x1 = reference_line[0][0]
        # y1 = reference_line[0][1]
        # x = object_coordinates[0]
        # m = ((y2 - y1) * 1.0) / (x2 - x1) ... multiply by 1.0 to force float division
        # y_overtheline = (m * (x - x1)) + y1  ... general line ecuation

        *** in the video the y's values increses while going down
        *** Are2 is always the higher values of y's after the reference line

        -------------      ------------
        | A1        /      |  \
        |          /       |   \
        | p=x,y   /        |    \   A1
        |        /  A2     | A   \
        |       /          |      \


        Given a point p=x,y the "x" is evaluated in the line equation, if the calculated "y_overtheline" is lower than the "y" of
        the point "p", then the point is down the line and so in A2
        '''
        y_overtheline = (m * object_coordinates[0]) + b
        '''
        # if y > y_overtheline point is in Area2
        '''
        if object_coordinates[1] > y_overtheline:
            return True
        else:
            return False


def aforo(header, aforo_info, box, object_id, ids, camera_id, initial, last, entradas, salidas, rectangle):
    '''
    A1 is the closest to the origin (0,0) and A2 is the area after the reference line
    A1 is by default the outside
    A2 is by default the inside
    This can be changed by modifying the configuration variable "outside_area" to 2 (by default 1)
    x = box[0]
    y = box[1]

    initial -  must be a dictionary, and will be used to store the first position (Area1 or Area2) of a given ID
    last -     must be a dictionary, and will be used to store the last position (Area1 or Area2) of a given ID
    '''

    aforo_url = aforo_info['endpoint']
    outside_area = aforo_info['reference_line']['outside_area']
    reference_line = aforo_info['reference_line']['line_coordinates']
    m = aforo_info['line_m_b'][0]
    b = aforo_info['line_m_b'][1]

    if rectangle:
        # si el punto esta afuera del area de interes no evaluamos
        if box[0] < rectangle[0] or box[0] > rectangle[4] or box[1] > rectangle[5] and box[1] < rectangle[1]:
            if reference_line:
                return entradas, salidas
            else:
                outside_area = 1
                area = 1

    if reference_line:
        if check_if_object_is_in_area2(box, reference_line, m, b):
            area = 2
        else:
            area = 1
    else:
        outside_area = 1
        area = 2

    if outside_area == 1:
        direction_1_to_2 = 1
        direction_2_to_1 = 0
    else:
        direction_1_to_2 = 0
        direction_2_to_1 = 1

    if object_id not in initial:
        initial.update({object_id: area})
        if object_id not in last:
            return entradas, salidas
    else:
        last.update({object_id: area})

    # De igual forma si los elementos continen las misma areas en el estado
    # actual que en el previo, entonces no tiene caso evaluar mas
    if initial[object_id] == last[object_id]:
        return entradas, salidas

    for item in last.keys():
        if initial[item] == 1 and last[item] == 2:
            time_in_epoc = com.get_timestamp()
            data_id = str(time_in_epoc) + '_' + str(object_id)
            data = {
                    'deepStreamId': data_id,
                    'direction': direction_1_to_2,
                    'cameraId': camera_id,
                    'dateStart': str(time_in_epoc),
                    'reportedEpocTime': str(time_in_epoc),
                }
            initial.update({item: 2})

            print('Sending Json to:',aforo_url, 'camera_id:', camera_id, 'ID: ',item, 'Sal:0,Ent:1 = ', direction_1_to_2, "tiempo =", time_in_epoc)
            #print(data)
            #jsm.send_json(header, data, 'PUT', aforo_url)
            x = threading.Thread(target=jsm.send_json, args=(header, data, 'PUT', aforo_url,))
            x.start()

            if direction_1_to_2 == 1:
                entradas += 1
            else:
                salidas += 1

        elif initial[item] == 2 and last[item] == 1:
            time_in_epoc = com.get_timestamp()
            data_id = str(time_in_epoc) + '_' + str(object_id)
            data = {
                    'deepStreamId': data_id,
                    'direction': direction_2_to_1,
                    'cameraId': camera_id,
                    'dateSstart': str(time_in_epoc),
                    'reportedEpocTime': str(time_in_epoc),
                }
            initial.update({item: 1})

            print('Sending Json to:', aforo_url, 'camera_id: ', camera_id, 'ID: ', item, 'Sal:0,Ent:1 = ', direction_2_to_1, "tiempo =", time_in_epoc)
            #print(data)
            #jsm.send_json(header, data, 'PUT', aforo_url)
            #quit()
            x = threading.Thread(target=jsm.send_json, args=(header, data, 'PUT', aforo_url,))
            x.start()

            if direction_2_to_1 == 1:
                entradas += 1
            else:
                salidas += 1

    return entradas, salidas


def set_aforo(scfg, srv_camera_id, service_name):
    # use aforo_list for aforo
    global aforo_list

    camera_mac = srv_camera_id[7:24]
    data = {}
    for service_definition in scfg[camera_mac]['services']:
        if srv_camera_id in service_definition and service_name in service_definition[srv_camera_id]:
            data = service_definition[srv_camera_id][service_name]

    # Copia de los datos de configuracion de aforo
    aforo_list.update({camera_mac: data})

    for item in data['reference_line']:
        if 'area_of_interest' in data['reference_line']:
            x1 = data['reference_line']['line_coordinates'][0][0]
            y1 = data['reference_line']['line_coordinates'][0][1]
            x2 = data['reference_line']['line_coordinates'][1][0]
            y2 = data['reference_line']['line_coordinates'][1][1]
    
            # padding es un espacio entre la linea y los bordes del area
            # si no se define es por default 0
            padding_left = data['reference_line']['area_of_interest']['padding_left']
            padding_top = data['reference_line']['area_of_interest']['padding_top']
            padding_right = data['reference_line']['area_of_interest']['padding_right']
            padding_bottom = data['reference_line']['area_of_interest']['padding_bottom']
    
            if x1 < x2:
                topx = x1 - padding_left
                width = abs((x2 + padding_right + padding_left) - x1)
            else:
                topx = x2 - padding_left
                width = abs((x1 + padding_right + padding_left) - x2)
    
            # adjusting if value is negative
            if topx < 0:
                topx = 1
    
            if y1 < y2:
                topy = y1 - padding_top
                height = abs((y2 + padding_bottom + padding_top) - y1)
            else:
                topy = y2 - padding_top
                height = abs((y1 + padding_bottom + padding_top) - y2)
    
            # adjusting if value is negative
            if topy < 0:
                topy = 0
    
            # ecuacion de la pendiente
            if (x2 - x1) == 0:
                m = None
                b = None
            elif (y2 - y1) == 0:
                m = 0
                b = 0
            else:
                m = ((y2 - y1) * 1.0) / (x2 -x1)
                b = y1 - (m * x1)
    
            if 'line_width' not in data['reference_line']:
                data['reference_line']['line_width'] = 2
    
            aforo_list[camera_mac].update({'line_m_b': [m, b]})
            aforo_list[camera_mac]['reference_line']['area_of_interest'].update({'area_rectangle': [topx, topy, width, height]})
            aforo_list[camera_mac]['endpoint'] = scfg[camera_mac]['server_url']+aforo_list[camera_mac]['endpoint']
        else:
            com.log_error("Missing configuration parameters for 'aforo' service")

