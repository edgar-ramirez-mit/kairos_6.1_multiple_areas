
def get_min_max_of_coordinate(index, a, b):
    if a[index] < b[index]:
        return a[index], b[index]
    return b[index], a[index]


def check_area_corners_are_not_in_areas(areas, order_areas=False):
    for area_name, area in areas.items():
        search_areas = [ areas[key] for key in areas if area != areas[key] ]
        for search_area_xy in search_areas:
            for xy in area:
                result = verify_they_dont_touch_each_other(xy, search_area_xy)
                if result is False:
                    print('areas touch each other')
                    return result
    return True
            

def verify_they_dont_touch_each_other(coordinate, area):
    #checking x is not between xmin and xmax
    if area[0][0] < coordinate[0] and coordinate[0] < area[1][0]:
        if area[0][1] < coordinate[1] and coordinate[1] < area[2][1]:
            # means areas touch each other
            return False
    return True


def get_mins_maxs_from_list(search_areas_as_dict):
    if not isinstance(search_areas_as_dict, dict):
        print("Error, must be a directory")
        exit(1)
    i=1
    xmins = {}
    ymins = {}
    xmaxs = {}
    ymaxs = {}

    for area_name, area_coordinates in search_areas_as_dict.items():
        xmin, xmax = get_min_max_of_coordinate(0, area_coordinates[0], area_coordinates[1])
        ymin, ymax = get_min_max_of_coordinate(1, area_coordinates[0], area_coordinates[1])

        if area_name not in xmins:
            xmins.update({xmin: [area_name]})
        else:
            xmins[xmin].append(area_name)
    
        if area_name not in xmins:
            ymins.update({ymin: [area_name]})
        else:
            ymins[ymin].append(area_name)
    
        if area_name not in xmins:
            xmaxs.update({xmax: [area_name]})
        else:
            xmaxs[xmax].append(area_name)
    
        if area_name not in xmins:
            ymaxs.update({ymax: [area_name]})
        else:
            xmins[ymax].append(area_name)

    return xmins, ymins, xmaxs, ymaxs


def generate_rectangle_based_on_reference_line(areas_dictionary):
    '''
    En base a las lineas de referencia genera las coordenadas de 
    los rectangulos donde los puntos siempre estan en este orden:

        p1---------p2
        |           |
        |           |
        |           |
        p4---------p3
    '''
    i=1
    areas = []
    for c in areas_dictionary: 
        xmin, xmax = get_min_max_of_coordinate(0, areas_dictionary[c][0], areas_dictionary[c][1])
        ymin, ymax = get_min_max_of_coordinate(1, areas_dictionary[c][0], areas_dictionary[c][1])
        name=i
        areas.append({name: [(xmin,ymin), (xmax,ymin), (xmin,ymax), (xmax, ymax)]})
        i+=1
    return areas


def area_coordinates_as_dictionary(area_lists):
    areas_as_dictionary = {}
    for area in area_lists:
        for area_name, coordinates in area.items():
            areas_as_dictionary.update({area_name: coordinates})
    return areas_as_dictionary


############### Ejemplo de como ejecutar el codigo para determinar si los
############### rectangulos generados por las lineas de referencias se tocan 
############### en algun punto
'''
reference_lines = {
        "a": [(40,100),(300,30)],
        "b": [(400,100),(900,300)],
        "c": [(540,400),(1300,600)]
        }

#En base a las lineas de referencia genera las coordenadas de 
#los rectangulos donde los puntos siempre estan en este orden:

    p1---------p2
    |           |
    |           |
    |           |
    p4---------p3

'''
#areas = generate_rectangle_based_on_reference_line(reference_lines)
'''
Almacenamos las coordenadas de las areas como dictionarios para poder referirlas por name
'''
#areas_as_dictionary = area_coordinates_as_dictionary(areas)
'''
verifica que las areas no se toquen en ningun punto entre si
'''
#if check_area_corners_are_not_in_areas(areas_as_dictionary):
#    print('Las areas no se tocan entre si --- Todo OK')
#else:
#    print('Error --- alguna de las areas se toca con la otra')

#xmins, ymins, xmaxs, ymaxs = get_mins_maxs_from_list(areas_as_dictionary)
#print(xmins, ymins, xmaxs, ymaxs)

