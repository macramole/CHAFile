import sys
sys.path.insert(0, '../')

from ChaFile import *
from glob import glob
import json

"""
. Las llamadas telefónicas son sólo un turno en ADS
. Hay que descartar las utts que no tienen palabras (hay muchisimas y son en realidad dirigidas al chi (besa, rie))
. Tanto las intervening como las non-intervening son muchas menos que las utts


. TODO: Correr la cuenta de emisiones de nuevo sacar las que no tienen palabras
. TODO: Checkear los VS ADS porque estan dirigidos a cualquiera
"""

TURN_CDS_MAX_INTERVENING_CHILD = 1 # cuantas intervenciones del CHI
TURN_CDS_MAX_INTERVENING_OTHER = 3 # cuantas intervenciones de otros hablantes

TURN_ADS_MAX_INTERVENING_OTHER = 3 # cuantas intervenciones de otros hablantes

# MAX_INTERVENCION_TO_CHILD = 1 # cuantas intervenciones al CHI de otro hablante

TURN_MAX_TIME = 5000 #ms 

def getTurns( addressee, allowIntervining = True ):
	"""Get utterances grouped by speakers turns

	Args:
		addressee (str): ADDRESSEE_CHILD_DIRECTED or ADDRESSEE_ADULT
		allowIntervining (bool, optional): Only for ADDRESSEE_ADULT, allow intervening utterances. Defaults to True.

	Returns:
		dict: Utterances grouped by speakers turns
	"""
	speakers = cha.getSpeakers()

	def endTurno():
		nonlocal turnos, turno, speaker
		nonlocal qtyIntervencionChild, qtyIntervencionOther
		
		turnos[speaker].append(turno)
		turno = []

		qtyIntervencionChild = 0
		qtyIntervencionOther = 0

	turnos = {}

	if addressee == ADDRESSEE_CHILD_DIRECTED: ### Turnos dirigidos a target child
		target = SPEAKER_TARGET_CHILD

		for speaker in speakers:
			if speaker in [SPEAKER_CODE] :
				continue

			turnos[speaker] = []
			turno = []

			qtyIntervencionChild = 0
			qtyIntervencionOther = 0
			
			for l in cha.getLines():
				if len(l[TIER_MOR]) == 0: #las lineas vacias las descarto
					continue

				if not turno: # nuevo turno
					if l[LINE_SPEAKER] == speaker and l[LINE_ADDRESSEE] == target:
						turno.append(l)
				else: # turno existente
					tiempoActual = tiempoAnterior = None

					if LINE_BULLET in l and LINE_BULLET in turno[-1]:
						tiempoActual = l[LINE_BULLET][0]
						tiempoAnterior = turno[-1][LINE_BULLET][1]
					
					if tiempoActual and (tiempoActual - tiempoAnterior >= TURN_MAX_TIME):
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
								if qtyIntervencionChild > TURN_CDS_MAX_INTERVENING_CHILD:
									endTurno()
							else:
								qtyIntervencionOther += 1
								if qtyIntervencionOther > TURN_CDS_MAX_INTERVENING_OTHER:
									endTurno()
	
	elif addressee == ADDRESSEE_ADULT: ### Turnos entre adultxs
		target = SPEAKER_ADULT

		for speaker in speakers:
			if speaker in [SPEAKER_TARGET_CHILD, SPEAKER_CODE] :
				continue

			turnos[speaker] = []
			turno = []

			qtyIntervencionOther = 0
			
			for l in cha.getLines():
				if len(l[TIER_MOR]) == 0: #las lineas vacias las descarto
					continue

				if not turno: # nuevo turno
					if l[LINE_SPEAKER] == speaker and l[LINE_ADDRESSEE] == target:
						turno.append(l)
				else: # turno existente
					tiempoActual = tiempoAnterior = None

					if LINE_BULLET in l and LINE_BULLET in turno[-1]:
						tiempoActual = l[LINE_BULLET][0]
						tiempoAnterior = turno[-1][LINE_BULLET][1]
					
					if tiempoActual and (tiempoActual - tiempoAnterior >= TURN_MAX_TIME):
						endTurno()
					else:
						if l[LINE_SPEAKER] == speaker: #el hablante es correcto
							if l[LINE_ADDRESSEE] == target: #si habla con el chico u otro se corta el turno
								turno.append(l)
							else:
								endTurno()
						else: #el hablante cambió (sea el chico o no)
							if allowIntervining:
								qtyIntervencionOther += 1
								if qtyIntervencionOther > TURN_ADS_MAX_INTERVENING_OTHER:
									endTurno()
							else:
								endTurno()
	
	else:
		raise Exception("'addressee' argument should be ADDRESSEE_CHILD_DIRECTED or ADDRESSEE_ADULT")
					
	return turnos

