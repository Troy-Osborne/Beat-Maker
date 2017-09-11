from __future__ import division
from math import cos,sin,tanh,pi,sqrt
from matplotlib import pyplot as plt
from random import random
from struct import pack,unpack
import wave
tau=2*pi
hp=pi/2
saw=lambda val:((val+pi)%tau-pi)/pi
tri=lambda val:abs((val-pi/2)%tau-pi)*2/pi-1
trap=lambda steep:lambda val:max(-1,min(1,tri(val)*steep))
sqr=lambda val:1 if val%tau <pi else -1
def inwhich(x,l):
	if x<=0:
		return None
	for i in range(len(l)):
		if x < l[i][0]:
			return (l[i-1],l[i])
	return None

def getpos(a,b,x):
	return a[1]+((x-a[0])/(b[0]-a[0]))*(b[1]-a[1])

def getposh(a,b,x):
	return (x-a)/(b-a)

def between(x,a,b):
	return x>=a and x<b

def posin(x,p):
	if p ==None:
		return 0
	return getpos(p[0],p[1],x)

def pointmapf(sharpness,*points):
	return lambda x:posin(x,inwhich(x,points))**sharpness
	
def pointmap(sharpness,*points):
	return [posin(x/44100,inwhich(x/44100,points))**sharpness for x in range(44100)]
	
def pointsmanual(unpackedbytes):
	lastpos=0
	out=[(0,0)]
	for i in range(int(len(unpackedbytes)/2)):
		xpos=lastpos+unpackedbytes[i*2]/512
		ypos=unpackedbytes[i*2+1]/256
		out.append((xpos,ypos))
		lastpos=xpos
	return pointmap(1,*out)
	

def sharpen(wave,amount):
	return lambda x:abs(wave(x))**amount*sqr(x)

def AR(A,R,sharpness=1):
	return pointmap(sharpness,(0,0),(A,1),(A+R,0))
	
def ADSR(A,D,S,R,sharpness=1):
	return pointmap(sharpness,(0,0),(A,1),(A+D,S),(A+D+R,0))

def AHDSR(A,H,D,S,R,sharpness=1):
	return pointmap(sharpness,(0,0),(A,1),(A+H,1),(A+H+D,S),(A+H+D+R,0))

def ADSHR(A,D,S,H,R,sharpness=1):
	return pointmap(sharpness,(0,0),(A,1),(A+D,S),(A+D+H,S),(A+D+H+R,0))

def ADSDSR(A,D,S,D2,S2,R,sharpness=1):
	return pointmap(sharpness,(0,0),(A,1),(A+D,S),(A+D+D2,S2),(A+D+D2+R,0))

Waves={
	"sin":sin,
	"saw":lambda val:((val+pi)%tau-pi)/pi,
	"tri":lambda val:abs((val-pi/2)%tau-pi)*2/pi-1,
	"sqr":lambda val:1 if val%tau <pi else -1,
	"trap":lambda steepness:lambda val:max(-1,min(1, steepness*(abs((val-pi/2)%tau-pi)*2/pi-1))),
	"trap2":lambda val:max(-1,min(1, 2*(abs((val-pi/2)%tau-pi)*2/pi-1))),
	"trap4":lambda val:max(-1,min(1, 4*(abs((val-pi/2)%tau-pi)*2/pi-1))),
	"tanhm":lambda steepness:lambda x: (lambda p:tanh(p*steepness)-tanh(p-steepness-pi*steepness)+tanh(p*steepness-pi*steepness*2))(x%(2*pi)),
	"tanhm1":lambda x: (lambda p:tanh(p)-tanh(p-pi)+tanh(p-pi*2))(x%(2*pi)),
	"tanhm4":lambda x: (lambda p:tanh(p*4)-tanh(p*4-pi*4)+tanh(p*4-pi*4*2))(x%(2*pi)),
	"flat":lambda val:0
}

