#!/usr/bin/env python3

#rm ${HOME}/.cache/gstreamer-1.0/registry.aarch64.bin    borrar cache
################################################################################
# SPDX-FileCopyrightText: Copyright (c) 2019-2022 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
################################################################################











import sys

sys.path.append('../')
import platform
import configparser

import gi
gi.require_version('Gst', '1.0')
from gi.repository import GObject, Gst
from common.is_aarch_64 import is_aarch64
from common.bus_call import bus_call
from common.FPS import GETFPS

import pyds

#Bibliotecas Adicioanles para la funcionaliad con Tiler
from gi.repository import GLib
from ctypes import *
import time
import math



#################################
import lib.biblioteca as biblio
import lib.server as srv
import lib.common as com
import lib.validate as vl
import lib.aforo_values as aforo
import lib.social_distance as socialdist
import lib.people_counting as peoplecount
import lib.generic as gc
#################################














PGIE_CLASS_ID_PERSON = 0# si se ocupa Peoplenet la clase es 0 personas, bolsas 1 y rostros 2













MAX_DISPLAY_LEN = 64
MUXER_OUTPUT_WIDTH = 1920
MUXER_OUTPUT_HEIGHT = 1080
MUXER_BATCH_TIMEOUT_USEC = 4000000
TILED_OUTPUT_WIDTH = 1920
TILED_OUTPUT_HEIGHT = 1080
GST_CAPS_FEATURES_NVMM = "memory:NVMM"

#pgie_classes_str = ["Vehicle", "TwoWheeler", "Person", "RoadSign"]


def tiler_src_pad_buffer_probe(pad, info, u_data):



    obj_counter = {
            PGIE_CLASS_ID_PERSON: 0
            }





    frame_number = 0
    num_rects = 0                      # numero de objetos en el frame
    gst_buffer = info.get_buffer()

    if not gst_buffer:
        print("Unable to get GstBuffer ")
        return

    batch_meta = pyds.gst_buffer_get_nvds_batch_meta(hash(gst_buffer))
    l_frame = batch_meta.frame_meta_list

    #====================== Definicion de valores de mensajes a pantalla
    display_meta = pyds.nvds_acquire_display_meta_from_pool(batch_meta)
    current_pad_index = pyds.NvDsFrameMeta.cast(l_frame.data).pad_index
    # Todos los servicios requieren impresion de texto solo para Aforo se requiere una linea y un rectangulo
    display_meta.num_labels = 1                            # numero de textos
    py_nvosd_text_params = display_meta.text_params[0]
    py_nvosd_line_params = display_meta.line_params[0]                
    py_nvosd_rect_params = display_meta.rect_params[0]        

    # Setup los label de impresion en pantalla
    py_nvosd_text_params = gc.setup_displayed_text(py_nvosd_text_params)

    # Get the camera id - unique for each camera
    camera_id = gc.get_camera_id(current_pad_index)

    # Get information of service aforo and check if it is enabled
    is_aforo_enabled, aforo_info, display_meta, py_nvosd_line_params, py_nvosd_rect_params, rectangle = aforo.setup_display_variables(camera_id, display_meta, py_nvosd_line_params, py_nvosd_rect_params)

    # Get the information of service social_distance and check if it is enabled
    is_social_distance_enabled, social_distance_info = socialdist.get_social_distance(camera_id)

    # Get the information of service people_counting and check if it is enabled
    is_people_counting_enabled, people_counting_info = peoplecount.get_people_counting(camera_id)

    while l_frame is not None:
        try:
            frame_meta = pyds.NvDsFrameMeta.cast(l_frame.data)
        except StopIteration:
            break

        frame_number = frame_meta.frame_num
        l_obj = frame_meta.obj_meta_list
        num_rects = frame_meta.num_obj_meta
        
        ids = []
        boxes = []
        ids_and_boxes = {}

        # Ciclo interno donde se evaluan los objetos dentro del frame
        while l_obj is not None:
            try:
                # Casting l_obj.data to pyds.NvDsObjectMeta
                obj_meta = pyds.NvDsObjectMeta.cast(l_obj.data)
            except StopIteration:
                break

            x = obj_meta.rect_params.width
            y = obj_meta.rect_params.height
            t = obj_meta.rect_params.top
            l = obj_meta.rect_params.left
         
            obj_counter[obj_meta.class_id] += 1
            ids.append(obj_meta.object_id)
            x = int(obj_meta.rect_params.left + obj_meta.rect_params.width/2)

            if is_social_distance_enabled:
                # centroide al pie
                y = int(obj_meta.rect_params.top + obj_meta.rect_params.height) 
                ids_and_boxes.update({obj_meta.object_id: (x, y)})

            # Service Aforo (in and out)
            if is_aforo_enabled:
                # centroide al hombligo
                y = int(obj_meta.rect_params.top + obj_meta.rect_params.height/2) 
                boxes.append((x, y))

                if aforo_info['reference_line']['area_of_interest']['area_rectangle']:
                    entrada, salida = aforo.get_entrada_salida(camera_id)
                    initial, last = aforo.get_initial_last(camera_id)
                    header = gc.get_header()
                    entrada, salida = aforo.aforo(header, aforo_info, (x, y), obj_meta.object_id, ids, camera_id, initial, last, entrada, salida, rectangle)
                    aforo.set_entrada_salida(camera_id, entrada, salida)

            try: 
                l_obj = l_obj.next
            except StopIteration:
                break

        if is_aforo_enabled:
            '''
            Este bloque limpia los dictionarios initial y last, recolectando los ID que 
            ya no estan en la lista actual, es decir, "candidatos a ser borrados" y
            despues es una segunda corroboracion borrandolos
            15 se elige como valor maximo en el cual un id puede desaparecer, es decir, si un id desaparece por 15 frames, no esperamos
            recuperarlo ya
            '''
            entrada, salida = aforo.get_entrada_salida(camera_id)
            py_nvosd_text_params.display_text = "AFORO Total persons={} Entradas={} Salidas={}".format(obj_counter[PGIE_CLASS_ID_PERSON], entrada, salida)
            if frame_number > 0 and frame_number % 159997967 == 0:
                disappeared = get_disappeared(camera_id)
                initial, last = aforo.get_initial_last(camera_id)
                if disappeared:
                    elements_to_be_delete = [ key for key in last.keys() if key not in ids and key in disappeared ]
                    for x in elements_to_be_delete:
                        last.pop(x)
                        initial.pop(x)
                    set_disappeared(camera_id)
                else:
                    elements_to_be_delete = [ key for key in last.keys() if key not in ids ]
                    set_disappeared(camera_id, elements_to_be_delete)

        if is_social_distance_enabled:
            if len(ids_and_boxes) > 1: # if only 1 object is present there is no need to calculate the distance
                socialdist.social_distance2(camera_id, ids_and_boxes, social_distance_info)
            py_nvosd_text_params.display_text = "SOCIAL DISTANCE Source ID={} Source Number={} Person_count={} ".format(frame_meta.source_id, frame_meta.pad_index , obj_counter[PGIE_CLASS_ID_PERSON])

        if is_people_counting_enabled:
            if obj_counter[PGIE_CLASS_ID_PERSON] != peoplecount.get_people_counting_counter(camera_id):
                set_people_counting_counter(camera_id, obj_counter[PGIE_CLASS_ID_PERSON])
                peoplecount.people_counting(camera_id, obj_counter[PGIE_CLASS_ID_PERSON])

        #====================== FIN de definicion de valores de mensajes a pantalla

        # Lo manda a directo streaming
        pyds.nvds_add_display_meta_to_frame(frame_meta, display_meta)


        try:
            l_frame = l_frame.next
        except StopIteration:
            break

    return Gst.PadProbeReturn.OK


