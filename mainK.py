import bpy
import random
import math
import time
import os
#import numpy as np
#import matplotlib.pyplot as plt
#from scipy.optimize import fsolve

G = 6.67408*math.pow(10, -11) #m^3kg^-1s^-2 (Gravitational constant)
Mearth = 5.972*math.pow(10, 24) #kg (mass of earth)

Re = 6371 #km (radius of earth)
framerate = 24 

random.seed(time.time())

vstart=2
rstart = 1

pLow = 88*60
pHigh = 127*60

nMin = 4
nMax = 10

massMin = 1000 #kg
massMax = 10000 #kg

sizeScale = 100000 #scale down linear distances

collideScale = 100000 #scales likelyhood of collisions


def rrange(min, max):
    return random.random()*(max-min)+min

class CollisionObject:
    mesh = None
    object = None
    vel = (0, 0, 0)
    loc = (0, 0, 0)
    spawned = False
    hidden = False    
    immune = 0
    mass = 0

    X = (0, 0, 0) #unit vetors for the projected plane
    Y = (0, 0, 0)
    Z = (0, 0, 0)
    P = None
    e = None
    alpha0 = 0
    gamma = 0
    E_M = {None:None}
    a=0

    t = 0
    
    def __init__(self, loc=(None, None, None), mass=None, vel=(None, None, None)):
        self.spawn(loc, mass, vel)

    def createOrbitR(self):
        self.P=rrange(pLow,pHigh)
        self.e=rrange(0,0.5)
        self.alpha0 = rrange(0,2*math.pi)
        self.t0 = rrange(0,self.P)     
        self.a = pow((G*Mearth)*pow(self.P,2)/(4*math.pi*math.pi),(1/3))
        self.createNormal(rrange(-1,1),rrange(-1,1),rrange(-1,1))
        

        # print("start")
        # print("p",self.P,"e",self.e,"alpha0",self.alpha0,"t0",self.t0,"a",self.a,self.X,self.Y,self.Z)
        
        # self.getCartLoc()
         
        # self.createOrbit()
        # print("end")
        # print("p",self.P,"e",self.e,"alpha0",self.alpha0,"t0",self.t0,"a",self.a,self.X,self.Y,self.Z)

    def createNormal(self,A,B,C):
        self.Z = self.normalize([A,B,C])
        self.X = self.normalize(self.cross([0,1,0],self.Z))
        self.Y = self.normalize(self.cross(self.Z,self.X))
        
    def normalize(self,r):
        len = math.sqrt(pow(r[0],2)+pow(r[1],2)+pow(r[2],2))
        
        return[r[0]/len, r[1]/len, r[2]/len]
    
    
    def cross(self,A,B):
        x = (A[1]*B[2] - A[2]*B[1])
        y = (A[2]*B[0] - A[0]*B[2])
        z = (A[0]*B[1] - A[1]*B[0])
        
        return(x,y,z)
        
    def createOrbit(self):
        v = self.vel
        r = self.loc
        
        A = (r[2]*v[1] - r[1]*v[2])*(r[0]*v[1] - r[1]*v[0])
        B = (r[2]*v[0] - r[0]*v[2])*(r[1]*v[0] - r[0]*v[1])
        C = (r[0]*v[1] - r[1]*v[0])*(r[1]*v[0] - r[0]*v[1])
        

        
        self.createNormal(A,B,C)
        
        #Theta is the clockwise angle from x, Phi is the clockwise angle from y
       
        # self.phi = math.atan2((r[2]*v[1] - r[1]*v[2]),v[0]*r[1]-v[1]*r[0]) + math.pi
        
        # self.phi = math.atan2(r[2] - v[2]*v[1]/r[1],r[0] - v[0]*v[1]/r[1]) 
        
        # self.theta = math.atan2(r[2] - v[2]*v[0]/r[0],r[1] - v[1]*v[0]/r[0]) 
        
        # self.theta = math.atan2(math.cos(self.phi)*r[2] + math.sin(self.phi)*r[0], r[1])

        r2 = pow(r[0],2) + pow(r[1],2) + pow(r[2],2)
        rMag=math.sqrt(r2)
        v2 = pow(v[0],2) + pow(v[1],2) + pow(v[2],2)
        w2 = r2*v2
        
        # print("out",rMag,math.sqrt(v2))

        EperM = v2/2 - G*Mearth/rMag
        
        self.e = math.sqrt(EperM*2*w2/pow(G*Mearth,2) + 1) #eccentricity

        # print(self.e)
        
        if(self.e > 0.9):
            self.despawn()
            return
        
        
        
        rm = (math.sqrt(pow((G*Mearth),2) + 2*EperM*r2*v2)-G*Mearth)/(2*EperM)

        self.a = rm/(1-self.e)
        
        self.P = math.sqrt(pow(self.a,3)*4*math.pi*math.pi/(G*Mearth)) #Orbital period
    
    
        x = r[0]
        y = r[1]
        z = r[2]
        
        
        arg = ((self.a*(1-pow(self.e,2))/rMag)-1)/self.e
        if(abs(arg) > 1):
            arg = 1
        
        self.alpha0 = math.acos(arg)
           
        E = 2*math.atan(math.sqrt((1-self.e)*pow(math.tan(self.alpha0/2),2)/(1+self.e)))

        self.t0 = (E - self.e*math.sin(E))*2*math.pi/self.P
        
    def Efun(self,E,M):
        return E-self.e*math.sin(E) - M
    
    def getE(self,M):
        M = round(M,8)
        if M in self.E_M :
            return self.E_M[M]
        
        if (self.e > 0.8):
            E = math.pi
        else:
            E = M
 
        while abs(self.Efun(E,M)) > 0.01:
            E = E - (E - self.e*math.sin(E) - M)/(1-self.e*math.cos(E))

        self.E_M[M] = E
        return E
        
    def getOrbitPos(self):
        
        t = (self.t-self.t0)%self.P
        
        M = (t)*2*math.pi/self.P

        E = self.getE(M)
        
        
        alpha = 2*math.atan2(math.sqrt((1+self.e)/(1-self.e))*math.tan(E/2),1)
        dist = self.a*(1-self.e*math.cos(E))
        
        return (dist,alpha)
    
    def getCartLoc(self):

        pos = self.getOrbitPos()
        
        x0 = pos[0]*math.cos(pos[1]-self.alpha0)
        y0 = pos[0]*math.sin(pos[1]-self.alpha0)


        vel2 = G*Mearth*(2/pos[0] - 1/self.a)
        
       

        b = self.a*math.sqrt(1-pow(self.e,2))

        c = math.sqrt(pow(self.a,2) - pow(b,2))
        
        if(y0 ==0):
            vx0 = 0
            vy0 = math.sqrt(vel2)*x0/abs(x0)
        elif(x0 == 0):
            vx0 = -math.sqrt(vel2)*y0/abs(y0)
            vy0 = 0
        else:
            beta = -pow(b/self.a,2)*(x0+c)/y0
            vx0 = -math.sqrt(vel2/(1+pow(beta,2)))*y0/abs(y0)
            vy0 = beta*vx0
   
        # print("in",math.sqrt(pow(vx0,2) + pow(vy0,2)),math.sqrt(pow(x0,2) + pow(y0,2)))
        
        vx = self.X[0]*vx0 + self.Y[0]*vy0
        vy = self.X[1]*vx0 + self.Y[1]*vy0
        vz = self.X[2]*vx0 + self.Y[2]*vy0
        
        self.vel = (vx,vy,vz)
        
     
        x = self.X[0]*x0 + self.Y[0]*y0
        y = self.X[1]*x0 + self.Y[1]*y0
        z = self.X[2]*x0 + self.Y[2]*y0
        
        self.loc = (x,y,z)
        
        # print("out",math.sqrt(pow(vx,2) + pow(vy,2) + pow(vz,2)),math.sqrt(pow(x,2) + pow(y,2) + pow(z,2)))
        
    def spawn(self, loc, mass, velocity):
        self.spawned = True
        self.immune = 10
        self.mesh = bpy.data.meshes.new_from_object(
            bpy.context.scene, 
            bpy.data.objects["CD"],
            True,
            'PREVIEW')
        self.object = bpy.data.objects.new("Object", self.mesh)
        bpy.context.scene.objects.link(self.object)
        
        if loc[0] is None or loc[1] is None or loc[2] is None:
            self.createOrbitR()
        else:
            self.loc = loc
            self.vel = velocity
            self.createOrbit()
        
        self.setLocation()       
            
        if mass is None:
            self.setMass(rrange(massMin, massMax))
        else:
            self.setMass(mass)
            
        self.object.hide = True
        self.object.hide_render = True
        self.object.keyframe_insert(data_path="hide", frame=bpy.context.scene.frame_current-1)  
        self.object.keyframe_insert(data_path="hide_render", frame=bpy.context.scene.frame_current-1)         
        self.object.hide = False
        self.object.hide_render = False
        self.object.keyframe_insert(data_path="hide")
        self.object.keyframe_insert(data_path="hide_render")
    
    def hide(self):
        self.hidden = True
        self.object.hide = True
        self.object.hide_render = True
        self.object.keyframe_insert(data_path="hide")
        self.object.keyframe_insert(data_path="hide_render")  
    
    def despawn(self):
        if self.spawned and self.object is not None:
            self.spawned = False
            self.object.hide = False
            self.object.select = True
            bpy.ops.object.delete()
    
    def getR2(self):
        if self.object is not None:
            loc = self.loc
            x = loc[0]
            y = loc[1]
            z = loc[2]
            return (x*x+y*y+z*z)
        return 0
        
    def getXYZ(self):
        loc = self.loc
        return loc
        
    def setLocation(self):
        if self.object is not None:
            r = self.loc
            loc = (r[0]/sizeScale, r[1]/sizeScale, r[2]/sizeScale)
            self.object.location = loc
            self.object.keyframe_insert(data_path="location")            
    
    def getScale(self):
        if self.object is not None:
            return self.object.scale[1]
            
    def setScale(self, scale):
        
        if scale > ScaleMax:
            scale = ScaleMax
        if scale < ScaleMin:
            scale = ScaleMin
           
        if self.object is not None:
            self.object.scale = (scale, scale, scale)
            
    def getMass(self):
        if self.object is not None:
            return self.mass
        
    def setMass(self, mass):
        if self.object is not None:
            self.mass = mass
            self.setScale(ScaleFactor*density/mass)
    
    def _tick(self, rewind=False):
        if self.hidden:
            return
        if rewind:
            print("Rewind not implemented")
            return
        if self.immune > 0:
            self.immune -= 1
            
        dt = 100

        self.t = self.t+dt

        self.getCartLoc()
        self.setLocation()
        
                
    def tick(self, ticks):
        if not self.spawned:
            return
        if ticks == 0:
            pass
        elif ticks < 0:
            print("Rewind not implemented")
        else:
            for i in range(ticks):
                self._tick()