mid=lambda a,b,r:(r-a)/(b-a)
samplerate=44100
bpm=120
bps=bpm/60
spb=samplerate/bps
##Kick(Envelope,PitchEnvelope,[WaveSequence])
#####FX #####


square=lambda x:map(lambda y:y**2,x)
def delay(beats=.25,gain=.7,repeats=4):
	def inner(l):
		o=[]
		overshoot=beats*repeats
		total=sum([gain**x for x in range(repeats)])
		for i in range(len(l)+overshoot*spb):
			val=0
			for j in range(repeats):
				pos=i-(j*spb*beats)
				if pos<len(l)-1 and pos >=0:
					val+=l[i-int((j*spb*beats))]*gain**j
			o.append(val/total)
		return o
	return inner
	
				
######################
def wavesequence(waves,repeats="Reverse"): #Wave,Time in Beats
	start=0
	end=waves[-1]
	print end
	def inner(position):
		position=position%end
		lastpos=0
		lastwave=waves[0][0]
		for i in waves[:-1]:
			if position/spb <i[1]:
				m=mid(lastpos,i[1],position/spb)
				return lambda x:(1-m)*lastwave(x)+m*i[0](x)
			lastpos=i[1]
			lastwave=i[0]
		return i[0]
	return inner
	
def bytetoline(B):
	Line=[normal,tanhp,circlebr,circletl][B%4]
	B=B>>2
	Start=(B%8)/8
	B=B>>3
	End=B/8
	return lambda x:Start+Line(x)*(End-Start)

def bytetolayerfunction(B):
	F=[add,subtract,times,difference][B%4]
	return F

WS=wavesequence([(Waves["sin"],0),(Waves["tri"],.5),(Waves["saw"],1),(Waves["sqr"],1.5),(Waves["saw"],2),(Waves["trap"](1.2),3.5),4])

WS2=wavesequence([(Waves["sin"],0),(Waves["tri"],.5),(Waves["tanhm"](2),2),(Waves["trap"](2),3.5),4])

def LGEtoEnv(unpackedbytes):
	#Byte1=Type ##Odd Types = Wave Seed, Even Types =Pointmap
	#Byte2:32 = Env
	Type="Wave" if unpackedbytes[0]%8<3 else "PointMap"
	if Type=="Wave":
		print "w"
		if unpackedbytes[1]%2==0:
			lines=map(bytetoline,unpackedbytes[2:8])
			f=map(bytetolayerfunction,unpackedbytes[8:13])
			fx=map(lambda x:[delay(.25),delay(.125),delay(.5),square][x%4],unpackedbytes[13:16])
			return linewavehalf(lines[0],lines[1],lines[2],lines[3],lines[4],lines[5],f[0],f[1],f[2],f[3],f[4],fx[0],fx[1])
		elif unpackedbytes[1]%2==1:
			waves=map(lambda x:Waves[["sin","tri","saw","sqr","trap2","trap4","tanhm1","tanhm4"][x%8]],unpackedbytes[2:16])
			velocities=map(lambda x:x/256,unpackedbytes[16:30])
			fx=map(lambda x:[delay(.25),delay(.125),delay(.5),square][x%4],unpackedbytes[30:32])
			return sumwaveshalf(map(lambda x,y: (x,y),waves,velocities),fx)
	elif Type=="PointMap":
		print "pm"
		u=unpackedbytes[1]%32
		if u<16:
			if u<2:
				A=unpackedbytes[2]/256
				R=unpackedbytes[3]/256
				return AR(A,R)
			elif u<6:
				A=unpackedbytes[2]/256
				D=unpackedbytes[3]/256
				S=unpackedbytes[4]/256
				R=unpackedbytes[5]/256
				return ADSR(A,D,S,R)
			elif u<10:
				A=unpackedbytes[2]/256
				D=unpackedbytes[3]/256
				S=unpackedbytes[4]/256
				D2=unpackedbytes[5]/256
				S2=unpackedbytes[6]/256
				R=unpackedbytes[7]/256
				return ADSDSR(A,D,S,D2,S2,R)
			elif u<12:
				A=unpackedbytes[2]/256
				H=unpackedbytes[3]/256
				D=unpackedbytes[4]/256
				S=unpackedbytes[5]/256
				R=unpackedbytes[6]/256
				return AHDSR(A,H,D,S,R)
			else:
				A=unpackedbytes[2]/256
				D=unpackedbytes[3]/256
				S=unpackedbytes[4]/256
				H=unpackedbytes[5]/256
				R=unpackedbytes[6]/256
				return ADSHR(A,D,S,H,R)
		else:
			return pointsmanual(unpackedbytes[2:32])

