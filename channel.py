import email.utils
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple  # noqa: F401

import aiohttp  # noqa: F401
import aioodbc.cursor  # noqa: F401

from lib.api import twitch
from lib.data import ChatCommandArgs
from lib.helper.chat import permission

DateStruct = Optional[Tuple[int, int, int, int, int, int, int, int, int]]


@permission('moderator')
async def commandHighlight(args: ChatCommandArgs) -> bool:
    reason: Optional[str] = args.message.query or None

    response: aiohttp.ClientResponse
    data: Optional[Dict[str, Any]]
    response, data = await twitch.get_call(
        args.chat.channel, '/kraken/streams/' + args.chat.channel,
        headers={
            'Accept': 'application/vnd.twitchtv.v3+json',
            })
    try:
        if response.status != 200:
            raise ValueError()

        if data['stream']:
            if 'Date' not in response.headers:
                raise ValueError()
            date: Optional[str] = response.headers['Date']
            dateStruct: DateStruct
            dateStruct = email.utils.parsedate(date)
            if dateStruct is None:
                raise ValueError()
            unixTimestamp = time.mktime(dateStruct)
            currentTime: datetime
            currentTime = datetime.fromtimestamp(unixTimestamp)
            created: datetime = datetime.strptime(
                data['stream']['created_at'], '%Y-%m-%dT%H:%M:%SZ')

            cursor: aioodbc.cursor
            async with await args.database.cursor() as cursor:
                query: str = '''
INSERT INTO highlight_marker
    (broadcaster, broadcastId, broadcastTime, markedTime, reason)
    VALUES (?, ?, ?, ?, ?)
'''
                params: Tuple[Any, ...]
                params = (args.chat.channel, int(data['stream']['_id']),
                          created, currentTime, reason)
                await cursor.execute(query, params)
                await args.database.commit()

            timeMarked: str = str(currentTime - created)
            args.chat.send(f'Marked highlight at {timeMarked}')
            return True
        elif data['stream'] is None:
            args.chat.send(f'{args.chat.channel} is currently not streaming')
            return True
    except (ValueError, KeyError):
        args.chat.send('Fail to get stream information from Twitch.tv')
    except Exception:
        args.chat.send('Unknown Error')
    return True


@permission('broadcaster')
async def commandListHighlight(args: ChatCommandArgs) -> bool:
    highlights: List[Tuple[int, datetime, datetime, Optional[str]]]

    cursor: aioodbc.cursor
    async with await args.database.cursor() as cursor:
        query = '''
SELECT broadcastId, broadcastTime, markedTime, reason
    FROM highlight_marker
    WHERE broadcaster=?
    ORDER BY broadcastId DESC, markedTime ASC'''
        highlights = [r async for r
                      in await cursor.execute(query, (args.chat.channel, ))]

    response: aiohttp.ClientResponse
    data: Optional[Dict[str, Any]]
    response, data = await twitch.get_call(
        args.chat.channel,
        '/kraken/channels/' + args.chat.channel +
        '/videos?broadcasts=true&limit=100',
        headers={
            'Accept': 'application/vnd.twitchtv.v3+json',
            })

    try:
        if response.status != 200:
            raise ValueError()

        broadcastId: int
        startTime: datetime
        timestamp: datetime
        reason: Optional[str]
        for broadcastId, startTime, timestamp, reason in highlights:
            video: Optional[Dict[Any, Any]]
            video = next(filter(lambda v: v['broadcast_id'] == broadcastId,
                                data['videos']), None)
            reasoning = f' with reason: {reason}' if reason is not None else ''
            if video is not None:
                created: datetime
                created = datetime.strptime(video['recorded_at'],
                                            '%Y-%m-%dT%H:%M:%SZ')

                timespan: timedelta = timestamp - created
                url: str = (video['url'] + '?t=' + str(timespan.seconds // 60)
                            + 'm' + str(timespan.seconds % 60) + 's')
                args.chat.send(f'''\
Marked highlight on {timedelta} for broadcast at {url}{reasoning}\
''')
            else:
                args.chat.send(f'''\
Marked highlight on {timestamp - startTime} for broadcast recorded on \
{startTime}{reasoning}''')
        if not highlights:
            args.chat.send('No marked highlights')

        return True
    except (ValueError, KeyError):
        args.chat.send('Fail to get stream information from Twitch.tv')
    except Exception:
        args.chat.send('Unknown Error')
    return True


@permission('broadcaster')
async def commandClearHighlight(args: ChatCommandArgs) -> bool:
    cursor: aioodbc.cursor.Cursor
    async with await args.database.cursor() as cursor:
        query: str = 'DELETE FROM highlight_marker WHERE broadcaster=?'
        await cursor.execute(query, (args.chat.channel,))
        await args.database.commit()
    args.chat.send('Cleared all marked highlights')
    return True
