#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import io
import argparse
import logging
import time
import subprocess
import threading
import json
from wsgiref.simple_server import make_server
from wsgiref.simple_server import WSGIRequestHandler
from PIL import Image
import numpy as np

import pycozmo

class RCApp(object):
    """ Application class. """

    def __init__(self):
        logging.info("Initializing...")
        self._stop = False
        self.cli = pycozmo.Client()
        self.speed_left = 0.0   # 0 - 1.0
        self.speed_right = 0.0  # 0 - 1.0

    def init(self):
        """ Initialize application. """
        self._stop = False

        # Setup server
        self.server = make_server('', 3141, handle_api_post, handler_class=NoLoggingWSGIRequestHandler)

        # Connect to Cozmo
        self.cli.start()
        self.cli.connect()
        self.cli.wait_for_robot()

        # Raise head
        angle = (pycozmo.robot.MAX_HEAD_ANGLE.radians - pycozmo.robot.MIN_HEAD_ANGLE.radians) * 0.1
        self.cli.set_head_angle(angle)
        time.sleep(0.5)

#        self.set_cozmo_face()
#        self.cli.load_anims("/home/pi/Cozmo/Android/obb/com.anki.cozmo/assets/cozmo_resources/assets/animations")

        return True

    def term(self):
        """ Terminate application. """
        logging.info("Terminating...")

        self.cli.stop_all_motors()
        self.cli.disconnect()
        self.cli.stop()

    def run(self):
        """ Main loop. """
        logging.info("Starting...")

        self.cli.conn.add_handler(pycozmo.protocol_encoder.RobotState, on_robot_state)
        self.cli.conn.add_handler(pycozmo.protocol_encoder.RobotPoked, on_robot_poked)

        # Setup camera
        pkt = pycozmo.protocol_encoder.EnableCamera(image_send_mode=1, image_resolution=6)
        self.cli.conn.send(pkt)
        pkt = pycozmo.protocol_encoder.EnableColorImages(enable=False)
        self.cli.conn.send(pkt)

        # Wait for image to stabilize.
        self.cli.add_handler(pycozmo.event.EvtNewRawCameraImage, handle_camera_image, one_shot=True)
        time.sleep(1.0)

        res = subprocess.run(["raspistill", "-o", "/var/www/html/cozmo/camera2.jpg", "-rot", "270", "-w", "512", "-h", "360", "-t", "300"], stdout=subprocess.PIPE)

        camera_t = threading.Thread(target = camera_thread)
        camera_t.start()

        try:
            self.server.serve_forever()
        except:
            self.stop()

        logging.info("Done.")

    def stop(self):
        logging.debug("Stopping...")
        self._stop = True

    def _drive_lift(self, speed):
        self.cli.move_lift(speed)

    def _drive_head(self, speed):
        self.cli.move_head(speed)

    def _drive_wheels(self, speed_left, speed_right):
        lw = int(speed_left * pycozmo.MAX_WHEEL_SPEED.mmps)
        rw = int(speed_right * pycozmo.MAX_WHEEL_SPEED.mmps)
        self.cli.drive_wheels(lwheel_speed=lw, rwheel_speed=rw)

    def _handle_input(self, cmd, val):

        update = False

        if cmd == 'nop':
            return

