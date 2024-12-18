from ChaFile import *
from glob import glob
import os

chaPaths = glob("/home/macramole/Code/isolci/corpus_bebes/longi_audio1/codificados/codificados bullets elan/*.cha")
# chaPaths = glob("/home/macramole/Code/ciipme/aclew/highvolResults/listos_cha/*.cha")
# chaPaths = glob("/home/macramole/Code/ciipme/aclew/highVolFromGit/allCHA/eng/*.cha")

# chaPath = "/home/macramole/Code/ciipme/aclew/highvolResults/listos_cha/donatow-a1-nsm.elan.cha"
# chaPath = "/home/macramole/Code/ciipme/corpusESPON/longi_audio1/codificados/codificados bullets elan/alma-a1-nsb.cha"
# cha = ChaFile( chaPath, language=LANGUAGE_SPANISH )

#for c in chaPaths:
    #cha = ChaFile( c, language=LANGUAGE_SPANISH )
    # cha = ChaFile( c, language=LANGUAGE_ENGLISH )
    #print(cha.countUtterances(False), " / ", cha.countUtterances(True))

path = "/home/macramole/Code/isolci/corpus_bebes/longi_audio1/codificados/codificados bullets elan/alma-a1-nsb.cha"
cha = ChaFile( path, language=LANGUAGE_SPANISH, onlyCDS=True )
# lines = cha.getLinesBySpeakers()

# for speaker in lines:
#     count = 0
#     for line in lines[speaker]:
#         if len(line[TIER_MOR]) > 0 and not " xxx" in line[LINE_UTTERANCE]:
#             # print(line[LINE_UTTERANCE])
#             count += 1
    
#     print(f"{speaker}: {count}")

print( cha.getLinguisticProductivity(ADDRESSEE_CHILD_DIRECTED) )

# print()

# for line in cha.getLines():
#     if line[LINE_SPEAKER] == "NIN":
#         print(line[LINE_UTTERANCE])
#         print(line[TIER_MOR])
#         print()


# for path in chaPaths:
#     cha = ChaFile( path, language=LANGUAGE_SPANISH )
#     # print(cha.countUtterances(ADDRESSEE_CHILD_DIRECTED))
#     # print(len(cha.getLines(ADDRESSEE_CHILD_DIRECTED)))
#     cant_utt = 0
#     cant_mor = 0

#     for l in cha.getLines(ADDRESSEE_CHILD_DIRECTED):
#         # if len(l[TIER_MOR]) > 0:
#             # if len(l[TIER_MOR]) == 1:
#             #     if l[TIER_MOR][0][MOR_UNIT_CATEGORIA] == "co":
#             #         continue
            
#         cant_utt += 1
#         cant_mor += len(l[TIER_MOR])

#             # if len(l[TIER_MOR]) == 1:
#             #     print( l[LINE_UTTERANCE] )
#             #     print( l[TIER_MOR] ) 
#             #     print()
        
#     print(os.path.basename(path))
#     print(f"{cant_utt} | {cant_mor} = {cant_mor/cant_utt}")