cb = []    
allcb = []
last_frame = 0

def frame_change_handler(scene):
    global last_frame
    frame = scene.frame_current
    if frame == scene.frame_end:
        bpy.ops.screen.animation_cancel(restore_frame=False)
        bpy.app.handlers.frame_change_pre.clear()
        global started
        started = False
        closeFile()
        return
    dframe = frame-last_frame
    
    for i in range(len(cb)):
        cb[i].tick(dframe)
        
    deli = []
    delk = []
    # very inefficient N^N collision checking
    for i in range(len(cb)):
       for k in range(len(cb)-i):
          if i != k:
             checkCollision(cb[i], cb[k])
             
    sizes = []
    for i in range(len(cb)):
        if not cb[i].hidden:
            sizes.append(str(cb[i].getScale()))
             
    fileWrite("%d, %d, %s" % (frame, len(sizes), ' ,'.join(sizes)))
                        
    last_frame = frame

def checkCollision(a, b):
    if a.hidden or b.hidden or a.immune > 0 or b.immune > 0:
        return False
    
    r1 = a.getXYZ()
    r2 = b.getXYZ()
    
    v1 = a.vel
    v2 = b.vel

    vx1 = v1[0]
    vy1 = v1[1]
    vz1 = v1[2]
    
    vx2 = v2[0]
    vy2 = v2[1]
    vz2 = v2[2]
    
    x1 = r1[0]
    y1 = r1[1]
    z1 = r1[2]
    
    x2 = r2[0]
    y2 = r2[1]
    z2 = r2[2]
    
    d = math.pow(x2-x1,2) + math.pow(y2-y1,2) + math.pow(z2-z1,2)
    d = math.sqrt(d)
    
    s1 = a.getScale()
    s2 = b.getScale()
    if s1 is None or s2 is None:
        return False
    
    s = collideScale*(s1+s2)/2
    
    if d < s:
        print("boom")
        
        # print(r1,v1)
        # print(r2,v2)
    
        # collision happened.       
        
        # both objects are deleted
        a.hide()
        b.hide()
        
        N = random.randint(nMin, nMax)
    
        m1 = a.getMass() 
        m2 = b.getMass()
        
        Mtot = m1 + m2
        
        pxTot = vx1*m1 + vx2*m2
        pyTot = vy1*m1 + vy2*m2
        pzTot = vz1*m1 + vz2*m2
        
        Mtot2 = 0
        
        pxTot2 = 0
        pyTot2 = 0
        pzTot2 = 0
        
        ms = []
        vxs = []
        vys = []
        vzs = []


        
        for i in range(0,N-1):
            ms.append(abs(random.uniform(0.5*Mtot/N,1.5*Mtot/N)))
            vxs.append(random.gauss((vx1 + vx2)/N,(vx1 + vx2)/(3*N)))
            vys.append(random.gauss((vy1 + vy2)/N,(vy1 + vy2)/(3*N)))
            vzs.append(random.gauss((vz1 + vz2)/N,(vz1 + vz2)/(3*N)))
            
        for i in range(0,N-1):
            Mtot2  += ms[i]
            
        for i in range(0,N-1):
            ms[i]  *= Mtot/Mtot2
            
        for i in range(0,N-1):
            pxTot2 += vxs[i]*ms[i]
            pyTot2 += vys[i]*ms[i]
            pzTot2 += vzs[i]*ms[i] 
		

        for i in range(0,N-1):


            vxs[i] *= pxTot/(pxTot2)
            vys[i] *= pyTot/(pyTot2)
            vzs[i] *= pzTot/(pxTot2)
            

            
            obj = CollisionObject(((x1+x2)/2,(y1+y2)/2,(z1+z2)/2), ms[i], (vxs[i], vys[i], vzs[i]))
            
            cb.append(obj)
            allcb.append(obj)