def cb_newpad(decodebin, decoder_src_pad, data):
    print("In cb_newpad\n")
    caps = decoder_src_pad.get_current_caps()
    gststruct = caps.get_structure(0)
    gstname = gststruct.get_name()
    source_bin = data
    features = caps.get_features(0)

    # Need to check if the pad created by the decodebin is for video and not audio.
    print("gstname=", gstname)
    if gstname.find("video") != -1:
        # Link the decodebin pad only if decodebin has picked nvidia
        # decoder plugin nvdec_*. We do this by checking if the pad caps contain
        # NVMM memory features.
        print("features=", features)
        if features.contains("memory:NVMM"):
            # Get the source bin ghost pad
            bin_ghost_pad = source_bin.get_static_pad("src")
            if not bin_ghost_pad.set_target(decoder_src_pad):
                sys.stderr.write("Failed to link decoder src pad to source bin ghost pad\n")
        else:
            sys.stderr.write(" Error: Decodebin did not pick nvidia decoder plugin.\n")


def decodebin_child_added(child_proxy, Object, name, user_data):
    print("Decodebin child added:", name, "\n")
    if name.find("decodebin") != -1:
        Object.connect("child-added", decodebin_child_added, user_data)
    if is_aarch64() and name.find("nvv4l2decoder") != -1:
        print("Seting bufapi_version\n")
        Object.set_property("bufapi-version", True)


