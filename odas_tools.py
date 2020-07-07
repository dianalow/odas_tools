import subprocess
import time
import threading
import json

'''
this class will launch an ODAS instance and provide functions to read streaming
output (currently set to "sound source tracking" in ODAS)
'''
class ReadODAS():
    def __init__(self):
        self.current_chunk=[]
        self.proc = subprocess.Popen(["modules/odas/bin/odaslive", "-c" ,
        "modules/odas/config/odaslive/respeaker_v2_commandline.cfg"],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)

        self.t = threading.Thread(target=self.output_reader, args=(self.proc,))
        self.t.start()

    def terminate(self):
        self.proc.terminate()
        try:
            self.proc.wait(timeout=0.2)
            #print('== subprocess exited with rc =', self.proc.returncode)
        except subprocess.TimeoutExpired:
            print('subprocess did not terminate in time')

        self.t.join()

    def output_reader(self,process):
        chunk=[]
        countlines=0
        for line in iter(process.stdout.readline, b''):
            countlines+=1
            chunk.append(line.decode("utf-8"))
            if countlines==9:
                self.current_chunk = chunk
                chunk=[]
                countlines=0

    def read_current(self):
        '''reformat odas chunk to proper json'''
        t0 = ''.join(self.current_chunk).strip('\n')
        t1 = json.loads(t0)
        ts = t1['timeStamp']
        non_zero_activity = 0
        tracks = {}
        tracks['sources']={}
        #print("Timestamp:",ts)
        for n,src_num in enumerate(t1['src']):
            if src_num['id'] != 0:
                #print("\t",src_num)
                non_zero_activity+=1
                a1 = self.calculate_angles(src_num)
                tracks['sources'][src_num['id']]=[a1.ev, a1.az, src_num['activity']]
                #print("\t","id:", src_num['id'], "; Elevation:",a1.ev,"; Azimuth:", a1.az, "; Activity:", src_num['activity']),
        tracks['num_sources']=non_zero_activity
        return(tracks)

    def calculate_angles(self,chunk):
        """ calculate_angles(chunk)

        calculates elevation and azimuth given a json-formatted chunk from ODAS
        """
        import math
        import collections

        Angles = collections.namedtuple("Angles", "ev az")
        x = float(chunk['x'])
        y = float(chunk['y'])
        z = float(chunk['z'])
        ev = round(90 - math.acos(z/math.sqrt(x*x+y*y+z*z))*180/math.pi)
        az = round(math.atan2(y,x)*180/math.pi)

        return(Angles(ev, az))

if __name__ == "__main__":
    odas = ReadODAS()
    for i in range(5):
        time.sleep(1)
        tracks=odas.read_current()
        print(tracks['num_sources'])
        print(tracks['sources'])
    odas.terminate()
