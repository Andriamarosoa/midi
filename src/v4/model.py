from __future__ import annotations
from typing import Any
import math

def _get(config:Any,name:str,default): return config.get(name,default) if isinstance(config,dict) else getattr(config,name,default)

def build_pitch_model(config:Any,pitch_classes:int):
    import tensorflow as tf
    samples=int(_get(config,'input_samples',4096)); channels=int(_get(config,'channels',32)); blocks=int(_get(config,'tcn_blocks',4)); dropout=float(_get(config,'dropout',.2)); dense=int(_get(config,'dense_units',128)); pooling=str(_get(config,'pooling','hybrid')).lower()
    audio=tf.keras.Input((samples,1),name='audio'); mask=tf.keras.Input((samples,),name='time_mask')
    expanded=tf.keras.layers.Reshape((samples,1),name='expand_time_mask')(mask); x=tf.keras.layers.Multiply(name='apply_time_mask')([audio,expanded])
    x=tf.keras.layers.Conv1D(channels,9,strides=4,padding='causal',activation='swish',name='frontend_conv_1')(x); x=tf.keras.layers.LayerNormalization(name='frontend_norm_1')(x)
    width=channels*2; x=tf.keras.layers.Conv1D(width,7,strides=4,padding='causal',activation='swish',name='frontend_conv_2')(x); x=tf.keras.layers.LayerNormalization(name='frontend_norm_2')(x)
    for i in range(blocks):
        residual=x; y=tf.keras.layers.Conv1D(width,3,dilation_rate=2**i,padding='causal',activation='swish',name=f'tcn_{i}_conv_1')(x); y=tf.keras.layers.Dropout(dropout,name=f'tcn_{i}_dropout')(y); y=tf.keras.layers.Conv1D(width,3,dilation_rate=2**i,padding='causal',name=f'tcn_{i}_conv_2')(y); x=tf.keras.layers.Add(name=f'tcn_{i}_add')([residual,y]); x=tf.keras.layers.LayerNormalization(name=f'tcn_{i}_norm')(x); x=tf.keras.layers.Activation('swish',name=f'tcn_{i}_activation')(x)
    steps=math.ceil(math.ceil(samples/4)/4); last=tf.keras.layers.Cropping1D((0,steps-1),name='last_causal_step')(x); last=tf.keras.layers.Flatten(name='last_causal_state')(last); avg=tf.keras.layers.GlobalAveragePooling1D(name='global_average_state')(x)
    pooled=tf.keras.layers.Concatenate(name='hybrid_pool')([last,avg]) if pooling=='hybrid' else last if pooling=='last' else avg
    pooled=tf.keras.layers.Dense(dense,activation='swish',name='pitch_dense')(pooled); pooled=tf.keras.layers.Dropout(dropout,name='pitch_dropout')(pooled); output=tf.keras.layers.Dense(pitch_classes,activation='softmax',name='pitch')(pooled)
    return tf.keras.Model({'audio':audio,'time_mask':mask},output,name='mono_pitch_v4')
