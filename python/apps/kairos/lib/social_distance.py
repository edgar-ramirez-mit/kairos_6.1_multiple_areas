

########## SOCIAL DISTANCE ##########
global social_distance_list
social_distance_list = {}
global social_distance_url
global social_distance_ids
social_distance_ids = {}


def set_social_distance_url(server_url):
    global social_distance_url
    social_distance_url = srv_url + 'tx/video-socialDistancing.endpoint'


def social_distance2(camera_id, ids_and_boxes, social_distance_info):
    '''
    social distance is perform in pairs of not repeated pairs
    Being (A, B, C, D, E, F) the set of detected objects

    The possible permutation are:

       AB AC AD AE AF
          BC BD BE BF
             CD CE CF
                DE DF
                   Ef

    We are going to start compararing the first element (index=0 or i=0)
    '''
    # TODO: diccionario puede crecer mucho depurarlo comparando los elementos que dejen de existir o no sean detectados despues de 5seg')


    persistence_time = social_distance_info['persistence_time']
    tolerated_distance = social_distance_info['tolerated_distance']
    max_side_plus_side = tolerated_distance * 1.42
    detected_ids = social_distance_info['social_distance_ids']


    # sorting elements to always have the same evaluation order 
    ids = [ item for item in ids_and_boxes.keys() ]
    ids.sort()
    # creating the list 
    i = 1
    for pivot in ids[:-1]:
        for inner in ids[i:]:
            if pivot not in detected_ids:
                Ax = ids_and_boxes[pivot][0]
                x = ids_and_boxes[inner][0]
    
                if Ax > x:
                    dx = Ax -x
                else:
                    dx = x - Ax
    
                if dx < tolerated_distance:
                    Ay = ids_and_boxes[pivot][1]
                    y = ids_and_boxes[inner][1]

                    if Ay > y:
                        dy = Ay - y
                    else:
                        dy = y - Ay

                    if (dx + dy) < max_side_plus_side and sqrt((dx*dx) + (dy*dy)) < tolerated_distance:
                        # first time detection for pivot A and associated B
                        pivot_time = com.get_timestamp()
                        detected_ids.update({
                            pivot: {
                                inner:{
                                    '#detected_at': pivot_time,
                                    '#reported_at': None,
                                    'reported': False,
                                    }
                                }
                            })
            else:
                if inner not in detected_ids[pivot]:
                    Ax = ids_and_boxes[pivot][0]
                    x = ids_and_boxes[inner][0]
        
                    if Ax > x:
                        dx = Ax -x
                    else:
                        dx = x - Ax
        
                    if dx < tolerated_distance:
                        Ay = ids_and_boxes[pivot][1]
                        y = ids_and_boxes[inner][1]

                        if Ay > y:
                            dy = Ay - y
                        else:
                            dy = y - Ay

                        if (dx + dy) < max_side_plus_side and sqrt((dx*dx) + (dy*dy)) < tolerated_distance:
                            # firt time detection for associated C is registered
                            detected_at_inner = com.get_timestamp()
                            detected_ids[pivot].update({
                                inner:{
                                    '#detected_at': detected_at_inner,
                                    '#reported_at': None,
                                    'reported': False,
                                    }
                                })
                else:
                    Ax = ids_and_boxes[pivot][0]
                    x = ids_and_boxes[inner][0]
        
                    if Ax > x:
                        dx = Ax -x
                    else:
                        dx = x - Ax

                    if dx > tolerated_distance:
                        if not detected_ids[pivot][inner]['reported']:
                            del detected_ids[pivot][inner]
                    else:
                        Ay = ids_and_boxes[pivot][1]
                        y = ids_and_boxes[inner][1]

                        if Ay > y:
                            dy = Ay - y
                        else:
                            dy = y - Ay

                        if (dx + dy) >= max_side_plus_side or sqrt((dx*dx) + (dy*dy)) >= tolerated_distance:
                            del detected_ids[pivot][inner]
                        else:
                            current_time = com.get_timestamp()
                            initial_time = detected_ids[pivot][inner]['#detected_at']
                            if not detected_ids[pivot][inner]['reported'] and (current_time - initial_time) >= persistence_time:
                                detected_ids[pivot][inner].update({'#reported_at': current_time})
                                detected_ids[pivot][inner].update({'reported': True})
                                alert_id = str(current_time) + '_' +  str(pivot) + '_and_'+ str(inner)
                                data = {
                                    'id': alert_id,
                                    'camera-id': camera_id,
                                    '#date': current_time,
                                    }
                                print('Social distance', data, social_distance_url, 'PUT', 'distance=', sqrt((dx*dx) + (dy*dy)), 'tolerada:', tolerated_distance)
                                x = threading.Thread(target=send_json, args=(data, 'PUT', social_distance_url,))
                                x.start()
            i += 1


