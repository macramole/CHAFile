#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Oct 29 14:59:04 2018

@author: Leandro Garber

"""

import os
from subprocess import getstatusoutput
import re
from log import Log

# LINE constants. Use these for getting data from each line
LINE_UTTERANCE = "emisión"
LINE_NUMBER = "número"
LINE_SPEAKER = "hablante"
LINE_ADDRESSEE = "destinatario"
LINE_BULLET = "bullet"
LINE_NOUNS = "sustantivos"
LINE_ADJECTIVES = "adjetivos"
LINE_VERBS = "verbos"
LINE_LIGHT_VERBS = "light-verbs"
#################################

# Speaker constants. line[LINE_SPEAKER] will be one of these
SPEAKER_SILENCE = "*SIL"
SPEAKER_TARGET_CHILD = "CHI"
SPEAKER_OTHER_CHILD = "OCH"
SPEAKER_ADULT = "ADULT"
SPEAKER_PET = "P"
SPEAKER_OTHER = "OTHER"
SPEAKER_UNKNOWN = "UNKNOWN"
SPEAKER_BOTH = "BOTH" #ADULT + (TARGET || CHILD) This is a problem so we are discarding it
###############################################

# Use these constants for calling count method
ADDRESSEE_CHILD_DIRECTED = "cds"
ADDRESSEE_CHILD_PRODUCED = "chi"
ADDRESSEE_OVER_HEARD = "ohs"
ADDRESSEE_ALL = "all"

COUNT_TYPE_TOKENS = "tokens"
COUNT_TYPE_TYPES = "types"
###############################################

# Language constants
LANGUAGE_SPANISH = "spa"
LANGUAGE_ENGLISH = "eng"
######################

# MOR constants. 
# i.e line[TIER_MOR][0][MOR_UNIT_LEXEMA] will store the lexeme of the first word 
ERROR_NO_MOR_FOUND = 1

MOR_ERROR_NO_MOR_FOUND = "TIER \"%MOR\", ASSOCIATED WITH A SELECTED SPEAKER"
MOR_REGEX = r"([A-zÀ-ú:]*)\|([A-zÀ-ú]*)(.*)"
MOR_UNIT_CATEGORIA = "categoria"
MOR_UNIT_LEXEMA = "lexema"
MOR_UNIT_CATEGORIA_LEXEMA = "categoria|lexema" #solo para la búsqueda
MOR_UNIT_EXTRA = "extra"
MOR_STOP_WORDS = [  ["imp", "da", "-2S&IMP~pro:clit|3S"], #lexema o [categoria, lexema] o [categoria, lexema, extra]
					"okay",
					# "like",
					"right"
]
MOR_REPLACEMENTS = { #reemplazo de palabras que está agarrando mal el MOR, ej: n|papi debería ser n|papá
	"papi" : "papá",
	"mami" : "mamá",
	"vamos" : "i" #co|vamos -> co|i esto es porque toma como "co" algo que es "v"
}
###############################

BULLET_TAG = "\x15"

# TIER constants
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
###############################

## Internal use only. Use SPEAKER_*
ADDRESSEE_TAG = "[+ %s]"
ADDRESSEE_XDS_CHILD = "C"
ADDRESSEE_XDS_OTHER = "O"
ADDRESSEE_XDS_UNKNOWN = "U"
ADDRESSEE_XDS_ADULT = "A"
ADDRESSEE_XDS_TARGET_CHILD = "T"
ADDRESSEE_XDS_PET = "P"
ADDRESSEE_XDS_BOTH = "B"
###############

# Internal use
ADDRESSEE_CORRESPOND = {
	ADDRESSEE_XDS_CHILD : SPEAKER_OTHER_CHILD,
	ADDRESSEE_XDS_OTHER : SPEAKER_OTHER,
	ADDRESSEE_XDS_UNKNOWN : SPEAKER_UNKNOWN,
	ADDRESSEE_XDS_ADULT : SPEAKER_ADULT,
	ADDRESSEE_XDS_TARGET_CHILD : SPEAKER_TARGET_CHILD,
	ADDRESSEE_XDS_BOTH : SPEAKER_BOTH,
	ADDRESSEE_XDS_PET : SPEAKER_PET
}

CATEGORIAS_VERBOS = ["v","ger","part","imp","inf","cop", "aux"] #"cop" and "aux" are removed by default when counting verbs
CATEGORIAS_ADJETIVOS = ["adj"]
CATEGORIAS_SUSTANTIVOS = ["n", "n:gerund"] #n:gerund was found in english and want to count it as a noun

MISSING_VALUE = "?"
###############################################

log = Log()

class ChaFile:

	noBullets = True
	lines = []
	speakers = []
	language = None
	morAmbiguousLines = []

	processedVerbs = False
	processedNouns = False
	processedAdjectives = False

	morFound = False #true if MOR was found in at least one line

	def _parseMor(self, morContent, lineNumber):
		"""Internal use. Parse MOR tier

		Args:
			morContent (string): Content of the MOR tier
			lineNumber (int): Line number

		Returns:
			list: Parsed MOR tier
		"""
		morContent = morContent.split(" ")

		arrMorData = []

		for morUnit in morContent:
			if "^" in morUnit:
				if lineNumber not in self.morAmbiguousLines:
					self.morAmbiguousLines.append(lineNumber)

			parsedMorUnit = self._parseMorUnit(morUnit)
			if parsedMorUnit != {}:
				arrMorData.append( parsedMorUnit )

		return arrMorData

	def _parseMorUnit(self, morUnit):
		"""Internal use. Parse a MOR unit (one word)

		Args:
			morUnit (string): One word as described by MOR

		Returns:
			dict: A dict representation of the MOR unit
		"""
		if morUnit in MOR_STOP_WORDS:
			return {}
		
		matches = re.match(MOR_REGEX, morUnit)
		if matches != None: #no agarra ni . ! ? 
			if len(matches.groups()) == 3:
				morCategoria = matches.group(1)
				morLexema = matches.group(2)
				morExtra = matches.group(3)

				for stopWord in MOR_STOP_WORDS:
					if type(stopWord) is list:
						if morLexema == stopWord[1] and morCategoria == stopWord[0]:
							if len(stopWord) == 2:
								return {}
							else:
								if stopWord[2] in morExtra:
									return {}
					else:
						if morLexema == stopWord:
							return {}

				#reemplazo de palabras que está agarrando mal el MOR
				if morLexema in MOR_REPLACEMENTS:
					morLexema = MOR_REPLACEMENTS[morLexema]

				parsedMorUnit = {
					MOR_UNIT_CATEGORIA : morCategoria,
					MOR_UNIT_LEXEMA : morLexema,
					MOR_UNIT_EXTRA : morExtra
				}

				return parsedMorUnit
			else:
				log.log(f"Warning: Malformed mor unit \"{morUnit}\"")
				return {}
		else:
			return {}

	def _parsePra(self, praContent, lineNumber):
		"""Internal use. Parse pragmatic function

		Args:
			praContent (string): Content of the %pra tier
			lineNumber (int): Line number

		Returns:
			string: PRA code
		"""
		pra = praContent.strip()[1:].strip()
		if not pra in TIER_PRAGMATIC_FUNCTION_FUNCTIONS:
			log.log(f"Warning. Pragmatic function {pra} is invalid. Using {MISSING_VALUE} (line {lineNumber})")
			return MISSING_VALUE

		return pra

	def _parseDad(self, dadContent, lineNumber):
		"""Internal use. Parse activity type tier (%dad)

		Args:
			dadContent (string): Content of the %dad tier
			lineNumber (int): Line number

		Returns:
			list: List of activity types as strings
		"""
		dads = dadContent.strip()[1:].split(":")

		for dad in dads:
			if not dad in TIER_ACTIVITY_SCORES:
				log.log("Warning. Activity %s is invalid. Using IND (line %d)" % (dad, lineNumber))
				return ["IND"]

		return dads

	def __init__(self, chaFilePath,
				 ignoreSpeakers = [ SPEAKER_SILENCE ], onlyCDS = False, includeLines = [],
				 verbose = True, language = None):
		"""Constructor. Loads the CHA file and parse it

		Args:
			chaFilePath (string): Path to the CHA file
			ignoreSpeakers (list, optional): Utterances from these speakers won't be parsed. Defaults to [ SPEAKER_SILENCE ].
			onlyCDS (bool, optional): Only child directed utterances will be parsed. Defaults to False.
			includeLines (list, optional): Only these line numbers will be parsed. Defaults to [] which means all lines.
			verbose (bool, optional): Extra information will be printed when processing. Defaults to False.
			language (string, optional): Use one of the LANGUAGE constants or None for parsing it from the CHA file. Defaults to None.
		"""

		self.chaFilePath = chaFilePath
		self.ignoreSpeakers = ignoreSpeakers
		self.onlyCDS = onlyCDS
		self.includeLines = includeLines

		log.setVerbose(verbose)

		self.filename = os.path.basename(chaFilePath)
		self.filename = self.filename[0:self.filename.rfind(".")]

		self.setLanguage(language)
		self.processLines()

	def getLines(self):
		"""Get an array of parsed utterances

		Returns:
			list: Utterances. Access data using the LINE constants
		"""
		return self.lines

	def getLine(self, lineNumber):
		"""Get a line by its number

		Args:
			lineNumber (int): Line number

		Returns:
			dict: Utterance
		"""
		for line in self.lines:
			if line[LINE_NUMBER] == lineNumber:
				return line

		return None

	def getLinesFromTo(self, lineFrom, lineTo):
		"""Get a range of utterances

		Args:
			lineFrom (int): Line number from
			lineTo (int): Line number to

		Returns:
			list: Utterances. Access data using the LINE constants
		"""
		linesToReturn = []

		for line in self.lines:
			if line[LINE_NUMBER] >= lineFrom and line[LINE_NUMBER] < lineTo:
				linesToReturn.append(line)

		return linesToReturn

	def getLinesBySpeakers(self):
		"""Get all parsed utterance grouped by speaker

		Returns:
			list: Utterances. Access data using the LINE constants
		"""
		linesBySpeakers = {}

		for line in self.lines:
			if not line[LINE_SPEAKER] in linesBySpeakers:
				linesBySpeakers[ line[LINE_SPEAKER] ] = []

			linesBySpeakers[ line[LINE_SPEAKER] ].append(line)

		return linesBySpeakers

	def getSpeakers(self):
		"""Get all speakers involved in this transcription

		Returns:
			list: Speakers
		"""
		return self.speakers

	def setLanguage(self, lang=None):
		"""Set language for this transcription. It will be used for processing light verbs

		Args:
			lang (string, optional): Use LANGUAGE constant or None for parsing it from the CHA file. Defaults to None.

		Raises:
			FileNotFoundError: -
		"""
		if lang == None:
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
							language = x.group(1)
							if language in [LANGUAGE_SPANISH, LANGUAGE_ENGLISH]:
								self.language = language

							loop = False
					else:
						loop = False
		else:
			self.language = lang

		if self.language is None:
			log.log("Warning: no language found")
	def getLanguage(self):
		"""Return current language

		Returns:
			string: Language
		"""
		return self.language

	def processLines(self):
		"""Internal use. Main function that parses the CHA file

		Raises:
			FileNotFoundError: The path to the CHA file does not exist
		"""

		if not os.path.isfile(self.chaFilePath):
			raise FileNotFoundError()

		with open(self.chaFilePath,"r") as f:
			txtCHA = f.read()

		prog = re.compile(r"[\*%@]\w*:\t.*?(?=\*\w*:\t|@End|\Z)", re.S)#, re.X)
		parsedCHA = prog.findall(txtCHA)

		self.lines = []
		self.speakers = []
		languages = None
		lineNumber = 1

		for r in parsedCHA:
			#is header
			if r[0] == "@":
				lineNumber += r.count("\n") + 2 #2= utf8 and begin 
				headerMatch = re.match(r"@Languages:\s(.*)", r)
				if headerMatch:
					languages = headerMatch.group(1)
				continue
			
			prog = re.compile(r"(?P<tier>[\*%][\w-]*):[\s]*(?P<content>.*?)(?=[\*%][\w-]*:[\s]*|@End|\Z)", re.S)
			
			line = {
				LINE_NUMBER : lineNumber
			}
			
			skipLine = False

			#build line
			for m in prog.finditer(r):
				tier = m.group("tier")
				content = m.group("content").replace("\t"," ").replace("\n", "")

				if m.group("tier")[0] == "*": #is speaker
					speaker = tier[1:]
					if not speaker in self.ignoreSpeakers:
						if not speaker in self.speakers:
							self.speakers.append(speaker)

						line[LINE_SPEAKER] = speaker
						line[LINE_UTTERANCE] = content

						if BULLET_TAG in content:
							regexBullet = r"\x15(?P<from>\d*)_(?P<to>\d*)\x15"
							progBullet = re.compile(regexBullet)#, re.S)
							parsedBullet = list(progBullet.finditer(content))

							if len(parsedBullet) > 0 :
								bulletFrom = int(parsedBullet[0].group("from"))
								bulletTo = int(parsedBullet[-1].group("to"))
								line[ LINE_BULLET ] = [bulletFrom, bulletTo]
								line[ LINE_UTTERANCE ] = progBullet.sub("", line[ LINE_UTTERANCE ])
							else:
								#esto sucede cuando los bullets son de la forma %snd:"filename"_from_to
								line[ LINE_UTTERANCE ] = line[ LINE_UTTERANCE ].replace(BULLET_TAG, "").strip()
					else:
						skipLine = True
						break
				else:
					tierName = tier[1:]
					line[tierName] = content

					if tierName == "mor":
						self.morFound = True

					#no es realmente un tier
					#esto sucede cuando los bullets son de la forma %snd:"filename"_from_to
					if tierName == "snd":
						del line[tierName]
						lstContent = content.replace(BULLET_TAG, "").split("_")
						line[ LINE_BULLET ] = [int(lstContent[-2]), int(lstContent[-1])]

					if hasattr(self, f"_parse{tierName.capitalize()}" ):
						tierProcessFunction = getattr(self, f"_parse{tierName.capitalize()}" )
						line[tierName] = tierProcessFunction( line[tierName], line[LINE_NUMBER] )
			
			
			if not skipLine:
				self._setAddressee(line)

				if not (self.onlyCDS and line[LINE_ADDRESSEE] not in [SPEAKER_TARGET_CHILD, SPEAKER_BOTH]):
					if not speaker in self.ignoreSpeakers:
						if len(self.includeLines) == 0 or line[ LINE_NUMBER ] in self.includeLines:
							self.lines.append(line)
			
			lineNumber += r.count("\n")

		#if MOR is found on file all lines should have at least an empty TIER_MOR
		if self.morFound:
			for l in self.getLines():
				if TIER_MOR not in l:
					l[TIER_MOR] = []

	def _setAddressee(self, line):
		"""Internal use. Set normalized addressee 

		Args:
			line (dict): Utterance
		"""
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
				log.log(f"Warning unknown addressee '{line[TIER_XDS]}' in line '{line[LINE_NUMBER]}'")
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
		"""Returns number of utterances

		Returns:
			int: Number of utterances in the current transcript
		"""
		return len(self.lines)

	def countUtterancesByAddressee(self):
		"""Returns number of utterances grouped by addressee

		Returns:
			dict: Number of utterances by addressee
		"""
		addressees = {}

		for l in self.getLines():
			addressee = l[LINE_ADDRESSEE]
			if addressee in addressees:
				addressees[addressee] += 1
			else:
				addressees[addressee] = 1

		return addressees

	def countWordsByAddressee(self):
		"""Count words grouped by addressee

		Returns:
			dict: Number of words grouped by addresee
		"""
		assert self.morFound, "MOR tier not found"
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
		"""Number of words in the utterance

		Args:
			line (dict): A parsed utterance from getLines()

		Returns:
			int: Number of words in the utterance
		"""
		assert self.morFound, "MOR tier not found"
		dontCount = ["cm"] #no cuentes la coma

		c = 0
		for morUnit in line[TIER_MOR]:
			if morUnit != MISSING_VALUE and morUnit[MOR_UNIT_CATEGORIA] not in dontCount:
				c += 1

		return c

	def countNounsByAddressee(self):
		"""Number of nouns grouped by addressee

		Returns:
			dict: Addressees and number of nouns
		"""
		self.populateNouns()

		addressees = {}

		for l in self.getLines():
			c = len( l[LINE_NOUNS] )

			addressee = l[LINE_ADDRESSEE]
			if addressee in addressees:
				addressees[addressee] += c
			else:
				addressees[addressee] = c

		return addressees

	def getNounsInLine(self, linea):
		"""Returns a list of indexes of nouns in the MOR tier

		Args:
			linea (dict): Utterance

		Returns:
			list: List of indexes
		"""
		assert self.morFound, "MOR tier not found"
		
		if not self.processedVerbs:
			#in english, sometimes MOR mark as noun a word that is a verb
			self.populateVerbs()

		nouns = []

		if linea[TIER_MOR] != MISSING_VALUE: 	
			for i, morUnit in enumerate(linea[TIER_MOR]):
				if morUnit[MOR_UNIT_CATEGORIA] in CATEGORIAS_SUSTANTIVOS:
					if not i in linea[LINE_VERBS]: #in english, sometimes MOR mark as noun a word that is a verb
						nouns.append(i)
		
		return nouns

	def populateNouns(self):
		"""Populate LINE_NOUNS for every line with the indexes of the MOR line where nouns are found
		"""
		assert self.morFound, "MOR tier not found"

		if self.processedNouns: return
		
		if not self.processedVerbs:
			#in english, sometimes MOR mark as noun a word that is a verb
			self.populateVerbs()

		for linea in self.getLines():
			linea[LINE_NOUNS] = self.getNounsInLine(linea)
		
		self.processedNouns = True

	def countAdjectivesByAddressee(self):
		"""Number of adjectives grouped by addressee

		Returns:
			dict: Addressees and number of adjectives
		"""
		if not self.processedAdjectives:
			self.populateAdjectives()

		addressees = {}

		for l in self.getLines():
			c = len(l[LINE_ADJECTIVES])

			addressee = l[LINE_ADDRESSEE]
			if addressee in addressees:
				addressees[addressee] += c
			else:
				addressees[addressee] = c

		return addressees
	def getAdjectivesInLine(self, linea):
		"""Returns a list of indexes of adjectives in the MOR tier

		Args:
			linea (dict): Utterance

		Returns:
			list: List of indexes
		"""
		assert self.morFound, "MOR tier not found"
		adjetivos = []

		if linea[TIER_MOR] != MISSING_VALUE: 	
			for i, morUnit in enumerate(linea[TIER_MOR]):
				if morUnit[MOR_UNIT_CATEGORIA] in CATEGORIAS_ADJETIVOS:
					adjetivos.append(i)
		
		return adjetivos
	
	def populateAdjectives(self):
		"""Populate LINE_ADJECTIVES of every line with the indexes of the MOR tier where adjectives are found
		"""
		assert self.morFound, "MOR tier not found"
		
		if self.processedAdjectives: return

		for linea in self.getLines():
			linea[LINE_ADJECTIVES] = self.getAdjectivesInLine(linea)
		
		self.processedAdjectives = True

	def populateVerbs(self, countCopAux = False, processLightVerbs = True):
		"""Populate LINE_VERBS for every line with the indexes of the MOR tier where verbs are found

		Args:
			countCopAux (bool, optional): Should we count cop and aux as verbs ?. Defaults to False.
			processLightVerbs (bool, optional): Should we process light verbs. Defaults to True.
		"""
		if self.processedVerbs: return

		for l in self.getLines():
			self.getVerbsInLine(l, countCopAux, processLightVerbs)
		
		self.processedVerbs = True

	def _processLightVerbs(self, lineaMor, verbos):
		"""Internal use. Language dependent. Process light verbs to be skipped when counting verbs

		Args:
			lineaMor (dict): MOR tier for an utterance. Note that it is a dict, not a list
			verbos (list): List of verbs

		Returns:
			list: MOR tier without light verbs
		"""
		if self.language == LANGUAGE_SPANISH:
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
				[["debe"]],
				[["habe"],["que"]],
				[["esta"],["por"]],
				
				#[["deja"],["de"]],    #estos que comenté son los que cambiamos cuando hicimos aclew completo
				
				#[["acaba"],["de"]],
				#[["termina"],["de"]],

				#[["empeza"],["a"]],
				#[["empeza"],["por"]],

				#[["comienzo"],["a"]],
				#[["comenza"],["a"]],

				#[["pone"],["a"]],
				#[["volve"],["a"]]
			]

			siguiente_palabra_de_auxiliar = [ "inf", "ger", "part" ]

			#4) Cuando es copulativo + gerundio contar el gerundio
			#5) Cuando es copulativo + participio contar el participio.

			criteriosCategoria = [
					[ ["cop"],["ger","part"] ]
			]

			#6) No contar el copula o auxiliar si está solo (1versión) / contar el cópula o el auxiliar si esta sólo (2 versión)
			#countCopAux = False # Hago los dos mas abajo

			#7) En los casos de 2 o 3 Verbos (verbos conjugado, infinitivo, gerundio o participio), contar el que no es ni auxiliar, ni copula.
			#estoy contando frase verbal + verbo final

			#8) si hay 2 o más verbos conjugados coordinados en una emisión se toman todos.

			#1) 2) y 3) auxiliares    aux + (inf,ger,part)

			for raiz in raices:
				criteriaType = [ MOR_UNIT_LEXEMA for c in raiz ]
				criteria = raiz + [siguiente_palabra_de_auxiliar]
				criteriaType.append(MOR_UNIT_CATEGORIA)
				morIndexes = self._checkCriteria( list(lineaMor.values()), criteria, criteriaType )
				# existe el patron
				while len(morIndexes) > 0:
					#agarro la última palabra y la agrego como verbo
					trueIndex = list(lineaMor.keys())[ morIndexes[-1] ]
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
					verbos.append( trueIndex )

					trueIndexesToDelete = []
					for morIndex in morIndexes:
						trueIndexesToDelete.append( list(lineaMor.keys())[ morIndex ] )
					for i in trueIndexesToDelete:
						del lineaMor[ i ]

					morIndexes = self._checkCriteria( list(lineaMor.values()), criterio, MOR_UNIT_CATEGORIA )
		elif self.language == LANGUAGE_ENGLISH:		
			criterias = [
				[["part|go"], ["to"], ["n", *CATEGORIAS_VERBOS]],
				[["part|go"], ["n", *CATEGORIAS_VERBOS]], #gonna
				[["go"], [*CATEGORIAS_VERBOS]],
				[["have"], ["to"], [*CATEGORIAS_VERBOS]],
				[["do"], [*CATEGORIAS_VERBOS]],
				[["do"],["not"],[*CATEGORIAS_VERBOS]],
				[["use"], ["to"], [*CATEGORIAS_VERBOS]],



				# [["like"], ["to"], [*CATEGORIAS_VERBOS]], # se decidió no agregarla
				# [["want"], ["to"], [*CATEGORIAS_VERBOS]], # se decidió no agregarla
				# [["try"], ["to"], [*CATEGORIAS_VERBOS]], # se decidió no agregarla
			]

			for criteria in criterias:
				criteriaType = [ MOR_UNIT_LEXEMA if "|" not in c[0] else MOR_UNIT_CATEGORIA_LEXEMA for c in criteria ]
				del criteriaType[-1]
				criteriaType.append(MOR_UNIT_CATEGORIA)

				morIndexes = self._checkCriteria( list(lineaMor.values()), criteria, criteriaType )
				# existe el patron
				while len(morIndexes) > 0:
					#agarro la última palabra y la agrego como verbo
					trueIndex = list(lineaMor.keys())[ morIndexes[-1] ]
					verbos.append( trueIndex )

					trueIndexesToDelete = []
					for morIndex in morIndexes:
						trueIndexesToDelete.append( list(lineaMor.keys())[ morIndex ] )
					for i in trueIndexesToDelete:
						del lineaMor[ i ]

					criteriaType = [ MOR_UNIT_LEXEMA if "|" not in c else MOR_UNIT_CATEGORIA_LEXEMA for c in criteria ]
					del criteriaType[-1]
					criteriaType.append(MOR_UNIT_CATEGORIA)
					morIndexes = self._checkCriteria( list(lineaMor.values()), criteria, criteriaType )
			
			# Don't count LET'S as a verb
			stopWords = [
				{MOR_UNIT_CATEGORIA: 'v', MOR_UNIT_LEXEMA: 'let', MOR_UNIT_EXTRA: '~pro:obj|us'}
			]

			trueIndexesToDelete = []
			for i in lineaMor:
				morUnit = lineaMor[i]
				if morUnit in stopWords:
					trueIndexesToDelete.append(i)
			for i in trueIndexesToDelete:
				del lineaMor[ i ]
			
		return lineaMor

	def getVerbsInLine(self, linea, countCopAux = False, processLightVerbs = True ):
		"""Gets verbs in line and store them in LINE_VERBS

		Args:
			linea (dict): Utterance from getLines()
			countCopAux (bool, optional): Should we count cop and aux. Defaults to False.
			processLightVerbs (bool, optional): Should we skip light verbs. Defaults to True.

		Returns:
			list: Array of indexes to verbs
		"""
		verbos = []
		# no se borra nada del MOR original
		lineaMor={}
		for i, m in enumerate(linea[TIER_MOR]):
			lineaMor[i] = m

		if processLightVerbs:
			assert self.language != None, "language not set"
			lineaMor = self._processLightVerbs(lineaMor, verbos)

		if len(lineaMor) != len(linea[TIER_MOR]):
			linea[LINE_LIGHT_VERBS] = True

		#verbos normales
		verbosIndividualesAContar = CATEGORIAS_VERBOS.copy()

		if not countCopAux:
			verbosIndividualesAContar.remove("cop")
			verbosIndividualesAContar.remove("aux")
		
		if self.language == LANGUAGE_ENGLISH:
			verbosIndividualesAContar.remove("inf") #esto saca el to

		morIndexes = self._checkCriteria( list(lineaMor.values()), [ verbosIndividualesAContar ], MOR_UNIT_CATEGORIA )
		while len(morIndexes) > 0:
			trueIndex = list(lineaMor.keys())[ morIndexes[0] ]
			verbos.append( trueIndex )

			trueIndexesToDelete = []
			for morIndex in morIndexes:
				trueIndexesToDelete.append( list(lineaMor.keys())[ morIndex ] )
			for i in trueIndexesToDelete:
				del lineaMor[ i ]

			morIndexes = self._checkCriteria( list(lineaMor.values()), [ verbosIndividualesAContar ], MOR_UNIT_CATEGORIA )

		linea[LINE_VERBS] = verbos
		linea[LINE_VERBS].sort()
		
		return verbos

	def countVerbsByAddressee(self, countCopAux = False, processLightVerbs = True):
		"""Number of verbs grouped by addressee
		Args:
			countCopAux (bool, optional): Should we count cop and aux. Defaults to False.
			processLightVerbs (bool, optional): Should we skip light verbs. Defaults to True.
		Returns:
			dict: Addressees and number of verbs
		"""
		addressees = {}

		if not self.processedVerbs:
			self.populateVerbs(countCopAux=countCopAux, processLightVerbs=processLightVerbs)

		for l in self.getLines():
			c = len( l[LINE_VERBS] )

			addressee = l[LINE_ADDRESSEE]
			if addressee in addressees:
				addressees[addressee] += c
			else:
				addressees[addressee] = c

		return addressees
	
	def count(self, what, addressee=ADDRESSEE_ALL, countType=COUNT_TYPE_TOKENS, countCopAux = False, processLightVerbs = True):
		"""Count tokens or types of nouns, verbs or adjectives

		Args:
			what ([type]): LINE_VERBS, LINE_NOUNS or LINE_ADJECTIVES
			addressee ([type], optional): ADDRESSEE_ALL, ADDRESSEE_CHILD_DIRECTED, ADDRESSEE_OVER_HEARD or ADDRESSEE_CHILD_PRODUCED. Defaults to ADDRESSEE_ALL.
			countType ([type], optional): COUNT_TYPE_TOKENS or COUNT_TYPE_TYPES. Defaults to COUNT_TYPE_TOKENS.
			countCopAux (bool, optional): Should we count cop and aux as verbs ?. Defaults to False.
			processLightVerbs (bool, optional): Should we process light verbs. Defaults to True.
			
		Returns:
			int: count
		"""

		if what not in [ LINE_VERBS, LINE_NOUNS, LINE_ADJECTIVES ]:
			raise "'what' argument should be LINE_VERBS, LINE_NOUNS or LINE_ADJECTIVES"

		if what == LINE_VERBS:
			self.populateVerbs(countCopAux=countCopAux, processLightVerbs=processLightVerbs)
		elif what == LINE_NOUNS:
			self.populateNouns()
		elif what == LINE_ADJECTIVES:
			self.populateAdjectives()
		
		c = {}
		
		def add(l):
			nonlocal c

			for index in l[what]:
				v = l[TIER_MOR][index][MOR_UNIT_LEXEMA]
				if v in c:
					c[v] += 1
				else:
					c[v] = 1
		
		if addressee == ADDRESSEE_ALL:
			for l in self.getLines():
				add( l )
		elif addressee == ADDRESSEE_CHILD_DIRECTED:
			for l in self.getLines():
				if l[LINE_ADDRESSEE] == SPEAKER_TARGET_CHILD:
					add( l )
		elif addressee == ADDRESSEE_CHILD_PRODUCED:
			for l in self.getLines():
				if l[LINE_SPEAKER] == SPEAKER_TARGET_CHILD:
					add( l )
		elif addressee == ADDRESSEE_OVER_HEARD:
			for l in self.getLines():
				if l[LINE_ADDRESSEE] != SPEAKER_TARGET_CHILD and l[LINE_SPEAKER] != SPEAKER_TARGET_CHILD :
					add( l )
		
		# print(c)

		if countType == COUNT_TYPE_TOKENS:
			return sum(c.values())
		else:
			return len(c.keys())

	def findLinesByMorCriteria(self, criteria, criteriaType=MOR_UNIT_CATEGORIA):
		"""Finds utterances that follow a criteria

		Args:
			criteria (list): Criteria. Example: [ ["part_of_speech-1"], [ [ "part_of_speech-1","part_of_speech-2 ] ] ]. 
			An utterance will match if it contains two adjacent words: one with "part_of_speech-1" and the second one "part_of_speech-1" or "part_of_speech-2"
			criteriaType (str or list, optional): Search for part-of-speech (categoria léxica) or lexeme. If using a list it must have the same number of elements as criteria. Defaults to MOR_UNIT_CATEGORIA. MOR_UNIT_CATEGORIA_LEXEMA matches "<part_of_speech>|<lexeme>"

		Returns:
			list: List of dict with line and matched criteria
		"""
		results = []

		assert self.morFound, "MOR tier not found"
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

	def applyMorCriteriaInLine(self, line, criteria, criteriaType = MOR_UNIT_CATEGORIA):
		"""Same as findLinesByMorCriteria but for one line

		Args:
			line (dict): Utterance
			criteria (list): [description]
			criteriaType (str or list, optional): [description]. Defaults to MOR_UNIT_CATEGORIA.

		Returns:
			list: List of indexes of the words matching the criteria
		"""
		return self._checkCriteria( line["mor"], criteria, criteriaType )

	def _checkCriteria(self, mor, criteria, criteriaType):
		"""Internal use. Checks the MOR tier for the criteria (just once)

		Args:
			mor (list): MOR tier
			criteria (list): Same as findLinesByMorCriteria
			criteriaType (str or list): Same as findLinesByMorCriteria

		Returns:
			list: List of indexes of the words matching the criteria
		"""
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
				currentCriteriaType = criteriaType

				if isinstance(criteriaType, list):
					currentCriteriaType = criteriaType[currentCriteria]
				
				if currentCriteriaType == MOR_UNIT_CATEGORIA_LEXEMA:
					if not "|" in c:
						raise "Criteria type is MOR_UNIT_CATEGORIA_LEXEMA but criteria doesn't include | symbol"
					
					arrCriteria = c.split("|")

					isAMatch = morUnit[ MOR_UNIT_LEXEMA ] == arrCriteria[1] and morUnit[ MOR_UNIT_CATEGORIA ] == arrCriteria[0]
				else:
					isAMatch = morUnit[ currentCriteriaType ] == c
					
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

	def fixDAD(self):
		"""Choose only one type of activity per utterance when many were coded
		"""
		for l in self.getLines():
			if l[TIER_ACTIVITY] == MISSING_VALUE:
				if l[LINE_ADDRESSEE] == SPEAKER_TARGET_CHILD:
					log.log("Warning. Empty activity in +CHI line (%d)" % l[LINE_NUMBER])
				continue
			maxDAD = l[TIER_ACTIVITY][0]
			for dad in l[TIER_ACTIVITY]:
				if TIER_ACTIVITY_SCORES[dad] > TIER_ACTIVITY_SCORES[maxDAD]:
					maxDAD = dad

			l[TIER_ACTIVITY] = maxDAD
