import os

TEMPLATEFLOW_HOME=os.path.abspath("./TemplateFlow")
os.environ["TEMPLATEFLOW_HOME"]=TEMPLATEFLOW_HOME

from templateflow import api as tf
tf.get("MNI152NLin2009cAsym")
tf.get("MNI152NLin6Asym")
tf.get("tpl-fsLR")
tf.get("tpl-fsaverage")