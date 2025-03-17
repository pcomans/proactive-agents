#!/usr/bin/env python
import pika
import random

# Sample words for each topic
words = ['sunset', 'moonlight', 'whisper', 'breeze', 'dream']

connection = pika.BlockingConnection(
    pika.ConnectionParameters(host='localhost'))
channel = connection.channel()

channel.exchange_declare(exchange='agent_exchange', exchange_type='topic')

# Send to joke topic
joke_word = random.choice(words)
channel.basic_publish(
    exchange='agent_exchange', 
    routing_key='jokes.random',
    body=joke_word
)
print(f" [x] Sent jokes.random:{joke_word}")

# Send to poem topic
poem_word = random.choice(words)
channel.basic_publish(
    exchange='agent_exchange', 
    routing_key='poems.random',
    body=poem_word
)
print(f" [x] Sent poems.random:{poem_word}")

# Send to limerick topic
limerick_word = random.choice(words)
channel.basic_publish(
    exchange='agent_exchange', 
    routing_key='limericks.random',
    body=limerick_word
)
print(f" [x] Sent limericks.random:{limerick_word}")

connection.close()