#        print('command = ', cmd, val)

        if cmd == 'stop':
            self.stop()

        elif cmd == 'lift':
            if val == 'up' :
                self._drive_lift(0.8)
            elif val == 'down' :
                self._drive_lift(-0.8)
            else:
                self._drive_lift(0.0)

        elif cmd == 'head':
            if val == 'up' :
                self._drive_head(0.8)
            elif val == 'down' :
                self._drive_head(-0.8)
            else:
                self._drive_head(0.0)

        elif cmd == 'turn':
            # val = -100 - full turn left
            # val =  180 - full turn right
            self.speed_left = self.speed_right = float(val) / 100.0
            self.speed_right = -self.speed_right
            update = True

        elif cmd == 'move':
            # val =  100 - full forward
            # val = -100 - full reverse
            self.speed_left = self.speed_right = float(val) / 100.0
            update = True

        elif cmd == 'leftw':
            # val = 0 - 100
            self.speed_left = float(val) / 100.0
            update = True

        elif cmd == 'rightw':
            # val = 0 - 100
            self.speed_right = float(val) / 100.0
            update = True

        elif cmd == 'motor_stop':
            self.cli.stop_all_motors()
            self.speed = self.steering = 0.0
            self.speed_left = self.speed_right = 0.0
            self._drive_head(0.0)
            self._drive_lift(0.0)

        elif cmd == 'camera':
            if val == 'cozmo':
                self.cli.add_handler(pycozmo.event.EvtNewRawCameraImage, handle_camera_image, one_shot=True)
                time.sleep(0.3)
            elif val == 'raspi':
                res = subprocess.run(["raspistill", "-o", "/var/www/html/cozmo/camera2.jpg", "-rot", "270", "-w", "512", "-h", "360", "-t", "300"], stdout=subprocess.PIPE)

        elif cmd == 'face':
            self.set_cozmo_face(val)

        elif cmd == 'animation':
            self.cli.play_anim(val)

        if update:
            self._drive_wheels(self.speed_left, self.speed_right)


    def set_cozmo_face(self, face_mode = 'normal'):
        if ( face_mode == 'normal' ):
            f = pycozmo.procedural_face.ProceduralFace()
        elif ( face_mode == 'happy' ):
            f = pycozmo.procedural_face.ProceduralFace(
                left_eye = [0,0,1.0,1.0,0.0,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.0,0.0,0.0,0.0,0.0,0.5],
                right_eye = [0,0,1.0,1.0,0.0,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.0,0.0,0.0,0.0,0.0,0.5])
        elif ( face_mode == 'sad' ):
            f = pycozmo.procedural_face.ProceduralFace(
                left_eye = [0,0,1.0,1.0,0.0,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.0,0.0,0.9,0.0,0.0,0.0],
                right_eye = [0,0,1.0,1.0,0.0,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.0,0.0,0.9,0.0,0.0,0.0])
        elif ( face_mode == 'wink' ):
            f = pycozmo.procedural_face.ProceduralFace(right_eye = [0,0,1.0,0.1,0.0,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.0,0.0,0.0,0.0,0.0,0.0])
        elif ( face_mode == 'surprise' ):
            f = pycozmo.procedural_face.ProceduralFace(scale_y = 1.5)
        elif ( face_mode == 'lonly' ):
            f = pycozmo.procedural_face.ProceduralFace(scale_x = 0.2, scale_y = 0.2)
        elif ( face_mode == 'laugh' ):
            f = pycozmo.procedural_face.ProceduralFace(
                left_eye = [0,0,1.0,0.5,0.0,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.0,0.0,0.0,0.0,0.0,0.5],
                right_eye = [0,0,1.0,0.5,0.0,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.0,0.0,0.0,0.0,0.0,0.5])
        elif ( face_mode == 'sleepy' ):
            f = pycozmo.procedural_face.ProceduralFace(scale_y = 0.1)
        elif ( face_mode == 'angry' ):
            f = pycozmo.procedural_face.ProceduralFace(
                left_eye = [0,0,1.0,1.0,0.0,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.0,0.0,0.4,0.0,0.0,0.0],
                right_eye = [0,0,1.0,1.0,0.0,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.0,0.0,0.4,0.0,0.0,0.0])
        else:
            f = pycozmo.procedural_face.ProceduralFace()

        im = f.render()

        # The Cozmo protocol expects a 128x32 image, so take only the even lines.
        np_im = np.array(im)
        np_im2 = np_im[::2]
        im2 = Image.fromarray(np_im2)

        self.cli.display_image(im2)

# end of class RCApp(object):


def handle_api_post(environ, start_response):

    response_header = [
            ("Content-type", "text/plain; charset=utf-8"),
            ("Access-Control-Allow-Origin", "http://rp3-01.local"),
            ("Access-Control-Allow-Methods", "GET,POST,OPTIONS"),
            ("Access-Control-Allow-Credentials", "true"),
            ("Access-Control-Allow-Headers", "Content-Type,Accept"),
        ]
    response_header_jpg = [
            ("Content-type", "image/jpeg"),
            ("Access-Control-Allow-Origin", "http://rp3-01.local"),
            ("Access-Control-Allow-Methods", "GET,POST,OPTIONS"),
            ("Access-Control-Allow-Credentials", "true"),
            ("Access-Control-Allow-Headers", "Content-Type,Accept"),
        ]

    msg = build_json_from_robot_state()

    request_method = environ.get('REQUEST_METHOD')

    if request_method == "POST":

        try:
            request_size = int(environ.get('CONTENT_LENGTH', 0))
            wsgi_input = environ.get('wsgi.input')
            request_body = wsgi_input.read(request_size)
            json_body = json.loads(request_body)
            app._handle_input(json_body['command'], json_body['value'])

        except:
            print( 'illegal request body')
            start_response("400 Bad Request", response_header)

        else:
            start_response("200 OK", response_header)

    elif request_method == "GET":
        path_info = environ.get('PATH_INFO')
