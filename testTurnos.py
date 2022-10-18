from ChaFile import *
from glob import glob
import json

# Modo con intervención y sin intervención para ADS
# Para CDS dejamos como está

target = SPEAKER_TARGET_CHILD

TURNO_MAX_INTERVENCION_CHILD = 1 # cuantas intervenciones del CHI
TURNO_MAX_INTERVENCION_OTHER = 3 # cuantas intervenciones de otros hablantes

# MAX_INTERVENCION_TO_CHILD = 1 # cuantas intervenciones al CHI de otro hablante

TURNO_MAX_TIEMPO = 5000 #en ms 

def getTurnos():
    speakers = cha.getSpeakers()

    def endTurno():
        nonlocal turnos, turno, speaker
        nonlocal qtyIntervencionChild, qtyIntervencionOther
        
        turnos[speaker].append(turno)
        turno = []

        qtyIntervencionChild = 0
        qtyIntervencionOther = 0

    turnos = {}
    for speaker in speakers:
        turnos[speaker] = []
        turno = []

        qtyIntervencionChild = 0
        qtyIntervencionOther = 0
        
        for l in cha.getLines():
            if not turno: # nuevo turno
                if l[LINE_SPEAKER] == speaker and l[LINE_ADDRESSEE] == target:
                    turno.append(l)
            else: # turno existente
                tiempoActual = tiempoAnterior = None

                if LINE_BULLET in l and LINE_BULLET in turno[-1]:
                    tiempoActual = l[LINE_BULLET][0]
                    tiempoAnterior = turno[-1][LINE_BULLET][1]
                
                if tiempoActual and (tiempoActual - tiempoAnterior >= TURNO_MAX_TIEMPO):
                    endTurno()
                else:
                    if l[LINE_SPEAKER] == speaker: #el hablante es correcto
                        if l[LINE_ADDRESSEE] == target:
                            turno.append(l)
                        else:
                            endTurno()
                    else: #el hablante cambió
                        if l[LINE_SPEAKER] == SPEAKER_TARGET_CHILD:
                            qtyIntervencionChild += 1
                            if qtyIntervencionChild > TURNO_MAX_INTERVENCION_CHILD:
                                endTurno()
                        else:
                            qtyIntervencionOther += 1
                            if qtyIntervencionOther > TURNO_MAX_INTERVENCION_OTHER:
                                endTurno()
                    

    return turnos

for f in glob("/home/leandro/Code/ciipme/aclew/highvolResults/listos_cha/*.cha"):
    cha = ChaFile( f, language = LANGUAGE_SPANISH )
    filename = os.path.basename(f)

    turnos = getTurnos()
    cantTurnos = 0
    for t in turnos:
        cantTurnos += len(turnos[t])
    
    cantLineas = len(cha.getLines())

    print(f"{filename}: {cantTurnos} / {cantLineas}")

### Uno solo

chaPath = "/home/leandro/Code/ciipme/aclew/highvolResults/listos_cha/donatow-a1-nsm.elan.cha"
# chaPath = "/home/leandro/Code/ciipme/corpusESPON/longi_audio1/codificados/codificados bullets elan/facundoa-a1-nsm.cha"
cha = ChaFile( chaPath, language = LANGUAGE_SPANISH )
turnos = getTurnos()

with open("testTurnos.json", "w") as f:
    json.dump(turnos, f)


print("")
print(chaPath)
print("")
for speaker in turnos:
    cantTurnos = len(turnos[speaker])
    print(f"{speaker}: {cantTurnos}")
