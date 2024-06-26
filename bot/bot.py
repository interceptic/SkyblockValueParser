import discord
import asyncio
from discord.ext import commands
from bot.modals.evalue import Embed
from bot.modals.admin import give_admin, remove_admin
import json
import datetime
from bot.modals.list import Setup
from bot.modals.calculator import calculate
from bot.build_embed import build
from minecraft.info.tmbk import representTBMK
import aiosqlite
from database.sqlite import setup_db
import os
from bot.modals.aichat import openai_response


intents = discord.Intents.default()
intents.members = True 
intents.message_content = True
bot = commands.Bot(intents=intents, slash_command_prefix='/')  

@bot.event
async def on_ready():
    print('\x1b[32mLogged in!\x1b[0m')
    await bot.change_presence(status=discord.Status.dnd, activity=discord.Game("Made by Interceptic"))
    await bot.sync_commands()
    

@bot.slash_command(name='value', description='Skyblock Account Value')
async def value(ctx, name: str): 
    embed = discord.Embed(
        title="Fetching...",
        description=f"Obtaining data from api, please wait...",
        color=0xFF007B
    )
    embed.set_footer(text='Made by interceptic', icon_url='https://cdn.discordapp.com/avatars/1227394151847297148/a_17e8e189d32a91dc7a40f25a1ebcd9c0.webp?size=160')
    embed.timestamp = datetime.datetime.now()
    await ctx.respond(embed=embed)
    try:
        class_thing = Embed()
        await class_thing.send_embed(ctx, name)
    except Exception as error:
        print(error)



@bot.slash_command(name='admin', description='Give or remove admin from yourself...')
async def admin(ctx, remove: bool = False):
    with open("config.json") as conf:
        config = json.load(conf)
    if ctx.author.id != config['bot']['owner_discord_id']:
        await ctx.respond("Sorry, you're not allowed to use this command", ephemeral=True)
        return
    if remove: 
        await remove_admin(ctx, config['bot']['owner_discord_id'], config['bot']['admin_role_id'])
        return 
    await give_admin(ctx, config['bot']['owner_discord_id'], config['bot']['admin_role_id'])
    return

@bot.slash_command(name='list', description="List an account")
async def list(ctx, username: str, price: int, profile: bool = False, payment_methods: str = '', extra_info: str = ''):
    await ctx.response.defer()
    guild = await guild_in_db(ctx)
    if not guild:
        embed = await build('Server not in Database', "Sorry, please wait 3 seconds and start the setup process", 0xFF0000)
        setup = Setup
        await ctx.respond(embed=embed)
        await asyncio.sleep(3)
        await setup.check(ctx)
        return
    
    async with aiosqlite.connect('./database/database.db') as database:
        async with database.execute(
            'SELECT seller_id FROM info WHERE guild_id = ?', (ctx.guild.id,)
        ) as cursor:
            value = await cursor.fetchone()
    role = discord.utils.get(ctx.guild.roles, id=value[0])
    if not role in ctx.author.roles:
        await ctx.respond('You need seller role to run this command', ephemeral=True)
        return

    
    
    setup = Setup
    await setup.create_channel(ctx, username, price, profile, payment_methods, extra_info)

@bot.slash_command(name='coins', description="Calculate the price for coins")
async def coins(ctx, type: discord.Option(str, choices=["Buy", "Sell"]), amount: int):
    guild = await guild_in_db(ctx)
    if not guild:
        embed = await build('Server not in Database', "Sorry, please wait 3 seconds and start the setup process", 0xFF0000)
        setup = Setup
        await ctx.respond(embed=embed)
        await asyncio.sleep(3)
        await setup.check(ctx)
        return
    
    if type == "Sell":
        value = await calculate(ctx, amount, True)
        if value == False:
            embed = await build("Invalid Sell Amount", "Minimum amount to sell is 500 million.", 0xFF0000)
            await ctx.respond(embed=embed)
            return
        amount = representTBMK(amount * 1000000)    
        embed = await build(f"Price for {amount}", f"You can sell {amount} for ${round(value, 2)} USD", 0x00FFDC)
        await ctx.respond(embed=embed)
        return
    elif type == "Buy":
        value = await calculate(ctx, amount, False)
        amount = representTBMK(amount * 1000000)    
        embed = await build(f"Price for {amount}", f"You can buy {amount} for ${round(value, 2)} USD", 0x00FFDC)
        await ctx.respond(embed=embed)
        
        
    
async def guild_in_db(ctx):
    if not os.path.exists("./database/database.db"):
        await setup_db()
        return False
    async with aiosqlite.connect('./database/database.db') as sqlite:
        async with sqlite.execute('SELECT COUNT(*) FROM info WHERE guild_id = ?', (ctx.guild.id,)) as cursor:
            result = await cursor.fetchone()
            exists = result[0] > 0  # This will be True if guild id exists, otherwise False
            return exists


@bot.event
async def on_message(message):
    with open("config.json") as config:
        config = json.load(config)

    
    if message.author.guild_permissions.administrator:
        if '1250030190617165824' in message.content:
            prompt = f"A server admin in flux qol has said: {message.content}"
            response = openai_response(prompt, message)
            await message.reply(response)
            return
        
    if message.channel.id != 1254978027369136219:
        return
    if message.author == bot.user:
        return
    # if message.author.id != 1227394151847297148:
    #     return
   
   
    if not config['bot']['ai_chat']:
        await message.reply('**Sorry, the chatbot isnt currently available for member use. D: **')
        return

   
   
    with open("ai_history.json") as file:
        history = json.load(file)
        
    author_id = str(message.author.id)
    if author_id not in history['ids']:
        history['ids'][author_id] = {}
    if 'messages' not in history['ids'][author_id]:
        history['ids'][author_id]['messages'] = []
    if 'responses' not in history['ids'][author_id]:
        history['ids'][author_id]['responses'] = []
    
    
    history['ids'][author_id]['messages'].append(message.content)
    with open("ai_history.json", "w") as file:
        json.dump(history, file, indent=4)
    
    prompt = f"act like a friend but you are also an assistant and do what they say but do not repeat their words: {message.content}"
    response = openai_response(prompt, message)
    with open("ai_history.json") as file:
        history = json.load(file)
    history['ids'][author_id]['responses'].append(response)
    with open("ai_history.json", "w") as file:
        json.dump(history, file, indent=4)
   
   
    if 'role' in response or '@' in response or 'discord.gg' in response or 'discord.com/invite' in response or 'https://' in response:
        await message.reply('**Sorry, this response is restricted - ;)**')
        return
    await message.reply(response)
    return

