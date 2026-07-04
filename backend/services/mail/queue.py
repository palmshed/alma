import logging
import threading
from abc import ABC, abstractmethod
from collections.abc import Callable
from queue import Empty, Queue
from threading import Timer
from typing import Optional

from .config import MailConfig
from .models import MailMessage, MailStatus, RetryPolicy

logger = logging.getLogger("palmshed.mail.queue")


class MailQueue(ABC):
    @abstractmethod
    def enqueue(self, message: MailMessage) -> None: ...

    def start(self) -> None: ...

    def stop(self) -> None: ...

    def drain(self, timeout: float = 5.0) -> None: ...

    @property
    def depth(self) -> int:
        return 0

    @property
    def running(self) -> bool:
        return False


class ThreadMailQueue(MailQueue):
    def __init__(
        self,
        worker: Optional[Callable[[MailMessage], None]] = None,
        retry_policy: Optional[RetryPolicy] = None,
        use_threading: bool = True,
    ) -> None:
        self._queue: Queue = Queue()
        self._worker = worker
        self._retry_policy = retry_policy or RetryPolicy()
        self._use_threading = use_threading
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._draining = False

    def enqueue(self, message: MailMessage) -> None:
        message.status = MailStatus.PENDING
        self._queue.put(message)
        logger.info(
            "Queued mail: to=%s template=%s id=%s",
            message.recipient.email,
            message.template,
            message.id,
        )

    def start(self) -> None:
        if self._running or self._draining:
            return
        self._running = True
        if self._use_threading:
            self._thread = threading.Thread(target=self._process, daemon=True)
            self._thread.start()

    def stop(self) -> None:
        self._running = False

    def drain(self, timeout: float = 5.0) -> None:
        logger.info("Draining mail queue (timeout=%.1fs)...", timeout)
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout)
        remaining = self._queue.qsize()
        if remaining > 0:
            logger.warning("Drain complete with %d messages remaining", remaining)
        else:
            logger.info("Mail queue drained successfully")

    @property
    def depth(self) -> int:
        return self._queue.qsize()

    @property
    def running(self) -> bool:
        return self._running or self._draining

    def _process(self) -> None:
        while self._running or (self._draining and not self._queue.empty()):
            try:
                message = self._queue.get(timeout=1)
            except Empty:
                continue

            if not self._worker:
                continue

            try:
                self._worker(message)
                message.status = MailStatus.SENT
            except Exception:
                message.retry_count += 1
                if message.retry_count < self._retry_policy.max_retries:
                    delay = self._retry_policy.delay_for(message.retry_count)
                    message.status = MailStatus.RETRYING
                    logger.info(
                        "Retry %d/%d for %s in %.1fs",
                        message.retry_count,
                        self._retry_policy.max_retries,
                        message.id,
                        delay,
                    )
                    Timer(delay, self._queue.put, args=[message]).start()
                else:
                    message.status = MailStatus.FAILED
                    logger.error(
                        "Mail failed after %d retries: to=%s template=%s id=%s",
                        message.retry_count,
                        message.recipient.email,
                        message.template,
                        message.id,
                    )

    def __call__(self, message: MailMessage) -> None:
        self.enqueue(message)


def get_queue(
    config: MailConfig,
    worker: Optional[Callable[[MailMessage], None]] = None,
) -> MailQueue:
    return ThreadMailQueue(
        worker=worker,
        retry_policy=config.retry_policy,
        use_threading=config.async_queue,
    )
