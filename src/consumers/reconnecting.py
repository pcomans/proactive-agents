# -*- coding: utf-8 -*-

import logging
import time
from .base import TopicConsumer

LOGGER = logging.getLogger(__name__)

class ReconnectingTopicConsumer(object):
    """This is a consumer that will reconnect if the nested
    TopicConsumer indicates that a reconnect is necessary.
    """
    def __init__(self, amqp_url, agent_id, binding_key, topic_type, agent_registry):
        self._reconnect_delay = 0
        self._amqp_url = amqp_url
        self._agent_id = agent_id
        self._binding_key = binding_key
        self._topic_type = topic_type
        self._agent_registry = agent_registry
        self._consumer = TopicConsumer(
            self._amqp_url, 
            self._agent_id, 
            self._binding_key, 
            self._topic_type,
            self._agent_registry
        )

    def run(self):
        while True:
            try:
                self._consumer.run()
            except KeyboardInterrupt:
                self._consumer.stop()
                break
            self._maybe_reconnect()

    def _maybe_reconnect(self):
        if self._consumer.should_reconnect:
            self._consumer.stop()
            reconnect_delay = self._get_reconnect_delay()
            LOGGER.info('Reconnecting after %d seconds', reconnect_delay)
            time.sleep(reconnect_delay)
            self._consumer = TopicConsumer(
                self._amqp_url,
                self._agent_id,
                self._binding_key,
                self._topic_type,
                self._agent_registry
            )

    def _get_reconnect_delay(self):
        if self._consumer.was_consuming:
            self._reconnect_delay = 0
        else:
            self._reconnect_delay += 1
        if self._reconnect_delay > 30:
            self._reconnect_delay = 30
        return self._reconnect_delay 