#        print( 'path_info : ', path_info)

        img = io.BytesIO()
        app.latest_image.save(img, "JPEG")
        img = img.getvalue()

        if path_info == '/camera.jpg':
            pass

        start_response("200 OK", response_header_jpg)

        return [img]

    elif request_method == "OPTIONS":
#        print( 'OPTIONS request')
        start_response("200 OK", response_header)
    else:
        print( 'illegal request method', request_method)
        start_response("501 Not Implemented", response_header)

    return [msg.encode("utf-8")]

def build_json_from_robot_state():

    pkt = app.latest_robot_state_pkt

    list = { \
        'timestamp': pkt.timestamp, \
        'pose_frame_id': pkt.pose_frame_id, 'pose_origin_id': pkt.pose_origin_id, \
        'pose_x': pkt.pose_x, 'pose_y': pkt.pose_y, 'pose_z': pkt.pose_z, \
        'pose_angle_rad': pkt.pose_angle_rad, 'pose_pitch_rad': pkt.pose_pitch_rad, \
        'lwheel_speed_mmps': pkt.lwheel_speed_mmps, 'rwheel_speed_mmps': pkt.rwheel_speed_mmps, \
        'head_angle_rad': pkt.head_angle_rad, 'lift_height_mm': pkt.lift_height_mm, \
        'accel_x': pkt.accel_x, 'accel_y': pkt.accel_y, 'accel_z': pkt.accel_z, \
        'gyro_x': pkt.gyro_x, 'gyro_y': pkt.gyro_y, 'gyro_z': pkt.gyro_z, \
        'battery_voltage': pkt.battery_voltage, \
        'status': pkt.status, 'cliff_data_raw': pkt.cliff_data_raw, \
        'backpack_touch_sensor_raw': pkt.backpack_touch_sensor_raw, \
        'curr_path_segment': pkt.curr_path_segment, \
    }
    msg = json.dumps(list)

    return msg


def handle_camera_image(cli, image):
    del cli
    app.latest_image = image
    return


def camera_thread():
    while not app._stop:
        app.cli.add_handler(pycozmo.event.EvtNewRawCameraImage, handle_camera_image, one_shot=True)
        time.sleep(0.03)


def on_robot_state(cli, pkt: pycozmo.protocol_encoder.RobotState):
    del cli

    app.latest_robot_state_pkt = pkt

#    print("timestamp: {}, pose_frame_id: {}, pose_origin_id: {}"\
#        .format(pkt.timestamp, pkt.pose_frame_id, pkt.pose_origin_id))
#    print("pose: ({:.01f}, {:.01f}, {:.01f})-[{:.01f}, {:.01f}]"\
#        .format(pkt.pose_x, pkt.pose_y, pkt.pose_z, pkt.pose_angle_rad, pkt.pose_pitch_rad))
#    print("wheel: ({:.01f}, {:.01f})".format(pkt.lwheel_speed_mmps, pkt.rwheel_speed_mmps))
#    print("head: {:.01f}, lift:{:.01f})".format(pkt.head_angle_rad, pkt.lift_height_mm))
#    print("accel: ({:.01f}, {:.01f}, {:.01f}), gyro: ({:.01f}, {:.01f}, {:.01f})"\
#        .format(pkt.accel_x, pkt.accel_y, pkt.accel_z, pkt.gyro_x, pkt.gyro_y, pkt.gyro_z))
#    print("Battery level: {:.01f} V".format(pkt.battery_voltage))
#    print("status: {}, cliff: {}, backpack_touch: {}, curr_path: {}"\
#        .format(pkt.status, pkt.cliff_data_raw, pkt.backpack_touch_sensor_raw, pkt.curr_path_segment)) 


def on_robot_poked(cli, pkt: pycozmo.protocol_encoder.RobotPoked):
    del cli, pkt
    print("Robot poked.")


# stop logging ouput of simple server
class NoLoggingWSGIRequestHandler(WSGIRequestHandler):
    def log_message(self, format, *args):
        pass


def parse_args():
    """ Parse command-line arguments. """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-v', '--verbose', action='store_true', help='verbose')
    args = parser.parse_args()
    return args

def main():
    # Parse command-line.
    args = parse_args()

    # Configure logging.
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        format="%(asctime)s.%(msecs)03d %(name)-15s %(levelname)-8s %(message)s",
        datefmt='%Y-%m-%d %H:%M:%S',
        level=level)

    # Create application object.
    res = app.init()
    if res:
        app.run()
        app.term()


if __name__ == '__main__':
    app = RCApp()
    main()