def set_social_distance(key_id, social_distance_data):
    global social_distance_list

    if not isinstance(social_distance_data, dict):
        service.log_error("'social_distance_data' parameter, most be a dictionary")

    if not isinstance(social_distance_data['enabled'], bool):
        service.log_error("'social_distance_data' parameter, most be True or False")

    if not isinstance(int(float(social_distance_data['tolerated_distance'])), int) and int(float(social_distance_data['tolerated_distance'])) > 3:
        service.log_error("'social_distance_data.tolarated_distance' parameter, most be and integer bigger than 3 pixels")
    else:
        new_value = int(float(social_distance_data['tolerated_distance']))
        social_distance_data.update({'tolerated_distance': new_value})

    if not isinstance(int(float(social_distance_data['persistence_time'])), int) and int(float(social_distance_data['persistence_time'])) > -1:
        service.log_error("'social_distance_data.persistence_time' parameter, most be a positive integer/floater")
    else:
        new_value = int(float(social_distance_data['persistence_time'])) * 1000
        social_distance_data.update({'tolerated_distance': new_value})

    #social_distance_data.update({'persistence_time': social_distance_data['persistence_time'] * 1000})

    social_distance_list.update(
            {
                key_id: social_distance_data
            })

    social_distance_list[key_id].update({'social_distance_ids': {}})


def get_social_distance(camera_id, key = None):
    global social_distance_list

    if camera_id not in social_distance_list.keys():
        return  False, {}

    if social_distance_list:
        if key:
            return social_distance_list[camera_id]['enabled'], social_distance_list[camera_id][key]
        else:
            return  social_distance_list[camera_id]['enabled'], social_distance_list[camera_id]


def validate_socialdist_values(data):

    #print('print1', data, '...', ['enabled', 'tolerated_distance', 'persistence_time'])
    if not validate_keys('video-socialDistancing', data, ['enabled', 'tolerated_distance', 'persistence_time']):
        return False

    if not isinstance(data['enabled'], str):
        service.log_error("'enabled' parameter, most be string: {}".format(data['enabled']))
    
    if not isinstance(float(data['tolerated_distance']), float) and float(data['tolerated_distance']) > 0:
        service.log_error("tolerated_distance element, most be a positive integer")
    else:
        data.update({'tolerated_distance': float(data['tolerated_distance'])})

    if not isinstance(float(data['persistence_time']), float)  and float(data['persistence_time']) > 0:
        service.log_error("persistence_time element, most a be positive integer/floater")
    else:
        data.update({'persistence_time': float(data['persistence_time'])})

    return True


def validate_people_counting_values(data):

    validate_keys('people_counting', data, ['enabled'])

    if not isinstance(data['enabled'], bool):
        service.log_error("'people_counting.' parameter, most be True or False, current value: {}".format(data['enabled']))

    return True


def get_social_distance_url():
    global social_distance_url
    return social_distance_url


def set_social_distance_url(server_url):
    global social_distance_url
    social_distance_url = server_url + 'tx/video-socialDistancing.endpoint'
    return social_distance_url


def validate_keys(service, data, list_of_keys):

    if not isinstance(data, dict):
        service.log_error("'data' parameter, most be a dictionary")
    if 'enabled' not in data:
        return False

    for key in data.keys():
        if key == 'enabled' and data[key] == 'False':
            return False

    for key in list_of_keys:
        if key not in data.keys():
            service.log_error("'{}' missing parameter {}, in config file".format(service, key))

    return True