#def Kick(Envelopes,PitchEnvelopes,wavesequence,Wiring="linear"):

#lines#
normal=lambda x:x
circletl=lambda x:sin(x*pi/2)
circlebr=lambda x:sin(3*pi/2+x*pi/2)+1
tanhp=lambda x:(tanh(tau*x-.5*tau)+1)/2
"""
plt.plot([circletl(i/100) for i in range(100)])
plt.plot([circlebr(i/100) for i in range(100)])
plt.plot([tanhp(i/100) for i in range(100)])
plt.show()"""
####lw fx
def add(a,b):
	return a+b

def subtract(a,b):
	return a-b

def difference(a,b):
	return abs(a-b)

def times(a,b):
	return a-b

#####	
def linesynth(line1,line2,line3,line4,line5,line6,function1,function2,function3,function4,function5,effect1,effect2,size=44100):
	return effect2(effect1([min(max(-1,function5(line6(i/size),function4(line5(i/size),function3(line4(i/size),function2(line3(i/size),function1(line2(i/size),line1(i/size))))))),1) for i in range(size)]))[:size-1]

def linewavehalf(line1,line2,line3,line4,line5,line6,function1,function2,function3,function4,function5,effect1,effect2,size=44100,symmetry=True):
	l=linesynth(line1,line2,line3,line4,line5,line6,function1,function2,function3,function4,function5,effect1,effect2,int(size*2))
	if symmetry:
		return l[::4]+l[len(l)::-4]
	else:
		return l[::4]+map(lambda x:1-x,l[::4])
		
	
def linewave(line1,line2,line3,line4,line5,line6,function1,function2,function3,function4,function5,effect1,effect2,size=44100,symmetry=True):
	l=linesynth(line1,line2,line3,line4,line5,line6,function1,function2,function3,function4,function5,effect1,effect2,int(size))
	if symmetry:
		return l[::4]+l[len(l)::-4]+map(lambda x:-x,l[::4]+l[len(l)::-4])
	else:
		return l[::4]+map(lambda x:1-x,l[::4])+map(lambda y:-y,l[::4]+map(lambda x:1-x,l[::4]))
		
def sumwaves(waves,effects,size=44100): #wave=(func,magnitude)
	mag=sum(map(lambda x:x[1],waves))+.0001
	return [sum(map(lambda x:x[0](i/44100*pi*2),waves))/mag for i in range(size)]
	
def sumwaveshalf(waves,effects,size=44100): #wave=(func,magnitude)
	mag=sum(map(lambda x:x[1],waves))+.0001
	return [sum(map(lambda x:x[0](i/44100*pi),waves))/mag for i in range(size)]
#####
"""
plt.plot([WS(i)(i/44100*110*pi) for i in range(88200)])
#plt.plot(linewave(normal,tanhp,circletl,circlebr,normal,circlebr,add,add,times,times,subtract,square,delay(.5),symmetry=True))
plt.show()
"""
def RandomLGE(chromosones=32,bytesper=1):
	return "".join([pack("B",int(random()*256)) for i in range(chromosones)])

