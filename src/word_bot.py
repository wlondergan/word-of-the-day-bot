from discord import Client, MessageType, Intents, Message
import os
import sys
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from english_processing import get_word_of_the_day, shortest_available_stem

token = os.environ['TOKEN']
channel_id = int(os.environ['CHANNEL_ID'])
#blacklist_file = os.environ['BLACKLIST']
#whitelist_file = os.environ['WHITELIST']
eastern_time_info = ZoneInfo('America/New_York')
utc_info = timezone.utc

#blacklist = [str(line) for line in os.open(blacklist_file)]
#whitelist = [str(line) for line in os.open(whitelist_file)]

EMOJI_ID = 1259346961627086918

intents = Intents.default()
intents.message_content = True

class WordOfTheDayInfo:
    def __init__(self, msg_id, user_id, timecode):
        self.msg_id = msg_id
        self.user_id = user_id
        self.timecode = timecode

def to_est(date: datetime) -> datetime:
    if date.tzinfo is None:
        date.tzinfo = utc_info
    return date.astimezone(eastern_time_info)

class WordBot(Client):

    def _determine_word_of_the_day(self, message: Message) -> str | WordOfTheDayInfo:
        word = get_word_of_the_day(message.content)
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
        wotd_channel = self.get_channel(channel_id)
        async for message in wotd_channel.history(limit=None, oldest_first=True):
            if message.author != self.user.id and message.type == MessageType.default:
                res = self._determine_word_of_the_day(message)
                if type(res) is str:
                    timecode = to_est(message.created_at)
                    if not self._already_posted_on(timecode, message.author.id):
                        self._words[res] = WordOfTheDayInfo(message.id, message.author.id, timecode)
                    else:
                        await self.remove_reaction(message)
                else:
                    await self.remove_reaction(message)
        sys.stderr.print("Finished parsing previous messages and setting up.")

    async def on_message(self, message: Message):
        if message.channel.id == channel_id and message.type == MessageType.default:
            print(message.content)
            #don't bother checking the bot's own messages
            if message.author.id == self.user.id:
                return
            
            res = self._determine_word_of_the_day(message)

            if type(res) is str:
                print('new word of the day: {}'.format(message.content))
                timecode = to_est(message.created_at)
                if res:
                    if self._already_posted_on(timecode, message.author.id):
                        await message.reply("Only one word of the day per day, bozo 💀")
                    else:
                        self._words[res] = WordOfTheDayInfo(message.id, message.author.id, timecode)
                        await message.add_reaction(self.get_emoji(EMOJI_ID))
            elif res is not None:
                original_message = await message.channel.fetch_message(res.msg_id)
                await message.reply(":bangbang:Recycled word alert:bangbang:\n {} already said [{}]({})"
                                        .format(original_message.author.mention, original_message.content, original_message.jump_url))
                
    async def on_message_edit(self, before, after):
        await self.remove_wotd(before)
        await self.on_message(after)

    async def on_message_delete(self, message):
        await self.remove_wotd(message, deleted=True)

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
                
    async def dispute_word():
        pass
                
client = WordBot(intents=intents)
client.run(token)
            
        
        