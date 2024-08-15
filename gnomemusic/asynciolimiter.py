# SPDX-License-Identifier: MIT
# Copyright (c) 2022 Bar Harel
# Licensed under the MIT license as detailed in LICENSE.txt
"""AsyncIO rate limiters.

This module provides different rate limiters for asyncio.

    - `Limiter`: Limits by requests per second and takes into account CPU heavy
    tasks or other delays that can occur while the process is sleeping.
    - `LeakyBucketLimiter`: Limits by requests per second according to the
    leaky bucket algorithm. Has a maximum capacity and an initial burst of
    requests.
    - `StrictLimiter`: Limits by requests per second, without taking CPU or
    other process sleeps into account. There are no bursts and the resulting
    rate will always be a less than the set limit.

If you don't know which of these to choose, go for the regular Limiter.

The main method in each limiter is the wait(). For example:

    # Limit to 10 requests per 5 second (equiv to 2 requests per second)
    >>> limiter = Limiter(10/5)
    >>> async def main():
    ...     await limiter.wait() # Wait for a slot to be available.
    ...     pass # do stuff

    # Limit to, at most, 1 request every 10 seconds
    >>> limiter = StrictLimiter(1/10)

For more info, see the documentation for each limiter.
"""

from abc import ABC as _ABC, abstractmethod as _abstractmethod
import asyncio as _asyncio
from collections import deque as _deque
import functools as _functools
# Deque, Optional are required for supporting python versions 3.8, 3.9
from typing import (TypeVar as _TypeVar, Deque as _Deque,
                    Optional as _Optional, cast as _cast,
                    Callable as _Callable, Awaitable as _Awaitable)

__all__ = ['Limiter', 'StrictLimiter', 'LeakyBucketLimiter']
__version__ = "1.0.0"
__author__ = "Bar Harel"
__license__ = "MIT"
__copyright__ = "Copyright (c) 2022 Bar Harel"


_T = _TypeVar('_T')


def _pop_pending(
        futures: _Deque[_asyncio.Future]) -> _Optional[_asyncio.Future]:
    """Pop until the first pending future is found and return it.

    If all futures are done, or deque is empty, return None.

    Args:
        futures: A deque of futures.

    Returns:
        The first pending future, or None if all futures are done.
    """
    while futures:
        waiter = futures.popleft()
        if not waiter.done():
            return waiter
    return None


class _BaseLimiter(_ABC):
    """Base class for all limiters."""
    @_abstractmethod
    async def wait(self) -> None:  # pragma: no cover # ABC
        """Wait for the limiter to let us through.

        Main function of the limiter. Blocks if limit has been reached, and
        lets us through once time passes.
        """
        pass

    @_abstractmethod
    def cancel(self) -> None:  # pragma: no cover # ABC
        """Cancel all waiting calls.

        This will cancel all currently waiting calls.
        Limiter is reusable afterwards, and new calls will wait as usual.
        """
        pass

    @_abstractmethod
    def breach(self) -> None:  # pragma: no cover # ABC
        """Let all calls through.

        All waiting calls will be let through, new `.wait()` calls will also
        pass without waiting, until `.reset()` is called.
        """
        pass

    @_abstractmethod
    def reset(self) -> None:  # pragma: no cover # ABC
        """Reset the limiter.

        This will cancel all waiting calls, reset all internal timers, and
        restore the limiter to its initial state.
        Limiter is reusable afterwards, and the next call will be
        immediately scheduled.
        """
        pass

    def wrap(self, coro: _Awaitable[_T]) -> _Awaitable[_T]:
        """Wrap a coroutine with tprinthe limiter.

        Returns a new coroutine that waits for the limiter to be unlocked, and
        then schedules the original coroutine.

        Equivalent to:

            >>> async def wrapper():
            ...     await limiter.wait()
            ...     return await coro
            ...
            >>> wapper()

        Example use:

            >>> async def foo(number):
            ...     print(number)  # Do stuff
            ...
            >>> limiter = Limiter(1)
            >>> async def main():
            ...     print_numbers = (foo(i) for i in range(10))
            ...     # This will print the numbers over 10 seconds
            ...     await asyncio.gather(*map(limiter.wrap, print_numbers))

        Args:
            coro: The coroutine or awaitable to wrap.

        Returns:
            The wrapped coroutine.
        """
        async def _wrapper() -> _T:
            await self.wait()
            return await coro
        wrapper = _wrapper()
        _functools.update_wrapper(_wrapper, _cast(_Callable, coro))
        return wrapper


