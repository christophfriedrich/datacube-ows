# This file is part of datacube-ows, part of the Open Data Cube project.
# See https://opendatacube.org for more information.
#
# Copyright (c) 2017-2021 OWS Contributors
# SPDX-License-Identifier: Apache-2.0
import datetime
import logging
from functools import wraps
from time import monotonic
from typing import Any, Callable, List, Optional, TypeVar

import pytz

F = TypeVar('F', bound=Callable[..., Any])

def log_call(func: F) -> F:
    """
    Profiling function decorator

    Placing @log_call at the top of a function or method, results in all calls to that function or method
    being logged at debug level.
    """
    @wraps(func)
    def log_wrapper(*args, **kwargs):
        _LOG = logging.getLogger()
        _LOG.debug("%s args: %s kwargs: %s", func.__name__, args, kwargs)
        return func(*args, **kwargs)
    return log_wrapper


def time_call(func: F) -> F:
    """
    Profiling function decorator

    Placing @log_call at the top of a function or method, results in all calls to that function or method
    being timed at debug level.

    For debugging or optimisation research only.  Should not occur in mainline code.
    """
    @wraps(func)
    def timing_wrapper(*args, **kwargs):
        start: float = monotonic()
        result: Any = func(*args, **kwargs)
        stop: float = monotonic()
        _LOG = logging.getLogger()
        _LOG.debug("%s took: %d ms", func.__name__, int((stop - start) * 1000))
        return result
    return timing_wrapper


def group_by_begin_datetime(pnames: Optional[List[str]] = None,
                            truncate_dates: bool = True) -> "datacube.api.query.GroupBy":
    """
    Returns an ODC GroupBy object, suitable for daily/monthly/yearly/etc statistical/summary data.
    (Or for sub-day time resolution data)
    """
    from datacube.api.query import GroupBy
    base_sort_key = lambda ds: ds.time.begin
    if pnames:
        index = {
            pn: i
            for i, pn in enumerate(pnames)
        }
        sort_key = lambda ds: (index.get(ds.type.name), base_sort_key(ds))
    else:
        sort_key = base_sort_key
    if truncate_dates:
        grp_by = lambda ds: datetime.datetime(
            ds.time.begin.year,
            ds.time.begin.month,
            ds.time.begin.day,
            tzinfo=pytz.UTC)
    else:
        grp_by = lambda ds: ds.time.begin
    return GroupBy(
        dimension='time',
        group_by_func=grp_by,
        units='seconds since 1970-01-01 00:00:00',
        sort_key=sort_key
    )


def group_by_subday() -> "datacube.api.query.GroupBy":
    """
    Returns an ODC GroupBy object, suitable for sub-day level data

    :return:
    """

def group_by_solar(pnames: Optional[List[str]] = None) -> "datacube.api.query.GroupBy":
    from datacube.api.query import GroupBy, solar_day
    base_sort_key = lambda ds: ds.time.begin
    if pnames:
        index = {
            pn: i
            for i, pn in enumerate(pnames)
        }
        sort_key = lambda ds: (index.get(ds.type.name), base_sort_key(ds))
    else:
        sort_key = base_sort_key
    return GroupBy(
        dimension='time',
        group_by_func=solar_day,
        units='seconds since 1970-01-01 00:00:00',
        sort_key=sort_key
    )


def group_by_mosaic(pnames: Optional[List[str]] = None) -> "datacube.api.query.GroupBy":
    from datacube.api.query import GroupBy, solar_day
    base_sort_key = lambda ds: ds.time.begin
    if pnames:
        index = {
            pn: i
            for i, pn in enumerate(pnames)
        }
        sort_key = lambda ds: (solar_day(ds), index.get(ds.type.name), base_sort_key(ds))
    else:
        sort_key = lambda ds: (solar_day(ds), base_sort_key(ds))
    return GroupBy(
        dimension='time',
        group_by_func=lambda n: datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc),
        units='seconds since 1970-01-01 00:00:00',
        sort_key=sort_key
    )


def get_sqlconn(dc: "datacube.Datacube") -> "sqlalchemy.engine.base.Connection":
    """
    Extracts a SQLAlchemy database connection from a Datacube object.

    :param dc: An initialised Datacube object
    :return: A SQLAlchemy database connection object.
    """
    # pylint: disable=protected-access
    return dc.index._db._engine.connect()


def find_matching_date(dt, dates) -> bool:
    """
    Check for a matching datetime in sorted list, using subday time resolution second-rounding rules.

    :param dt: The date to dun
    :param dates: List of sorted date-times
    :return: True if match found
    """
    def range_of(dt):
        start = datetime.datetime(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second, tzinfo=dt.tzinfo)
        end = start + datetime.timedelta(seconds=1)
        return start, end

    dtlen = len(dates)
    if dtlen == 0:
        return False
    splitter = dtlen // 2
    start, end = range_of(dates[splitter])
    if dt >= start and dt < end:
        return True
    elif dt < start:
        return find_matching_date(dt, dates[0:splitter])
    else:
        return find_matching_date(dt, dates[splitter + 1:])
