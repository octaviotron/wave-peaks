#!/usr/bin/python

import time
import wave
import contextlib
import datetime
import struct
import os
import subprocess
import copy

TOP=32766       # 0.0db (top overloaded wave point)
UMBRAL=TOP*0.8  # 0.8db (noise gate thresshold)
TASA=0.8        # tolerance for accepting a signal (80% of the concurrency average)
wavfolder = "wavs"

# given a "folder" name gives all "*.wav" files found
def listfiles(folder):
    path = os.getcwd() + os.sep + folder
    sound_files = []
    for arch in os.listdir(path):
        if arch.endswith(".wav"):
            filename, file_extension = os.path.splitext(arch)
            sound_files.append(filename)
    return sound_files

# chunks the big audio files into smaller ones. This prevent memory leaks processing big ones.
def chfile(filename):
    if not os.path.isdir(".temp"):
        os.system("mkdir .temp")
    else:
        command = "rm -f .temp/*.wav"
        subprocess.call(command, shell=True)
    command = "ffmpeg -i wavs/"+filename+".wav -f segment -segment_time 60 -c copy .temp/"+filename+"-%05d.wav -loglevel panic > /dev/null"
    subprocess.call(command, shell=True)
    files = listfiles(".temp")
    files.sort()
    return files

# read the wave binary data and convert it to signed 16 bit data (-32767 to +32767)
def readwav(filename) :
    path = os.getcwd() + os.sep + ".temp" + os.sep + filename + ".wav"
    wf = wave.open(path,'r')
    nframes = wf.getnframes()
    wav = wf.readframes(nframes)
    if    wf.getsampwidth() == 4 :
        wav = struct.unpack("<%ul" % (len(wav) / 4), wav)
    elif  wf.getsampwidth() == 2 :
        wav = struct.unpack("<%uh" % (len(wav) / 2), wav)
    else :
        wav = struct.unpack("%uB"  %  len(wav),      wav)
        wav = [ s - 128 for s in wav ]
    nc  = wf.getnchannels()
    if  nc > 1  :
        wavs    = []
        for i in xrange(nc) :
            wavs.append([ wav[si] for si in xrange(0, len(wav), nc) ])
        pass
    else :
        wavs    = ( wav )
    return(wavs)

# finds where the signal is over the thresshold and on 0.0db top 
def umbral(data):
    concs = []  
    ca = 0      # amount of data over the thresshold
    cp = 0      # amount of data on top at distorted level
    cont = 0
    c2 = 0
    for i in range(len(data)):
        if data[i] > UMBRAL:
            ca = ca + 1
            if int(data[i]) > TOP:
                cp = cp +1
        if cont >= 16000:
            cont = 0
            if ca > 1:
                seg = (i/16000)-1
                concs.append([seg, ca, cp])
            ca = 0
            cp = 0
        c2 = c2 +1
        cont = cont +1
    return concs # [time in seconds, amount of high values, amount of peaks]

# read all wave data and detect where are data over thresshold
def picos(archivo):
    chks = chfile(archivo)
    umbrales = []
    for c in range(len(chks)):
        data=readwav(chks[c])
        umbrales.append(umbral(data))
    return umbrales

# convert seconds in hh:mm:ss format
def s2hms(entrada):
    e = float(entrada)
    salida = time.strftime('%H:%M:%S', time.gmtime(e))
    return str(salida)

# return only audio segments where is really any data over thresshold
def cleansilences(peaks):
    cleanpeaks=[]
    for i in range(0, len(peaks)):
        if len(peaks[i]) > 0:
            cleanpeaks.append([i, len(peaks[i])])
    return cleanpeaks

# calcule average of peaks in all audio data, useful later
def promedios(peaks):
    pro = 0
    pros = 0
    for i in range(0, len(peaks)):
        if len(peaks[i]) > 0:
            pro = pro + len(peaks[i])
            pros = pros + 1
    # average is lowered a bit for ensure better level recognition
    promedio = float(pro)/pros*TASA
    return promedio


# prepare times of data to be marked as a starting or ending cut
def precortes(lst, prom):
    precortes=[]
    for i in range(0, len(lst)):
        if lst[i][1] > prom:
            precortes.append(lst[i])
    return precortes

# separe beggining and ending points into a list of lists
def macros(lst):
    #print lst
    salida = []
    tmp = []
    for i in range(0, len(lst)-1):
        actual = lst[i][0]
        siguiente = lst[i+1][0]
        if siguiente - actual == 1:
            tmp.append(actual)
        else:
            tmp.append(actual)
            salida.append(tmp)
            tmp=[]
    if len(tmp) > 0:
        salida.append(tmp)
    return salida

# verifies any trailing data useful before cut time 
def comienza(momento_inicial):
    salida=[]
    bias=peaks[momento_inicial][0][0]         
    if bias > 3:
        t = ((momento_inicial*60) + bias + 1)    
        salida.append(t)                     
        return salida
    if momento_inicial==0:
        salida.append(0)
        return salida
    else:
        anterior = momento_inicial-1
    minuto_anterior = peaks[anterior]
    cont_anterior = 60
    for k in minuto_anterior[::-1]:
        segundo_a = k[0]
        if cont_anterior - segundo_a <= 10:
            cont_anterior = segundo_a
        else:
            break
    corte_anterior = cont_anterior
    t = ((anterior+1)*60)-(60 - corte_anterior)
    salida.append(t)
    return salida

# verifies any leading data useful after cut time
def termina(minuto_inicial):
    salida=[]
    bias=peaks[minuto_inicial][-1][0]
    if bias < 57:
        t = ((minuto_inicial*60) + bias + 2)
        salida.append(t)
        return salida
    posterior = minuto_inicial+1
    minuto_siguiente=peaks[posterior]
    cont = 0
    for i in minuto_siguiente:
        proxpico = i[0]
        if proxpico - cont <= 10:
            cont = proxpico
        else:
            break
    s = (posterior)*60+cont
    salida.append(s)
    return salida

# define the exact cut points (start and end) for each segment
def cortes(macros):
    salida = []
    for i in range(0, len(macros)):
        inicio = comienza(macros[i][0])
        fin = termina(macros[i][-1])
        salida.append(inicio)
        salida.append(fin)
    return salida # :-)

# cut the main file and export only the selected segment times
def cutfiles(cortes, archivo):
    cont = 0
    if not os.path.isdir("salida"):
        os.system("mkdir salida")
    command = "rm -f .temp/*.wav"
    subprocess.call(command, shell=True)
    for i in range(0, len(cortes), 2):
        inicial = s2hms(cortes[i][0])
        final = s2hms(cortes[i+1][0])
        entrada = os.getcwd() + os.sep + "wavs" + os.sep + archivo + ".wav"
        salida = os.getcwd() + os.sep + "salida" + os.sep + archivo + "-" + str(inicial) + "-" + str(final) + "-topic"+str(cont) + ".wav"
        command = "ffmpeg -y -i %s -ss %s -to %s -c copy %s > /dev/null 2>&1" % (entrada, inicial, final, salida)
        subprocess.call(command, shell=True)
        cont = cont +1
        command = "rm -f .temp/*.wav"
        subprocess.call(command, shell=True)

files = listfiles(wavfolder)
for i in range(0, len(files)):
    archivo = files[i]
    print "Reading " + archivo + ".wav file..."
    peaks = picos(archivo)
    clences = cleansilences(peaks)
    prom = promedios(peaks)
    precort = precortes(clences, 12)
    macrs=macros(precort)
    cort=cortes(macrs)
    cutfiles(cort, archivo)
    print archivo + ".wav file parts stored in 'salida' folder"