class _CommonLimiterMixin(_BaseLimiter):
    """Some common attributes a limiter might need.

    Includes:
        _waiters: A deque of futures waiting for the limiter to be unlocked.
        _locked: Whether the limiter is locked.
        _breached: Whether the limiter has been breached.
        _wakeup_handle: An asyncio.TimerHandle for the next scheduled wakeup.
    """

    def __init__(self, *args, **kwargs) -> None:  # type: ignore
        """Initialize the limiter.

        Subclasses must call `super()`.
        """
        super().__init__(*args, **kwargs)
        self._locked = False
        self._waiters: _Deque[_asyncio.Future] = _deque()
        self._wakeup_handle: _Optional[_asyncio.TimerHandle] = None
        self._breached = False

    async def wait(self) -> None:
        if self._breached:
            return

        if not self._locked:
            self._maybe_lock()
            return
        fut = _asyncio.get_running_loop().create_future()
        self._waiters.append(fut)
        await fut

    def cancel(self) -> None:
        while self._waiters:
            self._waiters.popleft().cancel()

    def breach(self) -> None:
        while self._waiters:
            fut = self._waiters.popleft()
            if not fut.done():
                fut.set_result(None)
        self._cancel_wakeup()
        self._breached = True
        self._locked = False

    def _cancel_wakeup(self) -> None:
        if self._wakeup_handle is not None:
            self._wakeup_handle.cancel()
            self._wakeup_handle = None

    def reset(self) -> None:
        self.cancel()
        self._cancel_wakeup()

        self._locked = False
        self._breached = False

    @_abstractmethod
    def _maybe_lock(self) -> None:  # pragma: no cover # ABC
        """Hook called after a request was allowed to pass without waiting.

        Limiter was unlocked, and we can choose to lock it.
        Subclasses must implement this.
        """
        pass

    def __del__(self):
        """Finalization. Cancel waiters to prevent a deadlock."""
        # No need to touch wakeup, as wakeup holds a strong reference and
        # __del__ won't be called.
        try:
            # Technically this should never happen, where there are waiters
            # without a wakeup scheduled. Means there was a bug in the code.
            waiters = self._waiters

        # Error during initialization before _waiters exists.
        except AttributeError:  # pragma: no cover # Technically a bug.
            return

        any_waiting = False
        for fut in waiters:  # pragma: no cover # Technically a bug.
            if not fut.done():
                fut.cancel()
                any_waiting = True

        # Alert for the bug.
        assert not any_waiting, "__del__ was called with waiters still waiting"

    def close(self) -> None:
        """Close the limiter.

        This will cancel all waiting calls. Limiter is unusable afterwards.
        """
        self.cancel()
        self._cancel_wakeup()