# for f in glob("/home/leandro/Code/ciipme/aclew/highvolResults/listos_cha/*.cha"):
#     cha = ChaFile( f, language = LANGUAGE_SPANISH )
#     filename = os.path.basename(f)

#     turnos = getTurnos()
#     cantTurnos = 0
#     for t in turnos:
#         cantTurnos += len(turnos[t])
	
#     cantLineas = len(cha.getLines())

#     print(f"{filename}: {cantTurnos} / {cantLineas}")

### Uno solo

# chaPath = "/home/macramole/Code/ciipme/aclew/highvolResults/listos_cha/donatow-a1-nsm.elan.cha"
# chaPath = "/home/macramole/Code/ciipme/corpusESPON/longi_audio1/codificados/codificados bullets elan/facundoa-a1-nsm.cha"
chaPath = "/home/macramole/Code/ciipme/corpusESPON/longi_audio1/codificados/codificados bullets elan/francescal-a1-nsm.cha"

cha = ChaFile( chaPath, language = LANGUAGE_SPANISH )

print("")
print(chaPath)
print("")

uttsBySpeaker = cha.getLinesBySpeakers()
uttsBySpeakerByAddressee = {}
for s in uttsBySpeaker:
	uttsToChild = 0
	uttsToAdult = 0
	for line in uttsBySpeaker[s]:
		if line[LINE_ADDRESSEE] == SPEAKER_ADULT:
			uttsToAdult += 1
		elif line[LINE_ADDRESSEE] == SPEAKER_TARGET_CHILD:
			uttsToChild += 1

	uttsBySpeakerByAddressee[s] = {
		"child" : uttsToChild,
		"adult" : uttsToAdult,
	}

turnos = getTurns( ADDRESSEE_CHILD_DIRECTED )
with open("testTurnosCDS.json", "w") as f:
	json.dump(turnos, f)

print("")
print("***")
print("CDS (turnos/utts)")
print("***")
for speaker in turnos:
	cantTurnos = len(turnos[speaker])
	print(f"{speaker}: {cantTurnos} / { uttsBySpeakerByAddressee[speaker]['child'] }")

turnos = getTurns( ADDRESSEE_ADULT, True )
for speaker in turnos:
	turnos[speaker][:] = [ utts for utts in turnos[speaker] if len(utts) > 1 ]
with open("testTurnosADS_intervening.json", "w") as f:
	json.dump(turnos, f)

print("")
print("***")
print("ADS intervening (turnos/utts)")
print("***")
for speaker in turnos:
	cantTurnos = len(turnos[speaker])
	print(f"{speaker}: {cantTurnos} / { uttsBySpeakerByAddressee[speaker]['adult'] }")

turnos = getTurns( ADDRESSEE_ADULT, False )
for speaker in turnos:
	turnos[speaker][:] = [ utts for utts in turnos[speaker] if len(utts) > 1 ]
with open("testTurnosADS_NON-intervening.json", "w") as f:
	json.dump(turnos, f)

print("")
print("***")
print("ADS NON-intervening (turnos/utts)")
print("***")
for speaker in turnos:
	cantTurnos = len(turnos[speaker])
	print(f"{speaker}: {cantTurnos} / { uttsBySpeakerByAddressee[speaker]['adult'] }")