#        pxTot2 = 0
#        mTot2 = 0

#        for i in range(0,N-1):
#            pxTot2 += vxs[i]*ms[i]
#            mTot2 += ms[i]

        return True
    return False
    
 
        

cb = []    
last_frame = 0

started = False

      
Rmin = 10
Rmax = 20

ScaleFactor = 10
ScaleMin = 1
ScaleMax = 10

Me=1
density = 132 #kg/m^3 - based on https://en.wikipedia.org/wiki/Envisat

def strTime():
    return time.strftime("%y/%m/%d %H:%m:%S")

def fileWrite(str):
    global outputfilename
    global filehandle
    if filehandle is not None:
        try:
            filehandle.write("%s\n" % str)
        except Exception as e:
            print(str(e))
            
def openFile():
    global outputfilename
    global filehandle
    if filehandle is None:
        try:
            filehandle = open(outputfilename, "a")
        except Exception as e:
            print(str(e))
            filehandle = None
            
def closeFile():
    global filehandle
    if filehandle is not None:
        try:
            filehandle.close()
            filehandle = None
        except Exception as e:
            print(str(e))

outputfilename = "1.csv"
filehandle = None
class KesslerSyndromeStart(bpy.types.Operator):
    bl_idname = "ks.start"
    bl_label = "Start"
    
    def invoke(self, context, event):
        global last_frame
        global cb
        global allcb
        global started
        
        if started:
            return {"FINISHED"}
        started = True
        
        global Rmin
        Rmin = context.scene.Rmin
        global Rmax
        Rmax = context.scene.Rmax
        global ScaleMin
        ScaleMin = context.scene.ScaleMin
        global ScaleMax
        ScaleMax = context.scene.ScaleMax
        global ScaleFactor
        ScaleFactor = context.scene.ScaleFactor
        global Me
        Me = context.scene.Me
        global density
        density = context.scene.density
        
        global outputfilename
        outputfilename = context.scene.filename
        outputfilename = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', outputfilename)

        openFile()
        fileWrite("# [%s] Started simulation of %d objects" % (strTime(), context.scene.number_of_objects))
        fileWrite("# time(frame), num of objects, sizes of objects ...")

        
        bpy.ops.screen.frame_jump(1)
        
        for i in range(len(allcb)):
            allcb[i].despawn()        
        allcb = []
        cb = []    
        
        for i in range(context.scene.number_of_objects):
            cb.append(CollisionObject())
            allcb.append(cb[i])
            
        bpy.app.handlers.frame_change_pre.clear()
        bpy.app.handlers.frame_change_pre.append(frame_change_handler)

        
        bpy.ops.screen.animation_play()
        return {"FINISHED"}
    
