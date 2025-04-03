# -*- coding: utf-8 -*-

import functools
import logging
import asyncio
import pika
from pika.adapters.select_connection import SelectConnection
from pika.exchange_type import ExchangeType
from rich.console import Console
from rich.panel import Panel

LOGGER = logging.getLogger(__name__)
console = Console()

class TopicConsumer(object):
    """This is a consumer that will handle unexpected interactions
    with RabbitMQ such as channel and connection closures.
    """
    EXCHANGE = 'agent_exchange'
    EXCHANGE_TYPE = ExchangeType.topic

    def __init__(self, amqp_url, agent_id, binding_key, topic_type, agent_registry):
        self.should_reconnect = False
        self.was_consuming = False
        self._connection = None
        self._channel = None
        self._closing = False
        self._consumer_tag = None
        self._url = amqp_url
        self._consuming = False
        self._prefetch_count = 1
        self._agent_id = agent_id
        self._binding_key = binding_key
        self._topic_type = topic_type
        self._queue_name = ''
        self._agent_registry = agent_registry

    def connect(self):
        LOGGER.info('Connecting to %s', self._url)
        return SelectConnection(
            parameters=pika.URLParameters(self._url),
            on_open_callback=self.on_connection_open,
            on_open_error_callback=self.on_connection_open_error,
            on_close_callback=self.on_connection_closed)

    def on_connection_open(self, _unused_connection):
        LOGGER.info('Connection opened')
        self.open_channel()

    def on_connection_open_error(self, _unused_connection, err):
        LOGGER.error('Connection open failed: %s', err)
        self.reconnect()

    def on_connection_closed(self, _unused_connection, reason):
        self._channel = None
        if self._closing:
            self._connection.ioloop.stop()
        else:
            LOGGER.warning('Connection closed, reconnect necessary: %s', reason)
            self.reconnect()

    def reconnect(self):
        self.should_reconnect = True
        self.stop()

    def open_channel(self):
        LOGGER.info('Creating a new channel')
        self._connection.channel(on_open_callback=self.on_channel_open)

    def on_channel_open(self, channel):
        LOGGER.info('Channel opened')
        self._channel = channel
        self.add_on_channel_close_callback()
        self.setup_exchange(self.EXCHANGE)

    def add_on_channel_close_callback(self):
        LOGGER.info('Adding channel close callback')
        self._channel.add_on_close_callback(self.on_channel_closed)

    def on_channel_closed(self, channel, reason):
        LOGGER.warning('Channel %i was closed: %s', channel, reason)
        self.close_connection()

    def setup_exchange(self, exchange_name):
        LOGGER.info('Declaring exchange: %s', exchange_name)
        cb = functools.partial(self.on_exchange_declareok, userdata=exchange_name)
        self._channel.exchange_declare(
            exchange=exchange_name,
            exchange_type=self.EXCHANGE_TYPE,
            callback=cb)

    def on_exchange_declareok(self, _unused_frame, userdata):
        LOGGER.info('Exchange declared: %s', userdata)
        self.setup_queue()

    def setup_queue(self):
        LOGGER.info('Declaring queue')
        self._channel.queue_declare(
            queue='',
            exclusive=True,
            callback=self.on_queue_declareok)

    def on_queue_declareok(self, method_frame):
        self._queue_name = method_frame.method.queue
        LOGGER.info('Binding %s to %s with %s', self.EXCHANGE, self._queue_name,
                   self._binding_key)
        self._channel.queue_bind(
            self._queue_name,
            self.EXCHANGE,
            routing_key=self._binding_key,
            callback=self.on_bindok)

    def on_bindok(self, _unused_frame):
        LOGGER.info('Queue bound')
        self.set_qos()

    def set_qos(self):
        self._channel.basic_qos(
            prefetch_count=self._prefetch_count, callback=self.on_basic_qos_ok)

    def on_basic_qos_ok(self, _unused_frame):
        LOGGER.info('QOS set to: %d', self._prefetch_count)
        self.start_consuming()

    def start_consuming(self):
        LOGGER.info('Issuing consumer related RPC commands')
        self.add_on_cancel_callback()
        self._consumer_tag = self._channel.basic_consume(
            self._queue_name, self.on_message)
        self.was_consuming = True
        self._consuming = True

    def add_on_cancel_callback(self):
        LOGGER.info('Adding consumer cancellation callback')
        self._channel.add_on_cancel_callback(self.on_consumer_cancelled)

    def on_consumer_cancelled(self, method_frame):
        LOGGER.info('Consumer was cancelled remotely, shutting down: %r',
                   method_frame)
        if self._channel:
            self._channel.close()

    async def process_message(self, body):
        agent = self._agent_registry[self._agent_id]
        prompt = f"You received a message on the {self._topic_type} topic: {body}\n"
        
        result = await agent.ainvoke({"messages": [("user", prompt)]})
        LOGGER.info('Agent response received')
        console.print(Panel(
            result['messages'][-1].content,
            title=f"[bold green]{self._topic_type.upper()} Response[/bold green]",
            subtitle=f"[bold blue]Message: {body}[/bold blue]",
            width=console.width,
            style="cyan"
        ))

    def on_message(self, _unused_channel, basic_deliver, properties, body):
        LOGGER.info('Received message # %s: %s',
                   basic_deliver.delivery_tag, body.decode())
        
        # Create an event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Run the async function in the event loop
            loop.run_until_complete(self.process_message(body.decode()))
        finally:
            loop.close()
            
        self.acknowledge_message(basic_deliver.delivery_tag)

    def acknowledge_message(self, delivery_tag):
        LOGGER.info('Acknowledging message %s', delivery_tag)
        self._channel.basic_ack(delivery_tag)

    def stop_consuming(self):
        if self._channel:
            LOGGER.info('Sending a Basic.Cancel RPC command to RabbitMQ')
            cb = functools.partial(
                self.on_cancelok, userdata=self._consumer_tag)
            self._channel.basic_cancel(self._consumer_tag, cb)

    def on_cancelok(self, _unused_frame, userdata):
        self._consuming = False
        LOGGER.info(
            'RabbitMQ acknowledged the cancellation of the consumer: %s',
            userdata)
        self.close_channel()

    def close_channel(self):
        LOGGER.info('Closing the channel')
        self._channel.close()

    def run(self):
        self._connection = self.connect()
        self._connection.ioloop.start()

    def stop(self):
        if not self._closing:
            self._closing = True
            LOGGER.info('Stopping')
            if self._consuming:
                self.stop_consuming()
                self._connection.ioloop.start()
            else:
                self._connection.ioloop.stop()
            LOGGER.info('Stopped')

    def close_connection(self):
        self._consuming = False
        if self._connection.is_closing or self._connection.is_closed:
            LOGGER.info('Connection is closing or already closed')
        else:
            LOGGER.info('Closing connection')
            self._connection.close() 