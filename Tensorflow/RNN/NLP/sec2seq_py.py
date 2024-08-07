# -*- coding: utf-8 -*-
"""Sec2Seq.py

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1zZTnmxzkeWEW8k9r5HCWaVqdQKmDcBXK
"""

from __future__ import print_function, division
from builtins import range , input

import os

from keras.models import Model
from keras.layers import Input, Dense, GRU, LSTM, Embedding
from keras.preprocessing.sequence import pad_sequences
from keras.preprocessing.text import Tokenizer
from keras.utils import to_categorical

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

Batch_size = 64
epochs = 20
latent_dim = 256
num_samples = 10000
max_squence_len = 100
max_num_words = 20000
embedding_dim = 100

input_texts = [] #input sentence
target_texts = [] # output sentence
target_texts_input = [] # output sentece with <sos> and <eos>

i = 0
db = pd.read_csv('/content/drive/MyDrive/NLP/DB/pes.txt',sep='\t',header=None )
db.drop(2, axis=1, inplace=True)
for index, row in db.iterrows(): # Iterate over DataFrame rows
  i += 1
  if i > num_samples:
    break

  input_text, trans = row[0], row[1] # Access row elements
  target_text = trans + '<eos>'
  target_text_input = '<sos>' + trans.strip()

  input_texts.append(input_text)
  target_texts.append(target_text)
  target_texts_input.append(target_text_input)

db.head()

print('Number of samples:', len(input_texts))

# max_num_words is the maximum number of words to keep, based on word frequency

# Tokenizing the input sequences
# Create a Tokenizer object with a specified number of words
tokenizer = Tokenizer(num_words=max_num_words)

# Fit the tokenizer on the input texts to build the vocabulary
tokenizer.fit_on_texts(input_texts)

# Convert the input texts to sequences of integers
input_sequences = tokenizer.texts_to_sequences(input_texts)

# Create a dictionary mapping words to their integer indices
word2idx = tokenizer.word_index
print('Found %s unique tokens.' % len(word2idx))

# Determine the maximum length of the input sequences
max_len_input = max(len(s) for s in input_sequences)

# max_num_words is the maximum number of words to keep, based on word frequency

# Tokenizing the output sequences
# Create a Tokenizer object with a specified number of words and no filters
tokenizer_outputs = Tokenizer(num_words=max_num_words, filters='')

# Fit the tokenizer on the combined target texts (both target and target input texts)
tokenizer_outputs.fit_on_texts(target_texts + target_texts_input)

# Convert the target texts to sequences of integers
target_sequences = tokenizer_outputs.texts_to_sequences(target_texts)
target_sequences_inputs = tokenizer_outputs.texts_to_sequences(target_texts_input)

# Create a dictionary mapping words to their integer indices
word2idx_outputs = tokenizer_outputs.word_index
print('Found %s unique tokens.' % len(word2idx_outputs))

# Add 1 to the number of unique words to account for padding or special tokens
num_words_output = len(word2idx_outputs) + 1

# Determine the maximum length of the target sequences
max_len_target = max(len(s) for s in target_sequences)

# Padding input/ encoder

encoder_input = pad_sequences(input_sequences, maxlen=max_len_input)
print('Shape of input tensor:', encoder_input.shape)

# padding decoder
# Padding the target sequences for the decoder. This ensures all sequences have the same length by adding padding
# at the end ('post'). This is important for batch processing in models.
decoder_targets = pad_sequences(target_sequences, maxlen=max_len_target, padding='post')
print('Shape of target tensor:', padding_target.shape)

# Padding the input sequences for the decoder. Similar to the above, this ensures all sequences have the same length
# by adding padding at the end ('post').
decoder_inputs = pad_sequences(target_sequences_inputs, maxlen=max_len_target, padding='post')
print('Shape of decoder input tensor:', decoder_input.shape)

# store pretrained words

word2vec = {} # Dictionary to hold word and its corresponding vector

# Define the path template with a placeholder for embedding dimension
gn_vec_path_template = 'path/to/your/vector/file_%d.txt'

with open(os.path.join(gn_vec_path_template % embedding_dim)) as f: # Open the file and read line by line

  for line in f:
    values = line.split() # Split the line into word and vector components

    word = values[0] # The first value is the word
    vec = np.asarray(values[1:], dtype='float32')# The remaining values are the vector components, converted to float32
    word2vec[word] = vec # Store the word and vector in the dictionary

# Determine the number of words to include in the embedding matrix
num_words = min(max_num_words, len(word2idx) + 1)
"""
The +1 in the line num_words = min(max_num_words, len(word2idx) + 1) is added to account for the possibility of including a special token, such as a padding or unknown token, that might not be explicitly listed in word2idx.

Here's a more detailed breakdown:

  len(word2idx): This gives the number of unique words in the word2idx dictionary.
  +1: Adding 1 ensures that there is an extra index available, which is often used for a special token. For example:
  Padding token (<PAD>): Used to pad sequences to the same length.
  Unknown token (<UNK>): Used for words that are not found in the word2idx dictionary.
  By adding 1, the code ensures that there is an index available for such a token,
  thus allowing the embedding matrix to accommodate this additional entry.

"""

# Initialize the embedding matrix with zeros
embedding_matrix = np.zeros((num_words, embedding_dim))

# Iterate over the word-to-index dictionary
for word, i in word2idx.items():
    # Check if the index is less than the maximum number of words
    if i < max_num_words:
        # Get the embedding vector for the word from the word2vec model
        embedding_vector = word2vec.get(word)
        # If the embedding vector exists, add it to the embedding matrix at the corresponding index
        if embedding_vector is not None:
            embedding_matrix[i] = embedding_vector