def create_source_bin(index, uri):
    print("Creating source bin")

    # Create a source GstBin to abstract this bin's content from the rest of the pipeline
    bin_name = "source-bin-%02d" % index
    nbin = Gst.Bin.new(bin_name)
    if not nbin:
        sys.stderr.write(" Unable to create source bin \n")

    # Source element for reading from the uri.
    # We will use decodebin and let it figure out the container format of the
    # stream and the codec and plug the appropriate demux and decode plugins.
    uri_decode_bin = Gst.ElementFactory.make("uridecodebin", "uri-decode-bin")
    if not uri_decode_bin:
        sys.stderr.write(" Unable to create uri decode bin \n")
    # We set the input uri to the source element
    uri_decode_bin.set_property("uri", uri)
    uri_decode_bin.connect("pad-added", cb_newpad, nbin)
    uri_decode_bin.connect("child-added", decodebin_child_added, nbin)

    Gst.Bin.add(nbin, uri_decode_bin)
    bin_pad = nbin.add_pad(Gst.GhostPad.new_no_target("src", Gst.PadDirection.SRC))
    if not bin_pad:
        sys.stderr.write(" Failed to add ghost pad in source bin \n")
        return None
    return nbin


def main():
    number_sources = gc.setup_services()
    is_live = False

    # Standard GStreamer initialization
    GObject.threads_init()
    Gst.init(None)

    # Create gstreamer elements
    # Create Pipeline element that will form a connection of other elements
    com.log_debug("Creating Pipeline")
    pipeline = Gst.Pipeline()

    if not pipeline:
        sys.stderr.write(" Unable to create Pipeline \n")

    # Create nvstreammux instance to form batches from one or more sources.
    com.log_debug("Creating streamux")
    streammux = Gst.ElementFactory.make("nvstreammux", "Stream-muxer")
    if not streammux:
        sys.stderr.write(" Unable to create NvStreamMux \n")

    # Create Pipeline element that will form a connection of other elements
    com.log_debug("Creating Pipeline")
    pipeline.add(streammux)

    # Se crea elemento que acepta todo tipo de video o RTSP
    i = 0
    for ordered_key in gc.call_order_of_keys:
        
        
        

        # Defining only 1 active source per camera 
        for service_id in gc.scfg[ordered_key]:
            uri_name = gc.scfg[ordered_key]['source']

            com.log_debug("Creating source_bin: {}.- {} with uri_name: {}\n".format(i, ordered_key, uri_name))

            if uri_name.find("rtsp://") == 0 :
                is_live = True

            source_bin = create_source_bin(i, uri_name)
            if not source_bin:
                com.log_error("Unable to create source bin")

            pipeline.add(source_bin)
            padname = "sink_%u" % i

            sinkpad = streammux.get_request_pad(padname)
            if not sinkpad:
                com.log_error("Unable to create sink pad bin")
            srcpad = source_bin.get_static_pad("src")
            if not srcpad:
                com.log_error("Unable to create src pad bin")
            srcpad.link(sinkpad)
            i += 1
            break

    com.log_debug("Numero de fuentes :{}".format(number_sources))
    print("\n------ Fps_streams: ------ \n", gc.fps_streams)


    '''
    -------- Service configurations loaded --------
    '''

    print("Creating Decoder \n")
    decoder = Gst.ElementFactory.make("nvv4l2decoder", "nvv4l2-decoder")
    if not decoder:
        sys.stderr.write(" Unable to create Nvv4l2 Decoder \n")

    # Use nvinfer to run inferencing on decoder's output,
    # behaviour of inferencing is set through config file

    pgie = Gst.ElementFactory.make("nvinfer", "primary-inference")
    if not pgie:
        sys.stderr.write(" Unable to create pgie \n")

    tracker = Gst.ElementFactory.make("nvtracker", "tracker")
    if not tracker:
        sys.stderr.write(" Unable to create tracker \n")





























    print("Creating tiler \n ")
    tiler = Gst.ElementFactory.make("nvmultistreamtiler", "nvtiler")
    if not tiler:
        sys.stderr.write(" Unable to create tiler \n")
    print("Creating nvvidconv \n ")
    nvvidconv = Gst.ElementFactory.make("nvvideoconvert", "convertor")
    if not nvvidconv:
        sys.stderr.write(" Unable to create nvvidconv \n")

    # Create OSD to draw on the converted RGBA buffer
    nvosd = Gst.ElementFactory.make("nvdsosd", "onscreendisplay")

    if not nvosd:
        sys.stderr.write(" Unable to create nvosd \n")

    # Finally render the osd output
    if is_aarch64():
        transform = Gst.ElementFactory.make("nvegltransform", "nvegl-transform")

    print("Creating EGLSink \n")
    sink = Gst.ElementFactory.make("nveglglessink", "nvvideo-renderer")
    sink.set_property('sync', 0)

    if not sink:
        sys.stderr.write(" Unable to create egl sink \n")
        
    if is_live:
        print("At least one of the sources is live")
        streammux.set_property('live-source', 1)
        
    # Tamano del streammux, si el video viene a 720, se ajusta automaticamente
    streammux.set_property('width', MUXER_OUTPUT_WIDTH)
    streammux.set_property('height', MUXER_OUTPUT_HEIGHT)
    streammux.set_property('batch-size', 1)
    streammux.set_property('batched-push-timeout', MUXER_BATCH_TIMEOUT_USEC)

    #
    # Configuracion de modelo
    # dstest2_pgie_config contiene modelo estandar, para  yoloV3, yoloV3_tiny y fasterRCNN





    pgie.set_property('config-file-path', gc.CURRENT_DIR + "/configs/kairos_peoplenet_pgie_config.txt")




    pgie_batch_size = pgie.get_property("batch-size")
    if pgie_batch_size != number_sources:
        print("WARNING: Overriding infer-config batch-size", pgie_batch_size," with number of sources ", number_sources, " \n")
        pgie.set_property("batch-size",number_sources)










    # Set properties of tracker
    config = configparser.ConfigParser()
    config.read('configs/dstest2_tracker_config.txt')
    #config.read('configs/kairos_peoplenet_tracker_config.txt')
    config.sections()

    ######## TRACKER ########
    for key in config['tracker']:
        if key == 'tracker-width':
            tracker_width = config.getint('tracker', key)
            tracker.set_property('tracker-width', tracker_width)
        elif key == 'tracker-height':
            tracker_height = config.getint('tracker', key)
            tracker.set_property('tracker-height', tracker_height)
        elif key == 'gpu-id':
            tracker_gpu_id = config.getint('tracker', key)
            tracker.set_property('gpu_id', tracker_gpu_id)
        elif key == 'll-lib-file':
            tracker_ll_lib_file = config.get('tracker', key)
            tracker.set_property('ll-lib-file', tracker_ll_lib_file)
        elif key == 'll-config-file':
            tracker_ll_config_file = config.get('tracker', key)
            tracker.set_property('ll-config-file', tracker_ll_config_file)
        elif key == 'enable-batch-process':
            tracker_enable_batch_process = config.getint('tracker', key)
            tracker.set_property('enable_batch_process', tracker_enable_batch_process)
    #########################

    # Creacion del marco de tiler 
    tiler_rows = int(math.sqrt(number_sources))                           # Example 3 = 1 renglones
    tiler_columns = int(math.ceil((1.0 * number_sources)/tiler_rows))     # Example 3 = 3 columnas
    tiler.set_property("rows", tiler_rows)
    tiler.set_property("columns", tiler_columns)
    tiler.set_property("width", TILED_OUTPUT_WIDTH)
    tiler.set_property("height", TILED_OUTPUT_HEIGHT)

    


    print("Adding elements to Pipeline \n")




    pipeline.add(decoder)
    pipeline.add(pgie)
    pipeline.add(tracker)



    pipeline.add(tiler)
    pipeline.add(nvvidconv)
    pipeline.add(nvosd)
    pipeline.add(sink)
    if is_aarch64():
        pipeline.add(transform)

    # we link the elements together
    # source_bin -> -> nvh264-decoder -> PGIE -> Tracker
    # tiler -> nvvidconv -> nvosd -> video-renderer
    print("Linking elements in the Pipeline \n")


    source_bin.link(decoder)
    decoder.link(streammux)
    streammux.link(pgie)
    pgie.link(tracker)
    tracker.link(tiler)

    #tracker.link(sgie1)
    #sgie1.link(sgie2)
    #sgie2.link(sgie3)
    #sgie3.link(tiler)

    tiler.link(nvvidconv)
    nvvidconv.link(nvosd)
    
    if is_aarch64():
        nvosd.link(transform)
        transform.link(sink)
    else:
        nvosd.link(sink)

    # create and event loop and feed gstreamer bus mesages to it
    loop = GObject.MainLoop()

    bus = pipeline.get_bus()
    bus.add_signal_watch()
    bus.connect("message", bus_call, loop)

    # Lets add probe to get informed of the meta data generated, we add probe to
    # the sink pad of the osd element, since by that time, the buffer would have
    # had got all the metadata.

    tiler_src_pad = tracker.get_static_pad("src")
    if not tiler_src_pad:
        sys.stderr.write(" Unable to get src pad \n")
    else:
        tiler_src_pad.add_probe(Gst.PadProbeType.BUFFER, tiler_src_pad_buffer_probe, 0)
    
    print("Starting pipeline \n")
    # start play back and listed to events
    pipeline.set_state(Gst.State.PLAYING)

    # start play back and listed to events
    try:
        loop.run()
    except Exception as e:
        print("This line? "+str(e))
        pass

    # cleanup
    print("Exiting app\n")
    pipeline.set_state(Gst.State.NULL)


if __name__ == '__main__':
    sys.exit(main())

