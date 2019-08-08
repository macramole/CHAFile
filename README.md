
[![DOI](https://zenodo.org/badge/201303243.svg)](https://zenodo.org/badge/latestdoi/201303243)


# CHA file parser for Python

Class for parsing [CLAN's](http://dali.talkbank.org/clan/) CHA file.

Made by Leandro Garber from [CIIPME-CONICET](http://www.ciipme-conicet.gov.ar/wordpress/)

## Features
* Utterances as a list of strings
* MOR tier as objects
* Easily add more custom tiers 
* Count nouns
* Count main verbs, either referring to physical or mental actions. Auxiliary verbs present in periphrastic verbs are excluded. (spanish only)

## Usage

Make a symlink (ln -s) to CLAN's bin directory called "clanBin".

### Import
```python
import sys
sys.path.insert(0, '<path_to_cloned_repo>')

import ChaFile
```

### Instance

```python
cha = ChaFile.ChaFile(<path_to_cha_file>)
```
Options
   
```python
cha = ChaFile.ChaFile(<path_to_cha_file>, <list_of_ignored_speakers> = [ SPEAKER_SILENCE ], <list_of_tiers> = [ TIER_MOR ], CDS_ONLY = False )
```
### Get utterances
```python
lines = cha.getLines()
```
Each line is an object with:
* LINE_UTTERANCE : The text of the utterance
* LINE_NUMBER 
* LINE_SPEAKER
* LINE_ADDRESSEE
* LINE_BULLET : Timestamp
* TIER_MOR : A list of objects with MOR data: MOR_UNIT_LEXEMA and MOR_UNIT_CATEGORIA
* ... any other tier you selected when instanced
