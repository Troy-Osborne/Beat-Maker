from __future__ import division
import sys
from math import sin,pi
from subprocess import Popen
#from Graph import ListToGraph
from BeatMaker import RandomLGE,LGEtoEnv,MakeLine,MakeLinePreview,envtobeat,envtobeatseq,wavesequence,Waves,wavesave
from struct import pack,unpack
from PIL import Image,ImageDraw
from time import time
from random import random
try:
    import pygtk
    pygtk.require("2.0")
except:
  	pass
try:
    import gtk
    import gtk.glade
except:
        sys.exit(1)
        
def midpoints(a,b,r):
	return (1-r)*a+r*b
	

samplerate=44100
bpm=95
bps=bpm/60
spb=samplerate/bps



def randwavseq():
	end=16
	n=0
	o=[]
	for i in range(int(random()*6)+2):
		wave=[Waves["sin"],Waves["tri"],Waves["saw"],Waves["sqr"],Waves["saw"],Waves["trap"](2),Waves["tanhm"](1),Waves["tanhm"](2)][int(random()*8)]
		o.append((wave,n))
		n+=int(random()*7+1)/4
	o.append(end)
	return wavesequence(o)
class BeatGTK:
	def __init__(self):
			self.rollinsts(None)
			self.Insts=[lambda x:sin(x),
			None,
			None,
			None,
			None,
			None]
			self.settings=[[1,0,False],
			[1,0,False],
			[1,pi,False],
			[1,0,False],
			[1,0,False],
			[1,0,False]  #volume,phaseshift,muted
			]
			#Set the Glade file
			self.gladefile = "GladeFiles/InstrumentAlign.glade"
			self.wTree = gtk.glade.XML(self.gladefile)
			self.vol1=self.wTree.get_widget("volslide1")
			self.vol2=self.wTree.get_widget("volslide2")
			self.vol3=self.wTree.get_widget("volslide3")
			self.vol4=self.wTree.get_widget("volslide4")
			self.vol5=self.wTree.get_widget("volslide5")
			self.vol6=self.wTree.get_widget("volslide6")
			self.pos1=self.wTree.get_widget("posslide1")
			self.pos2=self.wTree.get_widget("posslide2")
			self.pos3=self.wTree.get_widget("posslide3")
			self.pos4=self.wTree.get_widget("posslide4")
			self.pos5=self.wTree.get_widget("posslide5")
			self.pos6=self.wTree.get_widget("posslide6")
			self.RolButs=[
				self.wTree.get_widget("Rbutton1"),
				self.wTree.get_widget("Rbutton2"),
				self.wTree.get_widget("Rbutton3"),
				self.wTree.get_widget("Rbutton4"),
				self.wTree.get_widget("Rbutton5"),
				self.wTree.get_widget("Rbutton6")
			]
			self.depths=[
				self.wTree.get_widget("hscale1"),
				self.wTree.get_widget("hscale2"),
				self.wTree.get_widget("hscale3"),
				self.wTree.get_widget("hscale4"),
				self.wTree.get_widget("hscale5"),
				self.wTree.get_widget("hscale6")
			]
			self.PitchConts=[
				(self.wTree.get_widget("Pitch1"),self.wTree.get_widget("Cents1")),
				(self.wTree.get_widget("Pitch2"),self.wTree.get_widget("Cents2")),
				(self.wTree.get_widget("Pitch3"),self.wTree.get_widget("Cents3")),
				(self.wTree.get_widget("Pitch4"),self.wTree.get_widget("Cents4")),
				(self.wTree.get_widget("Pitch5"),self.wTree.get_widget("Cents5")),
				(self.wTree.get_widget("Pitch6"),self.wTree.get_widget("Cents6"))
			]
			self.images=[
				self.wTree.get_widget("image1"),
				self.wTree.get_widget("image2"),
				self.wTree.get_widget("image3"),
				self.wTree.get_widget("image4"),
				self.wTree.get_widget("image5"),
				self.wTree.get_widget("image6")
			]
			self.mainpreview=self.wTree.get_widget("mainpreview")
			### PITCH/VOL TOGGLE
			#Get the Main Window, and connect the "destroy" event
			self.window = self.wTree.get_widget("window1")
			self.PlayButton = self.wTree.get_widget("PlayButton")
			self.wTree.get_widget("Export").connect("clicked",self.MakeFile)
			for i in range(6):
				self.Roll(i+1)
			if (self.window):
					self.window.connect("destroy", self.NoReturn)
					self.wTree.get_widget("RollWaves").connect("clicked", self.rollinsts)
					for i in [self.pos1,self.pos2,self.pos3,self.pos4,self.pos5,self.pos6]:
							i.connect("value-changed", self.UpdateChannel)
					for i in self.RolButs:
							i.connect("clicked", self.RollButton)
					for i in [self.vol1,self.vol2,self.vol3,self.vol4,self.vol5,self.vol6]:
							i.connect("value-changed", self.UpdateChannel)
	def rollinsts(self,sender):
		self.WS=[randwavseq() for i in range(6)]
	def UpdateChannel(self,changed):
		Channel=changed.name[-1]
		t=changed.name[0]
		self.settings[int(Channel)-1][0]=self.__dict__["vol"+Channel].get_value()/100.0
		self.settings[int(Channel)-1][1]=self.__dict__["pos"+Channel].get_value()*pi
		self.DisplaySound(Channel)
	def DisplaySound(self,Channel):
		Channel=str(Channel)
		im=self.MakeGraph(int(Channel))
		im.save("./Images/"+Channel+".png")
		self.images[int(Channel)-1].set_from_file("./Images/"+Channel+".png")
	def getsequence(self,channel):
		return [self.wTree.get_widget("I"+str(channel+1)+"P"+str(i+1)).get_active() for i in range(16)]
	def DisplayMain(self):
		for i in range(6):
			self.settings[i][0]=self.__dict__["vol"+str(i+1)].get_value()/100.0
			self.settings[i][1]=self.__dict__["pos"+str(i+1)].get_value()*pi
		
		Waves=[(self.WS[0],-12),(self.WS[1],0),(self.WS[2],0),(self.WS[3],0),(self.WS[4],0),(self.WS[5],0)]
		Envs=[(i,envtobeatseq(self.Insts[i],self.getsequence(i),self.settings[i][1],self.depths[i].get_value()),self.settings[i][0]) if self.Insts[i] and not self.settings[i][2] else False for i in range(len(self.Insts))]
		Envs=filter(lambda x:x!=False,Envs)
		PEnvs=[(i[0],Envs[i[0]][1],self.PitchConts[i[0]][1].get_value() if self.PitchConts[i[0]][0].get_active() == False else 0) for i in Envs]
		print PEnvs
		line=MakeLinePreview(Waves,Envs,PEnvs)
		im=ListToGraph(line,resolution=(960,180))
		im.save("./Images/mainpreview.png")
		self.mainpreview.set_from_file("./Images/mainpreview.png")
		#wavesave(line)
	def MakeFile(self,sender):
		Waves=[(self.WS[0],-12),(self.WS[1],0),(self.WS[2],0),(self.WS[3],0),(self.WS[4],0),(self.WS[5],0)]
		Envs=[(i,envtobeatseq(self.Insts[i],self.getsequence(i),self.settings[i][1],self.depths[i].get_value()),self.settings[i][0]) if self.Insts[i] and not self.settings[i][2] else False for i in range(len(self.Insts))]
		Envs=filter(lambda x:x!=False,Envs)
		PEnvs=[(i[0],Envs[i[0]][1],self.PitchConts[i[0]][1].get_value() if self.PitchConts[i[0]][0].get_active() == False else 0) for i in Envs]
		line=MakeLine(Waves,Envs,PEnvs,bars=4)
		wavesave(line)
	def Return(self,sender):
		self.window.destroy()
		gtk.main_quit(sender)
	def NoReturn(self,sender):
		self.window.destroy()
		gtk.main_quit(sender)
	def BoxChange(self,changed):
		self.Update()
	def MakeGraph(self,Channel):
		return ListToGraph(self.Insts[int(Channel)-1],vol=self.settings[int(Channel)-1][0])
	def Roll(self,Channel):
		GEnv=RandomLGE(32)
		UGEnv=map(lambda x:unpack("B",x)[0],GEnv)
		GWave=RandomLGE(32)
		UGWave=map(lambda x:unpack("B",x)[0],GWave)
		Env=LGEtoEnv(UGEnv)
		self.Insts[Channel-1]=Env
		self.DisplaySound(Channel)
		self.DisplayMain()
	def RollButton(self,sender):
		Channel=int(sender.name[-1])
		self.Roll(Channel)
	