class Limiter(_CommonLimiterMixin):
    """Regular limiter, with a max burst compensating for delayed schedule.

    Takes into account CPU heavy tasks or other delays that can occur while
    the process is sleeping.

    Usage:
        >>> limiter = Limiter(1)
        >>> async def main():
        ...     print_numbers = (foo(i) for i in range(10))
        ...     # This will print the numbers over 10 seconds
        ...     await asyncio.gather(*map(limiter.wrap, print_numbers))

    Alternative usage:
        >>> limiter = Limiter(5)
        >>> async def request():
        ...     await limiter.wait()
        ...     print("Request")  # Do stuff
        ...
        >>> async def main():
        ...     # Schedule 5 requests per second.
        ...     await asyncio.gather(*(request() for _ in range(10)))

    Attributes:
        max_burst: In case there's a delay, schedule no more than this many
        calls at once.
        rate: The rate (calls per second) at which the limiter should let
        traffic through.
    """
    def __init__(self, rate: float, *, max_burst: int = 5) -> None:
        """Create a new limiter.

        Args:
            rate: The rate (calls per second) at which calls can pass through.
            max_burst: In case there's a delay, schedule no more than this many
            calls at once.
        """
        super().__init__()
        self._rate = rate
        self._time_between_calls = 1 / rate
        self.max_burst = max_burst

    def __repr__(self):
        cls = self.__class__
        return f"{cls.__module__}.{cls.__qualname__}(rate={self._rate})"

    @property
    def rate(self) -> float:
        """Calls per second at which the limiter should let traffic through."""
        return self._rate

    @rate.setter
    def rate(self, value: float) -> None:
        """Set the rate (calls per second) at which calls can pass through.

        Args:
            value: The rate (calls per second) at which calls can pass through.
        """
        self._rate = value
        self._time_between_calls = 1 / value

    def _maybe_lock(self):
        """Lock the limiter as soon a request passes through."""
        self._locked = True
        self._schedule_wakeup()

    def _schedule_wakeup(self, at: _Optional[float] = None,  # type: ignore
                         *, _loop=None) -> None:
        """Schedule the next wakeup to be unlocked.

        Args:
            at: The time at which to wake up. If None, use the current
            time + 1/rate.
            _loop: The asyncio loop to use. If None, use the current loop. For
            caching purposes.
        """
        loop = _loop or _asyncio.get_running_loop()
        if at is None:
            at = loop.time() + self._time_between_calls
        self._wakeup_handle = loop.call_at(at, self._wakeup)
        # Saving next wakeup and not this wakeup to account for fractions
        # of rate passed. See leftover_time under _wakeup.
        self._next_wakeup = at

    def _wakeup(self) -> None:
        """Advance the limiter counters once."""
        def _unlock() -> None:
            self._wakeup_handle = None
            self._locked = False
            return
        loop = _asyncio.get_running_loop()
        waiters = self._waiters
        # Short circuit if there are no waiters
        if not waiters:
            _unlock()
            return

        this_wakeup = self._next_wakeup
        current_time = loop.time()
        # We woke up early. Damn event loop!
        if current_time < this_wakeup:
            missed_wakeups = 0.0
            # We have a negative leftover bois. Increase the next sleep!
            leftover_time = current_time - this_wakeup
            # More than 1 tick early. Great success.
            # Technically the higher the rate, the more likely the event loop
            # should be late. If we came early on 2 ticks, that's really bad.
            assert -leftover_time < self._time_between_calls, (
                f"Event loop is too fast. Woke up {-leftover_time * self.rate}"
                f" ticks early.")

        else:
            # We woke up too late!
            # Missed wakeups can happen in case of heavy CPU-bound activity,
            # or high event loop load.
            # Check if we overflowed longer than a single call-time.
            missed_wakeups, leftover_time = divmod(
                current_time - this_wakeup, self._time_between_calls)

        # Attempt to wake up only the missed wakeups and ones that were
        # inserted while we missed the original wakeup.
        to_wakeup = min(int(missed_wakeups) + 1, self.max_burst)

        while to_wakeup and self._waiters:
            waiter = self._waiters.popleft()
            if waiter.done():  # Might have been cancelled.
                continue
            waiter.set_result(None)
            to_wakeup -= 1

        # All of the waiters were cancelled or we missed wakeups and we're out
        # of waiters. Free to accept traffic.
        if to_wakeup:
            _unlock()

        # If we still have waiters, we need to schedule the next wakeup.
        # If we're out of waiters we still need to wait before
        # unlocking in case a new waiter comes in, as we just
        # let a call through.
        else:
            self._schedule_wakeup(
                at=current_time + self._time_between_calls - leftover_time,
                _loop=loop)