Genes=RandomLGE(1024)
UnpackedGenes=map(lambda x:unpack("B",x)[0],Genes)
#EnvKick13_1=LGEtoEnv(UnpackedGenes[0:32])
#EnvKick13_2=LGEtoEnv(UnpackedGenes[32:64])
#EnvKick1234_1=LGEtoEnv(UnpackedGenes[64:96])
#EnvKick1234_2=LGEtoEnv(UnpackedGenes[96:128])
EnvBass_1=LGEtoEnv(UnpackedGenes[128:160])
#EnvMid_1=LGEtoEnv(UnpackedGenes[160:192])
#EnvRoll16_1=LGEtoEnv(UnpackedGenes[192:224])
#EnvRoll16_2=LGEtoEnv(UnpackedGenes[224:256])
def envtobeat(env,offset=0,expt=1):
	return lambda x:env[int(x*(4**expt)*bps+offset*44100)%44100]
def envtobeatseq(env,seq,offset=0,expt=1):
	def inner(x):
		sixteenth=int(((x*(4**expt)/spb+offset)))%16
		if seq[sixteenth]:
			return env[int((((x*(4**expt)/spb+offset))%1)*44100)]
		else: return 0
	return inner
		

	
"""
Kick1=envtobeat(EnvKick1234_1,0,0)
Kick2=envtobeat(EnvKick1234_2,0,0)"""
Bass=envtobeatseq(EnvBass_1,[False,True,True,True,False,False,True,True,False,True,True,True,True,False,True,False],0,1)
plt.plot([Bass(i) for i in range(spb)])
plt.show()
def MakeLine(Waves,VelocityEnvelopes,PitchEnvelopes,bars=1):
	VelocityEnvelopes=map(lambda x: (x[0],lambda y:x[1](y)*x[2]) ,VelocityEnvelopes)
	WavePositions=[0 for i in PitchEnvelopes]
	out=[]
	for i in range(int(spb*4*bars)):
		n=0
		posval=0
		for j in PitchEnvelopes: 
			VelocityCont=VelocityEnvelopes[j[0]]
			Velocity=VelocityCont[1](i)
			Wave,GroundFreq=Waves[VelocityCont[0]]
			Cents=j[2]
			Penv=j[1]
			WavePositions[n]+=(440*2**((GroundFreq+Penv(i)*Cents/100)/12))/44100
			posval+=Wave(i)(WavePositions[n])*Velocity
			n+=1
		out.append(posval)
	return out
	
def MakeLinePreview(Waves,VelocityEnvelopes,PitchEnvelopes,bars=1):	
	VelocityEnvelopes=map(lambda x: (x[0],lambda y:x[1](y)*x[2]) ,VelocityEnvelopes)
	WavePositions=[0 for i in PitchEnvelopes]
	out=[]
	for i in range(int(spb*4*bars/100)):
		n=0
		posval=0
		for j in PitchEnvelopes: 
			VelocityCont=VelocityEnvelopes[j[0]]
			Velocity=VelocityCont[1](i*100)
			Wave,GroundFreq=Waves[VelocityCont[0]]
			Cents=j[2]
			Penv=j[1]
			WavePositions[n]+=(440*2**((GroundFreq+Penv(i*100)*Cents/100)/12))/441
			posval+=Wave(i*100)(WavePositions[n])*Velocity
			n+=1
		out.append(posval)
	return out
"""

test=MakeLine([(WS2,12),(WS,12),(WS2,36)],
			[(0,Kick1,1),(1,Kick2,1),(1,Bass,1)],
				[(0,Kick1,2400),(1,Kick2,1200),(2,Bass,0)])
"""
def wavesave(l,name="test.wav"):
	w=wave.open(name,"wb")
	w.setparams((2,4,44100,0,'NONE',"not compressed"))
	for i in l:
		v=pack("<l",min(1,max(-1,i))*(2**31 -1))
		w.writeframes(v)
		w.writeframes(v)
	w.close()
"""

plt.plot(test)
plt.plot([Kick1(i) for i in range(spb*4)])
plt.plot([Kick2(i) for i in range(spb*4)])
plt.plot([Bass(i) for i in range(spb*4)])
plt.show()
wavesave(test)"""
