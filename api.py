from flask import Flask, request, Response
from flask_restful import Resource, Api

import json
import RPi.GPIO as GPIO
from motor import MotorIf as Motor
from accelerometer import Accelerometer as A

import thread
import time
from PID import PID

# initial configuration
GPIO.setmode(GPIO.BOARD)
GPIO.setup(11,GPIO.OUT)

# max speed = 100
motors = {'L': {'speed': 0 , 'dir': 'FORWARD' },
          'R': {'speed': 0 , 'dir': 'FORWARD' } }

mL = Motor('Left', 33,35,37)
mR = Motor('Right', 36,38,40)
mL.set_direction('FORWARD')
mR.set_direction('FORWARD')
mR.set_speed(50)
mL.set_speed(50)
acc = A(0x68)

m = {'L':mL,'R':mR}

exitFlag = 0

# first PID loop will try to set speed
# second PID loop will try to set angle

pid = { 'pid_speed' : PID(2,.5,0),
        'pid_angle' : PID(2,.5,0) }

        
def pid_thread():
    real_speed = 0
    while not exitFlag:
        rotation = acc.accelerometer()
        print "%f,%f\n" % rotation
        setPoint_Speed = (motors['L']['speed'] + motors['R']['speed'])/2.0
        pid['pid_speed'].SetPoint = setPoint_Speed
        pid['pid_speed'].update(real_speed)
        pid['pid_angle'].SetPoint = pid['pid_speed'].output    
        # y angle
        real_angle = rotation[1]
        print 'Angle set point: ', pid['pid_angle'].SetPoint, 'Real angle: ', real_angle 
        pid['pid_angle'].update(real_angle)
        real_speed = pid['pid_angle'].output
        
        # process
        if real_speed > 0:
            dir = 'FORWARD'
        else:
            dir = 'BACKWARD'
        print 'Speed set point', setPoint_Speed, 'Real_speed', real_speed
        speed = abs(real_speed)
        if speed > 100:
            speed = 100
        lSpeed = speed
        rSpeed = speed
        m['L'].set_direction(dir)
        m['R'].set_direction(dir)
        m['L'].set_speed(lSpeed)
        m['R'].set_speed(rSpeed)

thread.start_new_thread(pid_thread,())    

class MotorMgr(Resource):
    def get(self, motor):
        return Response(json.dumps(motors[motor]),mimetype='text/json')

    def put(self, motor):
        if 'dir' in request.form.keys():
            dir = request.form['dir']
            motors[motor]['dir'] = dir
            m[motor].set_direction(dir)
        if 'speed' in request.form.keys():
            speed = int(request.form['speed'])
            motors[motor]['speed'] = speed
            m[motor].set_speed(speed)
        return Response(json.dumps(motors[motor]),mimetype='text/json')

class LEDMgr(Resource):
    def get(self, state):
        if state == 'on':
            GPIO.output(11,True)
        else:
            GPIO.output(11,False)    
        return Response(json.dumps({"status": "ok"}),mimetype='text/json')
        
        
if __name__ == '__main__':
    try:
        app = Flask(__name__)
        api = Api(app)
        
        api.add_resource(MotorMgr, '/motor/<string:motor>')
        api.add_resource(LEDMgr, '/led/<string:state>')
        
        app.run(host='0.0.0.0', debug=True)
        GPIO.cleanup()
    except KeyboardInterrupt:
        exitFlag = 1
    
    GPIO.cleanup()