class LeakyBucketLimiter(_CommonLimiterMixin):
    """Leaky bucket compliant with bursts.

    Limits by requests per second according to the
    leaky bucket algorithm. Has a maximum capacity and an initial burst of
    requests.

    Usage:
        >>> limiter = LeakyBucketLimiter(1, capacity=5)
        >>> async def main():
        ...     print_numbers = (foo(i) for i in range(10))
        ...     # This will print the numbers 0,1,2,3,4 immidiately, then
        ...     # wait for a second before each number.
        ...     await asyncio.gather(*map(limiter.wrap, print_numbers))
        ...     # After 5 seconds of inactivity, bucket will drain back to
        ...     # empty.

    Alternative usage:
        >>> limiter = LeakyBucketLimiter(5)  # capacity is 10 by default.
        >>> async def request():
        ...     await limiter.wait()
        ...     print("Request")  # Do stuff
        ...
        >>> async def main():
        ...     # First 10 requests would be immediate, then schedule 5
        ...     # requests per second.
        ...     await asyncio.gather(*(request() for _ in range(20)))

    Attributes:
        capacity: The maximum number of requests that can pass through until
        the bucket is full. Defaults to 10.
        rate: The rate (calls per second) at which the bucket should "drain" or
        let calls through.
    """

    capacity: int
    """The maximum number of requests that can pass through until the bucket is
    full."""

    def __init__(self, rate: float, *, capacity: int = 10) -> None:
        """Create a new limiter.

        Args:
            rate: The rate (calls per second) at which calls can pass through
            (or bucket drips).
            capacity: The capacity of the bucket. At full capacity calls to
            wait() will block until the bucket drips.
        """
        super().__init__()
        self._rate = rate
        self._time_between_calls = 1 / rate
        self.capacity = capacity
        self._level = 0

    def __repr__(self):
        cls = self.__class__
        return (f"{cls.__module__}.{cls.__qualname__}(rate={self._rate}, "
                f"capacity={self.capacity})")

    @property
    def rate(self) -> float:
        """Calls per second at which the bucket should "drain" or let calls
        through."""

        return self._rate

    @rate.setter
    def rate(self, value: float) -> None:
        """Set the rate (calls per second) at which bucket should "drain".

        Args:
            value: The rate (calls per second) at which bucket should "drain".
        """
        self._rate = value
        self._time_between_calls = 1 / value

    def _maybe_lock(self):
        """Increase the level, schedule a drain. Lock when the bucket is full.
        """
        self._level += 1

        if self._wakeup_handle is None:
            self._schedule_wakeup()

        if self._level >= self.capacity:
            self._locked = True
            return

    def _schedule_wakeup(self, at: _Optional[float] = None,  # type: ignore
                         *, _loop=None) -> None:
        """Schedule the next wakeup to be unlocked.

        Args:
            at: The time at which to wake up. If None, use the current
            time + 1/rate.
            _loop: The asyncio loop to use. If None, use the current loop. For
            caching purposes.
        """
        loop = _loop or _asyncio.get_running_loop()
        if at is None:
            at = loop.time() + self._time_between_calls
        self._wakeup_handle = loop.call_at(at, self._wakeup)
        self._next_wakeup = at

    def reset(self) -> None:
        """Reset the limiter.

        This will cancel all waiting calls, reset all internal timers, reset
        the bucket to empty and restore the limiter to its initial state.
        Limiter is reusable afterwards, and the next call will be immediately
        scheduled.
        """
        super().reset()
        self._level = 0

    def _wakeup(self) -> None:
        """Drain the bucket at least once. Wakeup waiters if there are any."""
        loop = _asyncio.get_running_loop()
        this_wakeup = self._next_wakeup
        current_time = loop.time()

        # We woke up early. Damn event loop!
        if current_time < this_wakeup:
            missed_drains = 0.0
            # We have a negative leftover bois. Increase the next sleep!
            leftover_time = current_time - this_wakeup
            # More than 1 tick early. Great success.
            # Technically the higher the rate, the more likely the event loop
            # should be late. If we came early on 2 ticks, that's really bad.
            assert -leftover_time < self._time_between_calls, (
                f"Event loop is too fast. Woke up {-leftover_time * self.rate}"
                f" ticks early.")

        else:
            # We woke up too late!
            # Missed wakeups can happen in case of heavy CPU-bound activity,
            # or high event loop load.
            # Check if we overflowed longer than a single call-time.
            missed_drains, leftover_time = divmod(
                current_time - this_wakeup, self._time_between_calls)

        capacity = self.capacity
        level = self._level
        # There are no waiters if level is not == capacity.
        # We can decrease without accounting for current level.
        assert missed_drains.is_integer()
        level = max(0, level - int(missed_drains) - 1)
        while level < capacity and (
                waiter := _pop_pending(self._waiters)) is not None:
            waiter.set_result(None)
            level += 1

        # We have no more waiters
        if level < capacity:
            self._locked = False
            self._level = level
            if level == 0:
                return

        time_to_next_drain = self._time_between_calls - leftover_time
        self._schedule_wakeup(at=current_time + time_to_next_drain)


class StrictLimiter(_CommonLimiterMixin):
    """Limits by a maximum number of requests per second.
    Doesn't take CPU or other process sleeps into account.
    There are no bursts to compensate, and the resulting rate will always be
    less than the set limit.

    Attributes:
        rate: The maximum rate (calls per second) at which calls can pass
        through.
    """

    rate: float
    """The maximum rate (calls per second) at which calls can pass through."""

    def __init__(self, rate: float) -> None:
        """Create a new limiter.

        Args:
            rate: The maximum rate (calls per second) at which calls can pass
            through.
        """
        super().__init__()
        self.rate = rate

    def __repr__(self):
        cls = self.__class__
        return f"{cls.__module__}.{cls.__qualname__}(rate={self.rate})"

    def _maybe_lock(self):
        """Lock the limiter, schedule a wakeup."""
        self._locked = True
        self._schedule_wakeup()

    def _schedule_wakeup(self):
        """Schedule the next wakeup to be unlocked."""
        loop = _asyncio.get_running_loop()
        self._wakeup_handle = loop.call_at(
            loop.time() + 1 / self.rate, self._wakeup)

    def _wakeup(self):
        """Wakeup a single waiter if there is any, otherwise unlock."""
        waiter = _pop_pending(self._waiters)
        if waiter is not None:
            waiter.set_result(None)
            self._schedule_wakeup()
        else:
            self._locked = False
            self._wakeup_handle = None
