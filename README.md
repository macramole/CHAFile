# CHA file parser for Python

Class for parsing [CLAN's](http://dali.talkbank.org/clan/) CHA file.

## Features
* Utterances as a list of strings
* MOR tier as objects
* Easily add more custom tiers 
* Count nouns
* Count verbs (spanish only)

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
