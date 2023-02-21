

########## PEOPLE COUNTING ##########
global people_counting_url
global people_counting_counters
people_counting_counters = {}
global people_distance_list
people_distance_list = {}


def set_service_people_counting_url(server_url):
    global people_counting_url
    people_counting_url = server_url + 'SERVICE_NOT_DEFINED_'


def people_counting(camera_id, total_objects):
    '''
    Sending only the total of detected objects
    '''
    global people_counting_url
    
    date = get_timestamp()
    alert_id = str(date) + '_' + str(camera_id) + '_' + str(date)
    data = {
            'id': alert_id,
            'camera-id': camera_id,
            '#total_updated_at': date,
            'object_id': total_objects,
            }
    #print('People_counting first time..POST', data, people_counting_url)
    #x = threading.Thread(target=send_json, args=(data, 'POST', srv_url))
    #x.start()


def get_people_counting_counter(key_id):
    global people_counting_counters

    if key_id and key_id in people_counting_counters.keys():
        return people_counting_counters[key_id]


def set_people_counting_counter(key_id, value):
    global people_counting_counters

    if key_id is not None and isinstance(value, int) and value > -1:
        people_counting_counters.update({key_id: value})


def set_people_counting(key_id, people_couting_data):
    global people_distance_list

    if not isinstance(people_couting_data, dict):
        service.log_error("'people_counting_data' parameter, most be a dictionary")

    if not isinstance(people_couting_data['enabled'], bool) :
        service.log_error("'people_counting_data' parameter, most be True or False")

    people_distance_list[key_id] = people_couting_data
    set_people_counting_counter(key_id, 0)


def get_people_counting(camera_id):
    global people_distance_list

    if camera_id not in people_distance_list.keys():
        return False, {}

    return people_distance_list[camera_id]['enabled'], people_distance_list[camera_id]


def set_service_people_counting_url(server_url):
    global people_counting_url
    people_counting_url = server_url + 'SERVICE_NOT_DEFINED_'
    return people_counting_url


def get_service_people_counting_url():
    global people_counting_url
    return people_counting_url


