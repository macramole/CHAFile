from ChaFile import *
from glob import glob
import os

# chaPaths = glob("/home/macramole/Code/ciipme/aclew/highvolResults/listos_cha/*.cha")
# chaPaths = glob("/home/macramole/Code/ciipme/aclew/highVolFromGit/allCHA/eng/*.cha")
chaPaths = glob("/media/leandro/stuff/Code/isolci/corpus_bebes/longi_audio1/codificados/codificados bullets elan/*.cha")

# chaPath = "/home/macramole/Code/ciipme/aclew/highvolResults/listos_cha/donatow-a1-nsm.elan.cha"
# chaPath = "/home/macramole/Code/ciipme/corpusESPON/longi_audio1/codificados/codificados bullets elan/alma-a1-nsb.cha"
# cha = ChaFile( chaPath, language=LANGUAGE_SPANISH )

for c in chaPaths:
    print(os.path.basename(c))
    cha = ChaFile( c, language=LANGUAGE_SPANISH )
    # cha = ChaFile( c, language=LANGUAGE_ENGLISH )
    print(cha.getMLU(), " / ", cha.getMLU(ADDRESSEE_CHILD_DIRECTED))