def ListToGraph(lst,high=1,low=-1,resolution=(120,40),vol=1):
	ll=len(lst)
	midy=resolution[1]/2
	im=Image.new("RGB",resolution,(0,0,0))
	dr=ImageDraw.Draw(im)
	val=0
	for x in range(resolution[0]):
		place=(x/resolution[0])*(len(lst)-1)
		iplace=int(place)
		lastval=val
		val=midy-lst[iplace]*midy*vol
		dr.line((x-1,lastval,x,val),fill=(255,255,255))
	del dr
	return im
		
        
"""
class ADSRGTK:
	def __init__(self):
			#Set the Glade file
			self.functiontext=None
			self.function=ADSR(25,25,.5,25)
			self.gladefile = "GladeFiles/InstrumentAlign.glade"  /8*
			self.wTree = gtk.glade.XML(self.gladefile)
			self.RB= self.wTree.get_widget("Return_Button")
			self.tableleft = self.wTree.get_widget("TableLeft")
			self.Atk=self.wTree.get_widget("spinbutton1")
			self.Dec=self.wTree.get_widget("spinbutton2")
			self.Sus=self.wTree.get_widget("spinbutton3")
			self.Rel=self.wTree.get_widget("spinbutton4")
			### PITCH/VOL TOGGLE
			#Get the Main Window, and connect the "destroy" event
			self.window = self.wTree.get_widget("MainWindow")
			self.Image = self.wTree.get_widget("ImgAdsr")
			self.PlayButton = self.wTree.get_widget("PlayButton")
			self.Image.set_from_file("GUI/Enveloper/Images/Envelope_None.jpg")
			self.Instrument=None
			self.Update()
			if (self.window):
					self.window.connect("destroy", self.NoReturn)
					for i in [self.Atk,self.Dec,self.Sus,self.Rel]:
							i.connect("value-changed", self.BoxChange)
					self.RB.connect("clicked",self.Return)
	def Return(self,sender):
			self.window.destroy()
			gtk.main_quit(sender)
	def Update(self):
			Atk=self.Atk.get_value()
			Dec=self.Dec.get_value()
			Sus=self.Sus.get_value()/100
			Rel=self.Rel.get_value()
			self.function=ADSR(Atk,Dec,Sus,Rel)
			im=ListToGraph(map(self.function.atpos,range(480)),1,-1).save("GUI/Enveloper/Images/TempADSR.png")
			self.Image.set_from_file("GUI/Enveloper/Images/TempADSR.png")
			self.functiontext=reduce(lambda a,b:a+str(b)+",",[Atk,Dec,Sus,Rel],"ADSR(")[:-1]+")"
	def NoReturn(self,sender):
			self.window.destroy()
			gtk.main_quit(sender)
	def BoxChange(self,changed):
		self.Update()"""
	
def opendialog():
	Mygtk = BeatGTK()
	gtk.main()
	return (Mygtk.function,Mygtk.functiontext)
opendialog()
