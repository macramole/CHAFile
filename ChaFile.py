#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Oct 29 14:59:04 2018

@author: Leandro Garber


Tema CHAs importados desde ELAN de archivos de ACLEW

No hay +CHI ni +OCH sino que hay

En la misma línea [%%xds:] que puede ser:
	[%%xds:C]
	[%%xds:T]
	[%%xds:O]
	[%%xds:U]

En la mayoría de los casos el +CHI es [%%xds:C]. Excepto en ROS y CAS que es
[%%xds:T]

ESTO CAMBIÓ
Ahora se usa T en todos los casos pero xds se exporta como tier

"""

import os
from xml.dom import minidom
from subprocess import getstatusoutput
import re
from log import Log

ERROR_NO_MOR_FOUND = 1

MOR_ERROR_NO_MOR_FOUND = "TIER \"%MOR\", ASSOCIATED WITH A SELECTED SPEAKER"
MOR_UNIT_CATEGORIA = "categoria"
MOR_UNIT_LEXEMA = "lexema"
MOR_STOP_WORDS = ["imp|da-2S&IMP~pro:clit|3S", "imp|da-2S&IMP~pro:clit|3S=give"] #este es el dale
MOR_REPLACEMENTS = { #reemplazo de palabras que está agarrando mal el MOR, ej: n|papi debería ser n|papá
	"papi" : "papá",
	"mami" : "mamá",
	"vamos" : "i" #co|vamos -> co|i esto es porque toma como "co" algo que es "v"
}

LINE_UTTERANCE = "emisión"
LINE_NUMBER = "número"
LINE_SPEAKER = "hablante"
LINE_TOCHILD = "dirigidaAlNiño" #DEPRECATED in favor of LINE_ADDRESSEE
LINE_ADDRESSEE = "destinatario"
LINE_BULLET = "bullet"
LINE_NOUNS = "sustantivos"
LINE_VERBS = "verbos"

#BULLET_TAG = "%snd"
BULLET_TAG = "{0x15}"

TIER_MOR = "mor"
TIER_XDS = "xds"
TIER_PRAGMATIC_FUNCTION = "pra"
TIER_ACTIVITY = "dad"
TIER_ACTIVITY_SCORES = {
	"IND" :-1,
	"CAA" : 0, # Conversaciones entre adultos, Adult conversations
	"CAB" : 1, # Conversaci, Adult-Child Conversation
	"JUO" : 4, #
	"JUF" : 4, #
	"JUE" : 6,
	"LEC" : 6,
	"COM" : 2, # Household chores
	"HIG" : 5,
	"DOM" : 5,
	"CAL" : 5,
	"MTV" : 3
}
TIER_PRAGMATIC_FUNCTION_FUNCTIONS = [
	"PVN",
	"DAN",
	"DEN",
	"PVV",
	"DAV",
	"DAA",
	"DEV",
	"IND",
]

ADDRESSEE_TAG = "[+ %s]"
ADDRESSEE_XDS_CHILD = "C"
ADDRESSEE_XDS_OTHER = "O"
ADDRESSEE_XDS_UNKNOWN = "U"
ADDRESSEE_XDS_ADULT = "A"
ADDRESSEE_XDS_TARGET_CHILD = "T"
ADDRESSEE_XDS_BOTH = "B"
#BOTH ?

SPEAKER_SILENCE = "*SIL"
SPEAKER_TARGET_CHILD = "CHI"
SPEAKER_OTHER_CHILD = "OCH"
SPEAKER_ADULT = "ADULT"
SPEAKER_OTHER = "OTHER"
SPEAKER_UNKNOWN = "UNKNOWN"
SPEAKER_BOTH = "BOTH" #ADULT + TARGET

ADDRESSEE_CORRESPOND = {
	ADDRESSEE_XDS_CHILD : SPEAKER_OTHER_CHILD,
	ADDRESSEE_XDS_OTHER : SPEAKER_OTHER,
	ADDRESSEE_XDS_UNKNOWN : SPEAKER_UNKNOWN,
	ADDRESSEE_XDS_ADULT : SPEAKER_ADULT,
	ADDRESSEE_XDS_TARGET_CHILD : SPEAKER_TARGET_CHILD,
	ADDRESSEE_XDS_BOTH : SPEAKER_BOTH
}

CATEGORIAS_VERBOS = ["v","ger","part","aux","imp","inf","cop"] #habia sacado "cop" en variation sets y saque "co" porque toma cualquier cosa

MISSING_VALUE = "?"

CLAN_BIN_PATH = os.path.join( os.path.dirname(__file__), "./clanBin/" )

log = Log()

class ChaFile:

	noBullets = True
	lines = []
	speakers = []
	language = None

	def _parseMor(self, morContent, lineNumber):
			morContent = morContent.split(" ")

			arrMorData = []

			for morUnit in morContent:
				parsedMorUnit = self._parseMorUnit(morUnit)
				if parsedMorUnit != {}:
					arrMorData.append( parsedMorUnit )

			return arrMorData

	def _parseMorUnit(self, morUnit):
		if morUnit in MOR_STOP_WORDS:
			return {}

		sepIndex = morUnit.find("|")
		if sepIndex > -1:
			morCategoriaPalabra = morUnit[:sepIndex]

			endIndex = morUnit.find("=")

			# caso especial para verbos (n) porque está tomando mal los
			# diminutivos, para que agarre bien la descripción
			if morCategoriaPalabra == "n":
				endIndex = morUnit.find("&")
				if endIndex == -1:
					endIndex = morUnit.find("-")

					if endIndex == -1:
						endIndex = morUnit.find("=")

			morLexema = morUnit[sepIndex+1:endIndex]
			if endIndex == -1:
				morLexema = morUnit[sepIndex+1:].strip()

			#en verbos también me quedo con la descripción hasta -
			#co es un caso especial
			if morCategoriaPalabra in CATEGORIAS_VERBOS and morCategoriaPalabra != "co" :
				sepDescripcionIndex = morLexema.find("-")
				morLexema = morLexema[:sepDescripcionIndex]

			#reemplazo de palabras que está agarrando mal el MOR, ej: n|papi debería ser n|papá
			if morLexema in MOR_REPLACEMENTS:
				morLexema = MOR_REPLACEMENTS[morLexema]

			parsedMorUnit = {
				MOR_UNIT_CATEGORIA : morCategoriaPalabra,
				MOR_UNIT_LEXEMA : morLexema
			}

			return parsedMorUnit
		else:
			return {}

	def _parsePra(self, praContent, lineNumber):
		pra = praContent.strip()[1:].strip()
		if not pra in TIER_PRAGMATIC_FUNCTION_FUNCTIONS:
			log.log("Warning. Pragmatic function %s is invalid. Using %s (line %d)" % (MISSING_VALUE, pra, lineNumber))
			return MISSING_VALUE

		return pra

	def _parseDad(self, dadContent, lineNumber):
		dads = dadContent.strip()[1:].split(":")

		for dad in dads:
			if not dad in TIER_ACTIVITY_SCORES:
				log.log("Warning. Activity %s is invalid. Using IND (line %d)" % (dad, lineNumber))
				return ["IND"]

		return dads

	def __init__(self, chaFilePath, SPEAKER_IGNORE = [ SPEAKER_SILENCE ], USE_TIERS = [ TIER_MOR ], CDS_ONLY = False):
		self.chaFilePath = chaFilePath
		self.SPEAKER_IGNORE = SPEAKER_IGNORE
		self.USE_TIERS = USE_TIERS
		self.CDS_ONLY = CDS_ONLY

		self.filename = os.path.basename(chaFilePath)
		self.filename = self.filename[0:self.filename.rfind(".")]

		self._setLanguage()
		self.processLines()

	def getLines(self):
		return self.lines

	def getLine(self, lineNumber):
		for line in self.lines:
			if line[LINE_NUMBER] == lineNumber:
				return line

		return None

	def getLinesFromTo(self, lineFrom, lineTo):
		linesToReturn = []

		for line in self.lines:
			if line[LINE_NUMBER] >= lineFrom and line[LINE_NUMBER] < lineTo:
				linesToReturn.append(line)

		return linesToReturn

	def getLinesBySpeakers(self):
		linesBySpeakers = {}

		for line in self.lines:
			if not line[LINE_SPEAKER] in linesBySpeakers:
				linesBySpeakers[ line[LINE_SPEAKER] ] = []

			linesBySpeakers[ line[LINE_SPEAKER] ].append(line)

		return linesBySpeakers

	def getSpeakers(self):
		return self.speakers

	def _setLanguage(self):
		LANGUAGE_RE = "@Languages:.(.+)"

		if not os.path.isfile(self.chaFilePath):
			raise FileNotFoundError()

		with open(self.chaFilePath, "r") as f:
			loop = True
			while loop:
				line = f.readline()
				if line:
					x = re.match(LANGUAGE_RE, line)
					if x is not None:
						self.language = x.group(1)
						loop = False
				else:
					loop = False

		if self.language is None:
			log.log("Warning: no language found")
	def getLanguage(self):
		return self.language

	def processLines(self):
		INDEX_CONTENIDO = 13
		INDEX_LINENUMBER = 12
		INDEX_SPEAKER = 3

		strTiers = " "
		for t in self.USE_TIERS:
			strTiers += "+t%s " % ("%" + t)

		if not os.path.isfile(self.chaFilePath):
			raise FileNotFoundError()

		# La primera línea deberia andar pero no anda desde spyder y no puedo debuggear
		# entonces hago la segunda (que no creo que ande en Windows)
		# exitcode, output = getstatusoutput(  os.path.join(CLAN_BIN_PATH, "kwal") + " +d4 -f " + strTiers + " \"" + self.chaFilePath + "\" " )
		command = "cat \"%s\" | %s +d4 -f %s" % (self.chaFilePath, os.path.join(CLAN_BIN_PATH, "kwal"), strTiers)
		# print(command)
		exitcode, output = getstatusoutput( command )

		if exitcode != 0:
			log.log("CLAN's kwal command failed. Command was:\n %s" % command)
			log.log("Output: \n %s \n\n (...) \n\n %s" % ( output[0:1000], output[-1000:] ))
			raise IOError()

		try:
			xmlFrom = output.find("<?xml")
			xmlOutput = minidom.parseString(output[ xmlFrom: ])
		except:
			if MOR_ERROR_NO_MOR_FOUND in output:
				raise IOError(ERROR_NO_MOR_FOUND)
			else :
				log.log("Error parsing CLAN's kwal XML output. Command was:\n %s" % command)
				log.log("Output: \n %s \n\n (...) \n\n %s" % ( output[0:1000], output[-1000:] ))
				raise

		self.lines = []
		self.speakers = []

		for row in xmlOutput.getElementsByTagName("Row"):
			rowCells = row.getElementsByTagName("Cell")

			lineNumber = rowCells[INDEX_LINENUMBER].firstChild.firstChild.data
			content = rowCells[INDEX_CONTENIDO].firstChild.firstChild.data
			speaker = rowCells[INDEX_SPEAKER].firstChild.firstChild.data

			if speaker in self.SPEAKER_IGNORE:
				continue
			if not speaker in self.speakers:
				self.speakers.append(speaker)

			strLine = content[6:]

			line = {
				LINE_UTTERANCE : strLine,
				LINE_NUMBER : int(lineNumber),
				LINE_SPEAKER : speaker,
				LINE_ADDRESSEE : None
			}

			if BULLET_TAG in strLine:
				bullet = strLine[ strLine.find(BULLET_TAG): ].replace(BULLET_TAG,"").split("_")
				line[ LINE_BULLET ] = [ int(bullet[-2]), int(bullet[-1]) ]
				line[ LINE_UTTERANCE ] = strLine[ :strLine.find(BULLET_TAG)].strip()
				self.noBullets = False

			for tier in self.USE_TIERS:
				line[tier] = MISSING_VALUE

			tiers = []
			for i in range(INDEX_CONTENIDO+1, len(rowCells)):
				tierContent = rowCells[i].firstChild.firstChild.data
				tiers.append( tierContent )

			for tier in tiers:
				tierName = tier[1:4]
				line[tierName] = tier[5:].strip()

				if hasattr(self, "_parse%s" % tierName.capitalize() ):
					tierProcessFunction = getattr(self, "_parse%s" % tierName.capitalize() )
					line[tierName] = tierProcessFunction( line[tierName], line[LINE_NUMBER] )

			self._setAddressee(line)

			if not (self.CDS_ONLY and line[LINE_ADDRESSEE] not in [SPEAKER_TARGET_CHILD, SPEAKER_BOTH]):
				self.lines.append(line)

	def _setAddressee(self, line):
		addressee = SPEAKER_ADULT

		if not TIER_XDS in line:
			# This is the way we usually do it. e.g. +CHI
			for target in [ SPEAKER_TARGET_CHILD, SPEAKER_OTHER_CHILD ]:
				tag = ADDRESSEE_TAG % target
				if tag in line[LINE_UTTERANCE]:
					addressee = target
					line[LINE_UTTERANCE] = line[LINE_UTTERANCE].replace(tag, "").strip()
		elif line[TIER_XDS] != MISSING_VALUE:
			if line[TIER_XDS] in ADDRESSEE_CORRESPOND:
				addressee = ADDRESSEE_CORRESPOND[ line[TIER_XDS] ]
			else:
				print(f"Warning unknown addressee '{line[TIER_XDS]}' in line '{line[LINE_NUMBER]}'")
				addressee = ADDRESSEE_XDS_UNKNOWN

		line[LINE_ADDRESSEE] = addressee

		# This was the way elan2cha worked. Leaving this for compatibility
		# if ADDRESSEE_ALT_TAG in strLine:
		# 	for target in [ ADDRESSEE_ALT_TAG_ADULT,
		# 					ADDRESSEE_ALT_TAG_CHILD,
		# 					ADDRESSEE_ALT_TAG_OTHER,
		# 					ADDRESSEE_ALT_TAG_TARGET_CHILD,
		# 					ADDRESSEE_ALT_TAG_UNKNOWN]:
		# 		tag = ADDRESSEE_ALT_TAG_TEMPLATE % target
		# 		if tag in strLine:
		# 			if not USE_ALT_TARGET_CHILD:
		# 				addressee = ADDRESSEE_CORRESPOND[target]
		# 			else:
		# 				addressee = ADDRESSEE_CORRESPOND_ALT[target]
		#
		# 			strLine = strLine.replace(tag, "").strip()
		#
		# return addressee, strLine

	def countUtterances(self):
		return len(self.lines)

	def countUtterancesByAddressee(self):
		addressees = {}

		for l in self.getLines():
			addressee = l[LINE_ADDRESSEE]
			if addressee in addressees:
				addressees[addressee] += 1
			else:
				addressees[addressee] = 1

		return addressees

	def countWordsByAddressee(self):
		assert "mor" in self.USE_TIERS, "mor tier has to be selected for usage to use this function"
		addressees = {}

		for l in self.getLines():
			c = self.countWordsInLine(l)

			addressee = l[LINE_ADDRESSEE]
			if addressee in addressees:
				addressees[addressee] += c
			else:
				addressees[addressee] = c

		return addressees

	def countWordsInLine(self, line):
		assert "mor" in self.USE_TIERS, "mor tier has to be selected for usage to use this function"
		dontCount = ["cm"] #no cuentes la coma

		c = 0
		for morUnit in line[TIER_MOR]:
			if morUnit != MISSING_VALUE and morUnit[MOR_UNIT_CATEGORIA] not in dontCount:
				c += 1

		return c

	def countNouns(self):
		for l in self.getLines():
			self._countNounsLine(l)
	def _countNounsLine(self, linea):
		sustantivos = {}

		def sumarSustantivos(sust):
			if sust in sustantivos:
				sustantivos[sust] += 1
			else:
				sustantivos[sust] = 1

		for morUnit in linea[TIER_MOR]:
			if morUnit[MOR_UNIT_CATEGORIA] == "n":
				sumarSustantivos( morUnit[MOR_UNIT_LEXEMA] )

		linea[LINE_NOUNS] = sustantivos

	def getVerbs(self, soloIndices = True, CONTAR_COPULA_Y_AUXILIAR = False):
		for l in self.getLines():
			self._getVerbsInLine(l, soloIndices, CONTAR_COPULA_Y_AUXILIAR)

	def _getVerbsInLine(self, linea, soloIndices = True, CONTAR_COPULA_Y_AUXILIAR = False):
		verbos = []
		# line = copy.deepcopy(linea)
		lineaMor={}
		for i, m in enumerate(linea["mor"]):
			lineaMor[i] = m

		# V1 SÍ AUX: ir a, tener que, poder, haber, estar, dejar de, deber, acabar de,
		# terminar de, haber que, estar por, empezar a, empezar por, comenzar a, poner a, volver a

		#1) Cuando es auxiliar + infinitivos, contar el infinitivo
		#2) Cuando es auxiliar + gerundio, contar el gerundio
		#3) Cuando es auxiliar + participio, contar el participio

		raices = [
			[["i"],["a"]],
			[["tene"],["que"]],
			[["pode"]],
			[["habe"]],
			[["esta"]],
			[["deja"],["de"]],
			[["debe"]],
			[["acaba"],["de"]],
			[["termina"],["de"]],
			[["habe"],["que"]],
			[["esta"],["por"]],
			[["empeza"],["a"]],
			[["empeza"],["por"]],

			[["comienzo"],["a"]],
			[["comenza"],["a"]],

			[["pone"],["a"]],
			[["volve"],["a"]]
		]

		siguiente_palabra_de_auxiliar = [ "inf", "ger", "part" ]

		#4) Cuando es copulativo + gerundio contar el gerundio
		#5) Cuando es copulativo + participio contar el participio.

		criteriosCategoria = [
				[ ["cop"],["ger","part"] ]
		]

		#6) No contar el copula o auxiliar si está solo (1versión) / contar el cópula o el auxiliar si esta sólo (2 versión)
		#CONTAR_COPULA_Y_AUXILIAR = False # Hago los dos mas abajo

		#7) En los casos de 2 o 3 Verbos (verbos conjugado, infinitivo, gerundio o participio), contar el que no es ni auxiliar, ni copula.
		#estoy contando frase verbal + verbo final

		#8) si hay 2 o más verbos conjugados coordinados en una emisión se toman todos.

		#1) 2) y 3) auxiliares    aux + (inf,ger,part)

		for raiz in raices:
			criteriaType = [ MOR_UNIT_LEXEMA for c in raiz ]
			criteria = raiz + [siguiente_palabra_de_auxiliar]
			criteriaType.append(MOR_UNIT_CATEGORIA)

			morIndexes = self._checkCriteria( list(lineaMor.values()), criteria, criteriaType )
			while len(morIndexes) > 0:
				trueIndex = list(lineaMor.keys())[ morIndexes[-1] ]
				if not soloIndices:
					verbos.append( lineaMor[ trueIndex ] )
				else:
					verbos.append( trueIndex )

				trueIndexesToDelete = []
				for morIndex in morIndexes:
					trueIndexesToDelete.append( list(lineaMor.keys())[ morIndex ] )
				for i in trueIndexesToDelete:
					del lineaMor[ i ]

				criteriaType = [ MOR_UNIT_LEXEMA for c in raiz ]
				criteria = raiz + [siguiente_palabra_de_auxiliar]
				criteriaType.append(MOR_UNIT_CATEGORIA)
				morIndexes = self._checkCriteria( list(lineaMor.values()), criteria, criteriaType )

		#cop + (ger | part)
		for criterio in criteriosCategoria:
			morIndexes = self._checkCriteria( list(lineaMor.values()), criterio, MOR_UNIT_CATEGORIA )
			while len(morIndexes) > 0:
				trueIndex = list(lineaMor.keys())[ morIndexes[1] ]
				if not soloIndices:
					verbos.append( lineaMor[trueIndex] )
				else:
					verbos.append( trueIndex )

				trueIndexesToDelete = []
				for morIndex in morIndexes:
					trueIndexesToDelete.append( list(lineaMor.keys())[ morIndex ] )
				for i in trueIndexesToDelete:
					del lineaMor[ i ]

				morIndexes = self._checkCriteria( list(lineaMor.values()), criterio, MOR_UNIT_CATEGORIA )

		#verbos normales
		verbosIndividualesAContar = CATEGORIAS_VERBOS.copy()

		if not CONTAR_COPULA_Y_AUXILIAR:
			verbosIndividualesAContar.remove("cop")
			verbosIndividualesAContar.remove("aux")

		morIndexes = self._checkCriteria( list(lineaMor.values()), [ verbosIndividualesAContar ], MOR_UNIT_CATEGORIA )
		while len(morIndexes) > 0:
			trueIndex = list(lineaMor.keys())[ morIndexes[0] ]

			if not soloIndices:
				verbos.append( lineaMor[trueIndex] )
			else:
				verbos.append( trueIndex )

			trueIndexesToDelete = []
			for morIndex in morIndexes:
				trueIndexesToDelete.append( list(lineaMor.keys())[ morIndex ] )
			for i in trueIndexesToDelete:
				del lineaMor[ i ]

			morIndexes = self._checkCriteria( list(lineaMor.values()), [ verbosIndividualesAContar ], MOR_UNIT_CATEGORIA )

		linea[LINE_VERBS] = verbos

	def countVerbs(self, CONTAR_COPULA_Y_AUXILIAR = False):
		for l in self.getLines():
			self._countVerbsInLine(l, CONTAR_COPULA_Y_AUXILIAR)

	def _countVerbsInLine(self, linea, CONTAR_COPULA_Y_AUXILIAR = False):
		import copy

		verbos = {}
		line = copy.deepcopy(linea)

		def sumarVerbo(verbo):
			if verbo in verbos:
				verbos[verbo] += 1
			else:
				verbos[verbo] = 1

		# V1 SÍ AUX: ir a, tener que, poder, haber, estar, dejar de, deber, acabar de,
		# terminar de, haber que, estar por, empezar a, empezar por, comenzar a, poner a, volver a


		#1) Cuando es auxiliar + infinitivos, contar el infinitivo
		#2) Cuando es auxiliar + gerundio, contar el gerundio
		#3) Cuando es auxiliar + participio, contar el participio

		raices = [
			[["i"],["a"]],
			[["tene"],["que"]],
			[["pode"]],
			[["habe"]],
			[["esta"]],
			[["deja"],["de"]],
			[["debe"]],
			[["acaba"],["de"]],
			[["termina"],["de"]],
			[["habe"],["que"]],
			[["esta"],["por"]],
			[["empeza"],["a"]],
			[["empeza"],["por"]],

			[["comienzo"],["a"]],
			[["comenza"],["a"]],

			[["pone"],["a"]],
			[["volve"],["a"]]
		]

		siguiente_palabra_de_auxiliar = [ "inf", "ger", "part" ]

		#4) Cuando es copulativo + gerundio contar el gerundio
		#5) Cuando es copulativo + participio contar el participio.

		criteriosCategoria = [
				[ ["cop"],["ger","part"] ]
		]

		#6) No contar el copula o auxiliar si está solo (1versión) / contar el cópula o el auxiliar si esta sólo (2 versión)
		#CONTAR_COPULA_Y_AUXILIAR = False # Hago los dos mas abajo

		#7) En los casos de 2 o 3 Verbos (verbos conjugado, infinitivo, gerundio o participio), contar el que no es ni auxiliar, ni copula.
		#estoy contando frase verbal + verbo final

		#8) si hay 2 o más verbos conjugados coordinados en una emisión se toman todos.

		#1) 2) y 3) auxiliares    aux + (inf,ger,part)

		for raiz in raices:
			criteriaType = [ MOR_UNIT_LEXEMA for c in raiz ]
			criteria = raiz + [siguiente_palabra_de_auxiliar]
			criteriaType.append(MOR_UNIT_CATEGORIA)
			morIndexes = self._checkCriteria( line["mor"], criteria, criteriaType )
			while len(morIndexes) > 0:
				lexemaFinal = line["mor"][ morIndexes[-1] ][MOR_UNIT_LEXEMA]
				sumarVerbo(lexemaFinal)
				del line["mor"][ morIndexes[0]:(morIndexes[-1]+1) ]

				criteriaType = [ MOR_UNIT_LEXEMA for c in raiz ]
				criteria = raiz + [siguiente_palabra_de_auxiliar]
				criteriaType.append(MOR_UNIT_CATEGORIA)
				morIndexes = self._checkCriteria( line["mor"], criteria, criteriaType )

		#cop + (ger | part)
		for criterio in criteriosCategoria:
			morIndexes = self._checkCriteria( line["mor"], criterio, MOR_UNIT_CATEGORIA )
			while len(morIndexes) > 0:
				verboAContar = line["mor"][ morIndexes[1] ]
				sumarVerbo( verboAContar[ MOR_UNIT_LEXEMA ] )

				del line["mor"][ morIndexes[0]:(morIndexes[-1]+1) ]

				morIndexes = self._checkCriteria( line["mor"], criterio, MOR_UNIT_CATEGORIA )

		#verbos normales
		verbosIndividualesAContar = CATEGORIAS_VERBOS.copy()

		if not CONTAR_COPULA_Y_AUXILIAR:
			verbosIndividualesAContar.remove("cop")
			verbosIndividualesAContar.remove("aux")

		morIndexes = self._checkCriteria( line["mor"], [ verbosIndividualesAContar ], MOR_UNIT_CATEGORIA )
		while len(morIndexes) > 0:
			verboAContar = line["mor"][ morIndexes[0] ]
			sumarVerbo( verboAContar[ MOR_UNIT_LEXEMA ] )
			del line["mor"][ morIndexes[0]:(morIndexes[-1]+1) ]
			morIndexes = self._checkCriteria( line["mor"], [ verbosIndividualesAContar ], MOR_UNIT_CATEGORIA )

		linea[LINE_VERBS] = verbos

	# busca lineas cuyo mor cumplan cierto criterio
	#
	# el criterio es de la siguiente manera
	# [ ["categoria mor"], ["categoria mor","categoria mor2"] ]
	# tiene que haber dos palabras juntas. la primera con "categoria mor"
	# y la segunda o "categoria mor" o "categoria mor2"
	#
	# busca por categoria o por lexema (usar constantes MOR_UNIT_CATEGORIA o MOR_UNIT_LEXEMA)
	# criteriaType puede ser un array o un string
	# en caso de array tiene que ser del mismo tamaño que criteria
	def findLinesByMorCriteria(self, criteria, criteriaType=MOR_UNIT_CATEGORIA):
		results = []

		assert "mor" in self.USE_TIERS, "mor tier has to be selected for usage to use this function"
		assert isinstance( criteria, list ) and len(criteria) > 0 and isinstance( criteria[0], list ), "invalid criteria, expected: [ [], ...]"

		for line in self.lines:
			if "mor" in line:
				matchedCriteria = self._checkCriteria(line["mor"], criteria, criteriaType)
				if len(matchedCriteria) > 0:
					result = {
						"line" : line,
						"matchedCriteria" : []
					}

					for morUnitIndex in matchedCriteria:
						result["matchedCriteria"].append( line["mor"][morUnitIndex] )

					results.append(result)
		return results

	# funciona como findLinesByMorCriteria pero solo de una línea
	def applyMorCriteriaInLine(self, line, criteria, criteriaType = MOR_UNIT_CATEGORIA):
		return self._checkCriteria( line["mor"], criteria, criteriaType )

	# se fija si el mor cumple el criterio (SOLO UNA VEZ)
	# devuelve un array con los indices de las palabras que cumplen el criterio o vacio
	def _checkCriteria(self, mor, criteria, criteriaType):
		if mor == MISSING_VALUE:
			return []

		matchedCriteria = []
		currentCriteria = 0
		found = False

		for morUnitIndex in range(len(mor)):
			morUnit = mor[morUnitIndex]

			if morUnit == MISSING_VALUE:
				continue

			found = False
			for c in criteria[currentCriteria]:
				isAMatch = False
				if isinstance(criteriaType, str): #esto me parece que no lo estamos permitiendo desde el assert
					isAMatch = ( morUnit[criteriaType] == c )
				elif isinstance(criteriaType, list):
					isAMatch = ( morUnit[ criteriaType[currentCriteria] ] == c )

				if isAMatch:
					matchedCriteria.append(morUnitIndex)
					currentCriteria += 1
					found = True
					break

			if not found and currentCriteria > 0:
				matchedCriteria = []
				currentCriteria = 0


			if currentCriteria == len(criteria):
				return matchedCriteria

		return []

	# para que se quede un solo DAD cuadno hay varios. usa los scores de arriba
	def fixDAD(self):
		for l in self.getLines():
			if l[TIER_ACTIVITY] == MISSING_VALUE:
				if l[LINE_TOCHILD]:
					log.log("Warning. Empty activity in +CHI line (%d)" % l[LINE_NUMBER])
				continue
			maxDAD = l[TIER_ACTIVITY][0]
			for dad in l[TIER_ACTIVITY]:
				if TIER_ACTIVITY_SCORES[dad] > TIER_ACTIVITY_SCORES[maxDAD]:
					maxDAD = dad

		l[TIER_ACTIVITY] = maxDAD
