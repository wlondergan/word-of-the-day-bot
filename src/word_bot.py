from discord import Client, MessageType, Intents, Message
import os
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from english_processing import get_word_of_the_day, shortest_available_stem, is_word_candidate, get_word_candidate
import asyncio

import sys

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

token = os.environ['TOKEN']
channel_id = int(os.environ['CHANNEL_ID'])
blacklist_file = os.environ['BLACKLIST']
whitelist_file = os.environ['WHITELIST']
april_fools_link = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
eastern_time_info = ZoneInfo('America/New_York')
utc_info = timezone.utc

APRIL_FOOLS = datetime(month=4, day=1, year=2025)

EMOJI_ID = 1259346961627086918
POLL_DURATION_HRS = 6
POLL_VOTE_THRESHOLD = 5
DISPUTE_MESSAGE = 'WRONG'

intents = Intents.default()
intents.members = True
intents.message_content = True

class WordOfTheDayInfo:
    def __init__(self, msg_id, user_id, timecode, full_message):
        self.msg_id = msg_id
        self.user_id = user_id
        self.timecode = timecode
        self.full_message = full_message

def to_est(date: datetime) -> datetime:
    if date.tzinfo is None:
        date.tzinfo = utc_info
    return date.astimezone(eastern_time_info)

class WordBot(Client):

    def _determine_word_of_the_day(self, message: Message) -> str | WordOfTheDayInfo:
        word = get_word_of_the_day(message.content, self._blacklist, self._whitelist)
        if word is not None:
            stem = shortest_available_stem(word)

            if stem in self._words:
                return self._words[stem]
            else:
                return stem
            
    def _already_posted_on(self, date_time, user) -> bool:
        for v in self._words.values():
            if v.user_id == user and date_time.date() == v.timecode.date():
                return True
        return False
                
    async def on_ready(self):
        self._words = {}
        self._blacklist = [str(line) for line in open(blacklist_file, 'w+')]
        self._whitelist = [str(line) for line in open(whitelist_file, 'w+')]
        wotd_channel = self.get_channel(channel_id)
        async for message in wotd_channel.history(limit=None, oldest_first=True):
            if message.author != self.user.id and message.type == MessageType.default:
                res = self._determine_word_of_the_day(message)
                if type(res) is str:
                    timecode = to_est(message.created_at)
                    if not self._already_posted_on(timecode, message.author.id):
                        self._words[res] = WordOfTheDayInfo(message.id, message.author.id, timecode, message.content)
                        await self.add_reaction(message)
                    else:
                        await self.remove_reaction(message)
                else:
                    await self.remove_reaction(message)
        eprint("Finished parsing previous messages and setting up.")

    async def on_message(self, message: Message):
        if message.author.id == self.user.id or message.channel.id != channel_id: #only want wotd channel and non bot messages
            return
        
        if message.type == MessageType.reply:
            if message.content == DISPUTE_MESSAGE:
                await self.dispute_word(await message.channel.fetch_message(message.reference.message_id), message)

        elif message.type == MessageType.default:
            print(message.content)
            
            res = self._determine_word_of_the_day(message)

            if type(res) is str:
                print('new word of the day: {}'.format(message.content))
                timecode = to_est(message.created_at)
                if res:
                    if self._already_posted_on(timecode, message.author.id):
                        await message.reply("Only one word of the day per day, bozo 💀")
                    else:
                        self._words[res] = WordOfTheDayInfo(message.id, message.author.id, timecode, message.content)
                        await message.add_reaction(self.get_emoji(EMOJI_ID))

                        if timecode.date() == APRIL_FOOLS.date():
                            await message.reply(":bangbang:Recycled word alert:bangbang:\n {} already said [{}](<{}>)"
                                        .format(message.author.mention, message.content, april_fools_link))
            elif res is not None:
                original_message = await message.channel.fetch_message(res.msg_id)
                await message.reply(":bangbang:Recycled word alert:bangbang:\n {} already said [{}]({})"
                                        .format(original_message.author.mention, original_message.content, original_message.jump_url))
                
    async def on_message_edit(self, before, after):
        await self.remove_wotd(before)
        await self.on_message(after)

    async def on_raw_message_delete(self, message_event):
        for word, wotd_info in self._words.items():
            if wotd_info.msg_id == message_event.message_id:
                await self.get_channel(channel_id).send("{} deleted their word of the day \"{}\"! Kinda embarrassing, not gonna lie... 💀"
                                           .format(self.get_user(wotd_info.user_id).mention, wotd_info.full_message))
                self._words.pop(word)

    async def remove_wotd(self, msg, deleted=False):
        for key, wotd_info in self._words.items():
            if wotd_info.msg_id == msg.id:
                self._words.pop(key)
                if not deleted:
                    await self.remove_reaction(msg)
                return
            
    async def remove_reaction(self, msg):
        for reaction in msg.reactions:
            if reaction.me:
                await reaction.remove(self.user)

    async def add_reaction(self, msg):
        added = False
        for reaction in msg.reactions:
            if reaction.me:
                added = True
                break
        if not added:
            await msg.add_reaction(self.get_emoji(EMOJI_ID))
                
    async def dispute_word(self, msg: Message, dispute_msg: Message):
        dispute_text = "{} has thrown down the gauntlet 😱😱\nIs **{}** an acceptable word of the day?".format(dispute_msg.author.mention, msg.content)
        word = get_word_candidate(msg.content)
        if word is None:
            await dispute_msg.reply("bot abuser 😱")
            return
        poll = await msg.reply("{}\nHours to close: {}"
                               .format(dispute_text, POLL_DURATION_HRS))
        await poll.add_reaction('✔️')
        await poll.add_reaction('❌')
        for i in range(1, POLL_DURATION_HRS + 1):
            await asyncio.sleep(3600)
            await poll.edit(content="{}\nHours to close: {}"
                               .format(dispute_text, POLL_DURATION_HRS - i))
        completed_poll = await msg.channel.fetch_message(poll.id)
        yes_count = 0
        no_count = 0
        for reaction in completed_poll.reactions:
            if reaction.emoji == '✔️':
                yes_count = reaction.count - 1
            elif reaction.emoji == '❌':
                no_count = reaction.count - 1
        
        poll_close_message = ""
        
        stem = shortest_available_stem(word)
        if yes_count > no_count:
            self._whitelist.append(stem)
            if stem in self._blacklist:
                self._blacklist.remove(stem) #make sure to clear it from the other list if it was on it
            poll_close_message = "THE PEOPLE HAVE SPOKEN 😤\nTHIS WORD HAS BEEN DEEMED **VALID**!!"
        else: 
            self._blacklist.append(stem)
            if stem in self._whitelist:
                self._whitelist.remove(stem)
            poll_close_message = "THE PEOPLE HAVE SPOKEN 😤\nTHIS WORD HAS BEEN DEEMED **INVALID**!!"
        await completed_poll.reply(poll_close_message)
        self.write_white_blacklists()
        await completed_poll.edit(content="{}\nPOLL HAS CLOSED.\nVotes YAY: {}\nVotes NAY: {}"
                               .format(dispute_text, yes_count, no_count))
        await self.remove_wotd(msg)
        await self.remove_reaction(msg)
        await self.on_message(msg)
        
    def write_white_blacklists(self):
        with open(blacklist_file, mode='wt', encoding='utf-8') as blfile:
            blfile.write('\n'.join(self._blacklist))
        with open(whitelist_file, mode='wt', encoding='utf-8') as wlfile:
            wlfile.write('\n'.join(self._whitelist))

                
client = WordBot(intents=intents)
client.run(token)
            
        
        