class KesslerSyndromeContinue(bpy.types.Operator):
    bl_idname = "ks.continue"
    bl_label = "Continue"
    
    def invoke(self, context, event):
        bpy.app.handlers.frame_change_pre.clear()
        bpy.app.handlers.frame_change_pre.append(frame_change_handler)
        bpy.ops.screen.animation_play()
        
        openFile()
        return {"FINISHED"}
        
class KesslerSyndromeStop(bpy.types.Operator):
    bl_idname = "ks.stop"
    bl_label = "Stop"
    
    def invoke(self, context, event):
        global started
        started = False
        bpy.app.handlers.frame_change_pre.clear()
        bpy.ops.screen.animation_cancel(restore_frame=False)
        closeFile()
        return {"FINISHED"}
    
class KesslerSyndromeClear(bpy.types.Operator):
    bl_idname = "ks.clear"
    bl_label = "Clear"
    
    def invoke(self, context, event):
        global cb
        global allcb
        for i in range(len(allcb)):
            allcb[i].despawn()
        cb = []
        allcb = []
        return {"FINISHED"}

class KSPanel(bpy.types.Panel):
    bl_label = "Kessler Syndrome"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"
 
    def draw(self, context):
        col1 = self.layout.column(align=True)
        col1.prop(context.scene, "number_of_objects", slider=True)
        r1 = col1.row(align=True)
        r1.prop(context.scene, "Rmin", slider=True)
        r1.prop(context.scene, "Rmax", slider=True)
        r2 = col1.row(align=True)       
        r2.prop(context.scene, "ScaleMin", slider=True)
        r2.prop(context.scene, "ScaleMax", slider=True)
        r3 = col1.row(align=True)   
        r3.prop(context.scene, "ScaleFactor", slider=True)
        col1.prop(context.scene, "Me", slider=True)
        col1.prop(context.scene, "density", slider=True)
        
        colf = self.layout.column(align=True)
        colf.prop(context.scene, "filename")
        
        colo = self.layout.column(align=True)       
        colo.operator("ks.start")
        colo.operator("ks.continue")
        colo.operator("ks.stop")
        colo.operator("ks.clear")

