from mqueue.interfaces.tonqueue import TonControllQueueAbstract


class ServiceBusQueueProvider(TonControllQueueAbstract):
    pass


class QueueProvider(ServiceBusQueueProvider):
    # entry-point for TonControl
    pass