embedding_layer = Embedding(num_words,
                            embedding_dim,
                            weights=[embedding_matrix],
                            input_length=max_len_input,
                            trainable=False)

# Create a one-hot encoded targets matrix, because we cannot use sparse categorical cross entropy with sequences
# Initialize the matrix with zeros
# Shape of the matrix: (number of target sequences, maximum length of target sequence, number of possible output words)

decoder_targets_one_hot = np.zeros((len(decoder_targets), max_len_target, num_words_output), dtype='float32')

"""
Sparse categorical cross entropy is typically used when dealing with single-label classification problems where each label is an integer.
It expects the targets to be integers representing the class indices. This works well for non-sequential data where each data point corresponds to a single class.

However, when dealing with sequences, such as in sequence-to-sequence models,
the target is a sequence of integers, not a single integer. In these cases,
there are a few reasons why sparse categorical cross entropy might not be suitable:

Shape of the Targets:
For sequences, the targets are usually a 2D array (or 3D if you include batch size),
 where each element in the sequence is a class index. This requires a different handling compared to single-label classification.

One-Hot Encoding Requirement:
Sparse categorical cross entropy expects the targets to be a single integer per sample,
representing the class index directly. However, in sequence-to-sequence tasks,
we often need to work with one-hot encoded vectors to handle the full sequence properly.
One-hot encoding transforms the class index into a binary vector where only the index of the target class is 1,
and the rest are 0s. This allows for more straightforward computation of the loss over the entire sequence.

Compatibility with Model Output:
The output of sequence models, especially in tasks like translation or text generation,
is typically a sequence of probability distributions over the vocabulary for each time step.
To compute the cross entropy loss correctly, we need the target in a format that matches this output shape,
which is why we use one-hot encoding.

"""

# Iterate over each sequence in the decoder targets
for i, target in enumerate(decoder_targets):
    # Iterate over each word in the target sequence
    for t, word in enumerate(target):
        # Check if the word index is greater than 0 (usually 0 is reserved for padding)
        if word > 0:
            # Set the corresponding position in the one-hot encoded matrix to 1.0
            decoder_targets_one_hot[i, t, word] = 1.0

emcoder_inputs_placeholder = Input(shape=(max_len_input,))
x = embedding_layer(encoder_inputs_placeholder)
encoder = LSTM(latent_dim, return_state=True) # dopout = 0.2
encoder_outputs, state_h, state_c = encoder(x)

encoder_states = [state_h, state_c]

decoder_input_placeholder = Input(shape=(max_len_target,))
decoder_embedding = Embedding(num_words_output, latent_dim)
decoder_input_x = decoder_embedding(decoder_input_placeholder)
decoder_lstm = LSTM(latent_dim, return_sequences=True, return_state=True)
decoder_outputs, _, _ = decoder_lstm(decoder_input_x, initial_state=encoder_states)

decoder_dense = Dense(num_words_output, activation='softmax')
decoder_outputs = decoder_dense(decoder_outputs)

model = Model([encoder_inputs_placeholder, decoder_input_placeholder], decoder_outputs)
model.compile(optimizer='rmsprop', loss='categorical_crossentropy', metrics=['accuracy'])
results = model.fit([encoder_input, decoder_inputs], decoder_targets_one_hot,
                    batch_size=Batch_size,
                    epochs=epochs,
                    validation_split=0.2)

plt.plot(results.history['loss'], label='Training Loss')
plt.plot(results.history['val_loss'], label='Validation Loss')
plt.legend()
plt.show()


plt.plot(results.history['accuracy'], label='Training Accuracy')
plt.plot(results.history['val_accuracy'], label='Validation Accuracy')
plt.legend()
plt.show()

#save the model

model.save('NLP_model.h5')

encoder_model = Model(encoder_inputs_placeholder, encoder_states)
decoder_state_input_h = Input(shape=(latent_dim,))
decoder_state_input_c = Input(shape=(latent_dim,))
decoder_states_inputs = [decoder_state_input_h, decoder_state_input_c]

decoder_inputs_single = Input(shape=(1,))
decoder_inputs_single_x = decoder_embedding(decoder_inputs_single)

decoder_outputs, state_h, state_c = decoder_lstm(decoder_inputs_single_x, initial_state=decoder_states_inputs)
decoder_states = [state_h, state_c]
decoder_outputs = decoder_dense(decoder_outputs)

decoder_model = Model([decoder_inputs_single] + decoder_states_inputs, [decoder_outputs] + decoder_states)

idx2word_input = {v:k for k, v in word2idx.items()}
idx2word_target = {v:k for k, v in word2idx_outputs.items()}

def decode_sequence(input_seq):
    # Encode the input sequence into state
    states_value = encoder_model.predict(input_seq)
    target_seq = np.zeros((1, 1))
    target_seq[0, 0] = word2idx['<sos>']
    eos = word2idx['<eos>']
    output_sentence = []
    for i in range(max_len_target):
        output_tokens, h, c = decoder_model.predict([target_seq] + states_value)
        idx = np.argmax(output_tokens[0, -1, :])
        if eos == idx:
            break
        output_sentence.append(idx2word_target[idx])

        word = ''
        if idx > 0:
            word = idx2word_target[idx]
            target_seq[0, 0] = idx
        states_value = [h, c]
    return ' '.join(output_sentence)
  while True:
    i = np.random.choice(len(input_texts))
    input_seq = encoder_input[i: i + 1]
    decoded_sentence = decode_sequence(input_seq)
    print('-')
    print('Input sentence:', input_texts[i])
    print('Target sentence:', target_texts[i])
    print('Predicted translation:', decoded_sentence)
    ans = input('Do you want to continue? (y/n): ')
    if ans.lower() != 'y':
      break

