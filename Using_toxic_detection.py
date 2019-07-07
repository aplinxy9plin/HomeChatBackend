import pandas as pd
from io import StringIO
import pickle
from tensorflow.keras.preprocessing import sequence
from tensorflow.keras.models import Model, load_model
from tensorflow.keras import Input
from tensorflow.keras.layers import Dense, Embedding, GlobalMaxPooling1D
from tensorflow.keras.preprocessing.text import Tokenizer
from tensorflow.keras.optimizers import Adam

max_features = 20000  # number of words we want to keep
maxlen = 100  # max length of the comments in the model
batch_size = 64  # batch size for the model
embedding_dims = 20  # dimension of the hidden variable, i.e. the embedding dimension

with open('tokenizer.pickle', 'rb') as handle:
    tok = pickle.load(handle)

model = load_model('Simple_toxic_detection.h5')

def get_pred_string(input_string):
    TESTDATA = StringIO(input_string)
    my_string = pd.read_csv(TESTDATA, sep = '/n' , header = None, squeeze = True)
    my_string = tok.texts_to_sequences(my_string)
    my_string = sequence.pad_sequences(my_string, maxlen=maxlen)
    #["toxic", "severe_toxic", "obscene", "threat", "insult", "identity_hate"]
    return(model.predict(my_string))

#print(get_pred_string('punk ass motherfucker bitch'))