def register():
    bpy.utils.register_class(KSPanel)
    bpy.utils.register_class(KesslerSyndromeStart)
    bpy.utils.register_class(KesslerSyndromeContinue)
    bpy.utils.register_class(KesslerSyndromeStop)
    bpy.utils.register_class(KesslerSyndromeClear)
    bpy.types.Scene.number_of_objects = bpy.props.IntProperty \
      (
        name = "N",
        description = "Number of objects to generate",
        default = 10,
        min = 0
      )      
    bpy.types.Scene.Rmin = bpy.props.FloatProperty \
      (
        name = "Rmin",
        description = "Minimum radius to generate objects",
        default = 10,
        min = 0
      )
    bpy.types.Scene.Rmax = bpy.props.FloatProperty \
      (
        name = "Rmax",
        description = "Maximum radius to generate objects",
        default = 20,
        min = 0
      )
    bpy.types.Scene.ScaleMin = bpy.props.FloatProperty \
      (
        name = "ScaleMin",
        description = "Minimum scale to generate objects",
        default = ScaleMin,
        min = 0
      )
    bpy.types.Scene.ScaleMax = bpy.props.FloatProperty \
      (
        name = "ScaleMax",
        description = "Maximum scale to generate objects",
        default = ScaleMax,
        min = 0
      )
    bpy.types.Scene.ScaleFactor = bpy.props.FloatProperty \
      (
        name = "ScaleFactor",
        description = "How much larger does the object appear?",
        default = 100,
        min = 0
      )
    bpy.types.Scene.Me = bpy.props.FloatProperty \
      (
        name = "Me",
        description = "Mass of earth",
        default = 1, #5.972*math.pow(10, 24)
        min = 0
      )
    bpy.types.Scene.density = bpy.props.FloatProperty \
      (
        name = "density",
        description = "Density of objects",
        default = 100,
        min = 0
      )
      
    bpy.types.Scene.filename = bpy.props.StringProperty \
      (
        name = "Output File",
        description = "The file to output data to",
        default = "1.csv"
      )
      
def unregister():
    bpy.utils.unregister_class(KSPanel)
    bpy.utils.unregister_class(KesslerSyndromeStart)
    bpy.utils.unregister_class(KesslerSyndromeContinue)
    bpy.utils.unregister_class(KesslerSyndromeStop)
    bpy.utils.unregister_class(KesslerSyndromeClear)
    
if __name__ == "__main__" :
    register()
