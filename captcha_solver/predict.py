from .model import Build_Model, CTCLayer
import tensorflow as tf
import numpy as np
from tensorflow.keras import backend as K
from tensorflow.keras.models import Model
Characters = set('0123456789abcdefghijkmnopqrstuvwxyz')
from tensorflow.keras import layers

img_width = 144
img_height = 48

char_to_num = layers.experimental.preprocessing.StringLookup(
                  vocabulary=sorted(list(Characters)), num_oov_indices=0, mask_token=None )

# Mapping integers back to original characters
num_to_char = layers.experimental.preprocessing.StringLookup(
                  vocabulary=char_to_num.get_vocabulary(), num_oov_indices=1, mask_token=None, invert=True )
def encode_single_sample( img_path ):
    # 1. Read image
    img = tf.io.read_file( img_path )
    # 2. Decode and convert to grayscale
    img = tf.io.decode_png( img, channels=1 )
    # 3. Convert to float32 in [0, 1] range
    img = tf.image.convert_image_dtype( img, tf.float32 )
    # 4. Resize to the desired size
    img = tf.image.resize( img, [img_height,img_width] )
    # 5. Transpose the image because we want the time dimension to correspond to the width of the image, 
    #    i.e., shape = (img_weight,img_height,1).
    img = tf.transpose( img, perm=[1,0,2] )
    # 6. Map the characters in label to numbers
    # 7. Return a dict as our model is expecting two inputs
    return { "image": tf.expand_dims(img,0)}

def decode_batch_predictions(pred):
    input_len = np.ones(pred.shape[0]) * pred.shape[1]
    # Use greedy search. For complex tasks, you can use beam search
    results = K.ctc_decode(pred, input_length=input_len, greedy=True)[0][0][:,:4]
    # Iterate over the results and get back the text
    output_text = []
    for res in results:
        res = tf.strings.reduce_join(num_to_char(res)).numpy().decode('utf-8')
        output_text.append(res)
    return output_text


model = Build_Model()
model.load_weights("captcha_solver/CRNN.h5")
prediction_model = Model( model.get_layer( name='image' ).input, model.get_layer( name='Softmax' ).output, name='Prediction' )

def pred(path):
    inp = encode_single_sample(path)
    pred = prediction_model.predict(inp)
    res = decode_batch_predictions(pred)[0]
    return res
