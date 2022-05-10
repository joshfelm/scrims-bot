from time import sleep
from bs4 import BeautifulSoup
from selenium.webdriver import Chrome
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as ec
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
import pymongo
import datetime
import re


# import requests
# import urllib.request
# import shutil

import discord
# from discord.ext import get
import networkx as nx
import random
import sqlite3
from numpy.lib.shape_base import split
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import maximum_bipartite_matching

import os

processing_result = False
# roles [top, jg, mid, adc, supp]
KEY_CHAR = '!'
dc_client  = discord.Client()
mongo_client = pymongo.MongoClient(os.getenv('MONGODB_URI'))

roles_db = mongo_client.users.roles
leaderboard_collection = mongo_client.leaderboard
games_db = mongo_client.users.games

A = [0,1,0,1,0] # 0
B = [1,1,1,1,0] # 1
C = [0,0,0,1,0] # 2
D = [0,0,1,0,0] # 3
E = [0,0,1,0,0] # 4
F = [0,1,0,0,0] # 5
G = [1,1,1,0,0] # 6
H = [1,1,1,0,0] # 7
I = [1,1,1,1,0] # 8
J = [1,0,1,1,0] # 9

dict_q = {
    'plat': [],
    'diamond': [],
    'universal': [],
}

gameTeam1 = []
gameTeam2 = []
validroles = ['top','jungle','mid','adc','support']

#split into two teams, matching maximum amount of players
def split_teams(ids, players):
    autofill = False
    print(players)
    for p in players:
        p.extend(p)
    order = list(range(0,10))
    n = 0
    random.shuffle(order)
    shuffle_player = []
    for i in order:
        shuffle_player.append(players[i])
    graph_shuffle = csr_matrix(shuffle_player)
    team = maximum_bipartite_matching(graph_shuffle,perm_type='row')
    if -1 in team:
        # enable autofill
        autofill = True
        indices = [i for i, value in enumerate(team) if value == -1]
        print('missing positions: ', indices)
        unused = list(set(order) - set(team))
        print('unused players:', unused)
        random.shuffle(unused)
        n = 0
        for i in indices:
            team[i] = unused[n]
            n+=1
    actual_team = list(range(0,10))
    for i in range(len(team)):
        actual_team[i] = ids[order[team[i]]]
    team1 = actual_team[:5]
    team2 = actual_team[5:]
    return((team1,team2,autofill))

@dc_client.event
async def on_ready():
    print('Logged in as {0.user}'.format(dc_client))

# Handle messages
@dc_client.event
async def on_message(message):
    # Ignore if message is from bot
    if message.author == dc_client.user:
        return
    args = str(message.content).split()
    q_id = ''
    if (message.channel.id == 972100383973457940 or message.channel.id == 971802769939914764):
        #diamond
        q_id = 'diamond'
    elif (message.channel.id == 972100426562408508 or message.channel.id == 971802813581623316):
        #plat
        q_id = 'plat'
    elif (message.channel.id == 972099970259894302):
        #universal
        q_id = 'universal'
    else:
        q_id = None
    if message.content.startswith('$testscrim') and q_id != None:
        # sample scrim with players a-j
        list_fellas = [('1',A),('2',B),('3',C),('4',D),('5',E),('6',F),('7',G),('8',H)]
        # list_fellas = [('1',A),('8',H)]
        for l in list_fellas:
            dict_q[q_id].append(l)
        await message.channel.send(str(len(dict_q[q_id])) + ' players in q')
    elif message.content.startswith('$testscri2') and q_id != None:
        # sample scrim with players a-j
        list_fellas = [('1',A)]
        # list_fellas = [('1',A),('8',H)]
        for l in list_fellas:
            dict_q[q_id].append(l)
        await message.channel.send(str(len(dict_q[q_id])) + ' players in q')
    elif args[0] == '$' + 'showlb':
        if (args[1] == 'plat'):
            leaderboard_db = leaderboard_collection.plat
        if (args[1] == 'dia'):
            leaderboard_db = leaderboard_collection.dia
        if (args[1] == 'universal'):
            leaderboard_db = leaderboard_collection.dia
        lb_data = leaderboard_db.find({'id': message.author.id})
        if lb_data != []:
            for l in lb_data:
                await message.channel.send(str(l))
        else:
            await message.channel.send('No LB data for this user yet')
    elif args[0] == '$' + 'testmatch':
        team1 = [216631365288984576] # me
        team2 = [457302161416781824] # rid and charlie (218011028900937728)
        # match_id = 1000
        old_ids = games_db.distinct('match_id')
        # first match ever
        print(old_ids)
        if len(old_ids) == 0:
            match_id = 1000
        else:
            # new match id is one more than old ones
            match_id = max(old_ids) + 1
        games_db.insert_one({
            'match_id': match_id,
            'q_id': args[1].lower(),
            'team1': team1,
            'team2': team2,
            'resolved': False,
            'time_finished': None,
        })
    elif args[0] == '$' + 'delgames' and "admin" in [y.name.lower() for y in message.author.roles]:
        games_db.delete_many({})
        print('Wiped games database')
    elif args[0] == '$' + 'dellb' and "admin" in [y.name.lower() for y in message.author.roles]:
        if (args[1].lower() == 'plat'):
            leaderboard_db = leaderboard_collection.plat
        elif (args[1].lower() == 'dia'):
            leaderboard_db = leaderboard_collection.dia
        elif (args[1].lower() == 'universal'):
            leaderboard_db = leaderboard_collection.universal
        else:
            await message.channel.send('Invalid DB identifier')
            return
        leaderboard_db.delete_many({})
    elif args[0] == '$' + 'showgames':
        game_data = games_db.find({'resolved': False})
        for g in game_data:
            print(g)
    elif args[0] == '$' + 'usernamefetch':
        uname_data = roles_db.find_one({'_id': int(args[1])})
        await message.channel.send(uname_data['username'])
    elif args[0] == '$' + 'username':
        username = await dc_client.fetch_user(message.author.id)
        print(str(username)[:5])
        # print(dc_client.get_user(message.author.id))
    elif args[0] == '$' + 'usernameupdate':
        player_data = list(roles_db.find({}))
        print(player_data[0])
        for p in player_data:
            uname = await dc_client.fetch_user(p['_id'])
            update_entry = {'$set': {
                'username': str(uname)[:-5]
            }}
            roles_db.update_one({'_id': int(p['_id'])}, update_entry)
    else:
        # return # DISABLE ! COMMANDS FOR NOW
        # Information
        for a in args:
            a = a.lower()
        if message.channel.id == 972118405631062056 and args[0] not in ['!add', '!remove', '!roles', '!checkroles','!addroles', '!removeroles','!a','!r'] and not message.author.id == 800397947766440007:
            await message.delete()
            return
        if args[0] == KEY_CHAR + 'info' or args[0] == KEY_CHAR + 'help':
            info=discord.Embed(title='Commands:', color=0x76105b)
            info.add_field(name='__Adding roles__ - `!add`', value='Add your role using the `!addroles` or `!add` command. It would look something like \n`!addroles top jungle mid adc support` \nThis will automatically add you to the database on first use', inline=False)
            info.add_field(name='__Removing roles__ - `!remove`', value='Remove your roles in the same way using `!removeroles` or `!remove`', inline=False)
            info.add_field(name='__Checking roles__ - `!roles`', value='Check to see your currently stored roles with `!roles` or `!checkroles`', inline=False)
            info.add_field(name='__Queueing__ - `!q`', value='Use `!q` or `!queue` to queue up and `!leave` to leave', inline=False)
            info.add_field(name='__Show queue__ - `!show`', value='Use `!show` to list the current queue members', inline=False)
            info.add_field(name='__Reporting score__ - `!report`', value='Use `!report win` to report a win for your team or lose for vice versa. \nUse `!report remake` if you decide to cancel the game', inline=False)
            info.add_field(name='__See standings__ - `!table`', value='Use `!leaderboard` or `!table` to see the current standings (sorted by games won)', inline=False)
            info.add_field(name='__Check elo__ - `!elo summoner`', value='Check your elo and have it come up in a text channel!', inline=False)
            info.add_field(name='__See random tip__ - `!tip`', value='Get a random loading screen tip', inline=False)
            await message.channel.send(embed=info)
        elif args[0] == KEY_CHAR + 'tip':
            with open('lolfacts.txt') as f:
                content = f.readlines()
            # you may also want to remove whitespace characters like `\n` at the end of each line
            content = [x.strip() for x in content] 
            await message.channel.send(content[random.randint(0,len(content)-1)])
        elif args[0] == KEY_CHAR + 'elo':
            await message.channel.send('Disabled for now')
            return
            # Finds a given player's elo
            if (len(args) >= 2):
                async with message.channel.typing():
                    profile = ''
                    for a in args[1:]:
                        profile = profile + str(a) + ' '
                    profile = profile[:-1]
                    url = "https://u.gg/lol/profile/euw1/{}/overview".format(profile)
                    chrome_options = Options()  
                    chrome_options.add_argument("--headless") # Opens the browser up in background
                    # chrome_options.add_argument('--disable-gpu')
                    # chrome_options.add_argument("--disable-infobars")
                    # chrome_options.add_argument("--disable-extensions")
                    # chrome_options.add_argument("--no-sandbox")
                    chrome_options.add_argument('--no-sandbox')
                    # chrome_options.add_argument("--disable-dev-shm-usage")
                    chrome_options.add_argument('--remote-debugging-port=9222')
                    chrome_options.add_argument('--disable-gpu')
                    if os.getenv('GOOGLE_CHROME_BIN') != 'no':
                        chrome_options.binary_location = os.getenv('GOOGLE_CHROME_BIN') # Sets chrome path
                    response = ''
                    with Chrome(options=chrome_options) as browser:
                        browser.get(url)
                        try:
                            print("Waiting until page loads (could take up to 20s")
                            wait = WebDriverWait(browser, 20)
                            wait.until(ec.title_contains("LoL Profile for"));
                            print(browser.title)
                            response = browser.page_source
                        except:
                            await message.channel.send('Could not find ranked information for `' + profile + '` (EUW), or request time out')
                            return
                        finally:
                            browser.quit()
                            # await message.channel.send('Request timed out')
                            # return
                    soup = BeautifulSoup(response, "html.parser")
                    # with open('response.txt', 'w') as f:
                    #     print(str(soup), file=f)
                    aas = soup.find_all("div", class_="rank-text")
                if (len(aas) == 0):
                    await message.channel.send('Could not find ranked information for `' + profile + '` (EUW)')
                else:
                    rankText = aas[0].find_all('strong')[0]
                    if rankText.text != 'Unranked':
                        colstr = rankText['style'][7:]
                        if(colstr == ""):
                            colstr = aas[1].find_all('strong')[0]['style'][7:]
                        colstr.replace(' ','')
                        rgbColStr = colstr[colstr.find("(")+1:colstr.find(")")].split(",")
                        colstr = '%02x%02x%02x' % (int(rgbColStr[0]), int(rgbColStr[1]), int(rgbColStr[2]))
                    else:
                        colstr = ''
                    col = '000000'
                    if (len(colstr) == 0):
                        col = hex(int('000000', 16))
                    else:
                        col = hex(int(colstr, 16))
                    elo=discord.Embed(title='Elo for: **__' + str(profile) + '__**', color=int(col, 16))
                    elo.add_field(name='Ranked Solo/Duo', value=aas[0].text, inline=True)
                    if len(aas) > 1:
                        print("Flex rank = " + aas[1].text)
                        if len(aas[1].text) > 2:
                            elo.add_field(name='Ranked Flex', value=aas[1].text, inline=True)
                    elo.set_footer(text='Stats according to u.gg')
                    await message.channel.send(embed=elo)
            else:
                await message.channel.send('Enter the name of the player to lookup')
        # Show table
        elif args[0] == KEY_CHAR + 'table' or args[0] == KEY_CHAR + 'leaderboard':
            await message.channel.send('https://crustacean-corner-website-real.herokuapp.com/')
            return
            sql = "SELECT * FROM results ORDER BY w DESC"
            conn = sqlite3.connect('scrims.db')
            cursor = conn.cursor()
            cursor.execute(sql)
            data = cursor.fetchall()
            players = []
            table=discord.Embed(title='Standings:', color=0x76105b)
            table.add_field(name='\u200b', value='Position', inline=True)
            table.add_field(name='\u200b', value='Wins/Played', inline=True)
            table.add_field(name='\u200b', value='WR', inline=True)
            pos = 1
            for (pid, played, wins) in data:
                table.add_field(name='\u200b', value=str(pos) + '. <@{}>'.format(pid), inline=True)
                table.add_field(name='\u200b', value=str(wins) + '/' + str(played), inline=True)
                if played == 0:
                    table.add_field(name='\u200b', value=str(0), inline=True)
                else:
                    table.add_field(name='\u200b', value=str(wins/played * 100), inline=True)
                pos+=1
            
            await message.channel.send(embed=table)
        elif args[0] == KEY_CHAR + 'report':
            global processing_result
            if processing_result:
                await message.add_reaction('❌')
                return
            processing_result = True
            # Report score
            if not args[1].isnumeric():
                await message.channel.send('Invalid match id. Report in the form `!report <match id> <result>')
                processing_result = False
                return
            match_id = int(args[1])
            match_result = args[2].lower()
            game_data = games_db.find_one({'match_id': match_id, 'resolved': False})
            print(game_data)
            if (game_data == None):
                await message.channel.send('No ongoing match with that ID')
                processing_result = False
                return
            team1 = game_data['team1']
            team2 = game_data['team2']
            remake = False
            if not (message.author.id in team1 or message.author.id in team2):
                await message.channel.send('You\'re not playing in that match!')
                processing_result = False
                return
            if match_result in ['w', 'win', 'victory']:
                if message.author.id in team1:
                    winning_team = team1
                    losing_team = team2
                else:
                    winning_team = team2
                    losing_team = team1
            elif match_result in ['l', 'loss', 'lose']:
                if message.author.id in team2:
                    winning_team = team1
                    losing_team = team2
                else:
                    winning_team = team2
                    losing_team = team1
            elif match_result in ['remake']:
                update_entry = {'$set': {
                    'resolved': True,
                    'time_finished': datetime.datetime.now()
                }}
                # match_data = games_db.find_one({'id': match_id})
                games_db.update_one({'match_id': match_id}, update_entry)
                await message.add_reaction('✅')
                processing_result = False
                return
            else:
                await message.channel.send('Match result must be either win, loss, or remake')
                processing_result = False
                return
            await message.add_reaction('⏳')
            if (game_data['q_id'] == 'plat'):
                leaderboard_db = leaderboard_collection.plat
            elif (game_data['q_id'] == 'diamond'):
                leaderboard_db = leaderboard_collection.dia
            elif (game_data['q_id'] == 'universal'):
                leaderboard_db = leaderboard_collection.universal
            for p in winning_team:
                player_data = leaderboard_db.find_one({'id': p, 'q_id': game_data['q_id']})
                if player_data == None:
                    # new entry
                    uname = roles_db.find_one({'_id': p})['username']
                    leaderboard_db.insert_one({
                        'id': p,
                        'q_id': game_data['q_id'],
                        'username': uname,
                        'played': 1,
                        'won': 1,
                        'lost': 0,
                        'elo': 110,
                        'wr': 1
                    })
                else:
                    wr = round(float(player_data['won']+1)/float(player_data['played']+1),2)
                    update_entry = {'$set': {
                        'played': player_data['played']+1,
                        'won': player_data['won']+1,
                        'elo': max(player_data['elo']+10, 0),
                        'wr': wr,
                    }}
                    leaderboard_db.update_one({'id': p}, update_entry)
            for p in losing_team:
                player_data = leaderboard_db.find_one({'id': p})
                if player_data == None:
                    # new entry
                    uname = roles_db.find_one({'_id': p})['username']
                    leaderboard_db.insert_one({
                        'id': p,
                        'q_id': game_data['q_id'],
                        'username': uname,
                        'played': 1,
                        'won': 0,
                        'lost': 1,
                        'elo': 100-6,
                        'wr': 0
                    })
                else:
                    wr = round(float(player_data['won'])/float(player_data['played']+1),2)
                    update_entry = {'$set': {
                        'played': player_data['played']+1,
                        'lost': player_data['lost']+1,
                        'elo': max(player_data['elo']-6, 0),
                        'wr': wr,
                    }}
                    leaderboard_db.update_one({'id': p}, update_entry)
            update_entry = {'$set': {
                'resolved': True,
                'time_finished': datetime.datetime.now()
            }}
            games_db.update_one({'match_id': match_id}, update_entry)
            processing_result = False
            await message.add_reaction('✅')
        elif args[0] == KEY_CHAR + 'show' and q_id != None:
            # Show queue
            if len(dict_q[q_id]) > 0:
                msg = ''
                for (id,roles) in dict_q[q_id]:
                    msg = msg + '<@{}>'.format(id) + '\n'
                msg = msg[:-1]
                showQ=discord.Embed(title=str(len(dict_q[q_id])) + ' players currently in queue', description=msg, color=0x76105b)
                await message.channel.send(embed=showQ)
            else:
                await message.channel.send('No queue right now. Type !q or !queue to start one')
        #COPYPASTAS
        elif args[0] == KEY_CHAR + 'cancel' and q_id != None and "admin" in [y.name.lower() for y in message.author.roles]:
            dict_q[q_id] = []
            embedVal = '__**{}**__ cancelled the queue.'.format(message.author.name)
            cancelQ=discord.Embed(title=str(len(dict_q[q_id])) + ' players are currently in the queue', description=embedVal, color=0x76105b)
            await message.channel.send(embed=cancelQ)
        elif args[0] == KEY_CHAR + 'leave' and q_id != None:
            # Leave queue
            if len(dict_q[q_id]) > 0:
                id = str(message.author.id)
                inQ = False
                for (pid,roles) in dict_q[q_id]:
                    if (str(pid) == id):
                        inQ = True
                        dict_q[q_id].remove((pid,roles))
                if inQ:
                    desc = '__**{}**__ left.'.format(message.author.name)
                    leaveQ=discord.Embed(title=str(len(dict_q[q_id])) + ' players currently in queue', description=desc, color=0x76105b)
                    await message.channel.send(embed=leaveQ)
                else:
                    await message.channel.send('You\'re not in the queue right now')
            else:
                await message.channel.send('No queue right now. Type !q or !queue to start one')
        elif args[0] == KEY_CHAR + 'q' and q_id != None:
            #Join q
            data = roles_db.find_one({'_id': message.author.id})
            if data == None:
                await message.channel.send('You\'re not set up yet. Add your roles to join the queue')
            else:
                id = data['_id']
                roles = data['roles']
                inq = False
                for (user_id, _) in dict_q[q_id]:
                    if user_id == id:
                        inq = True
                if inq:
                    await message.channel.send('You\'re already in the queue!')
                else:
                    splitroles = roles.split(',')
                    rolesindex = []
                    for r in validroles:
                        if splitroles.__contains__(r):
                            rolesindex.append(1)
                        else:
                            rolesindex.append(0)
                    dict_q[q_id].append((id,rolesindex))
                    if len(dict_q[q_id]) < 10:
                        # await message.channel.send('Ok, joined queue. There are currently ' + str(len(q)) + ' People in the queue')
                        embedVal = '__**{}**__ has joined.'.format(message.author.name)
                        joinQ=discord.Embed(title=str(len(dict_q[q_id])) + ' players are currently in the queue', description=embedVal, color=0x76105b)
                        # joinQ.add_field(name='\u200b', value=embedVal, inline=False)
                        await message.channel.send(embed=joinQ)
                    else:
                        ids = []
                        qroles = []
                        # get list of roles and discord ids from queue
                        for (id,qrole) in dict_q[q_id]:
                            ids.append(id)
                            qroles.append(qrole)
                        # split into two teams (bipartite matching)
                        (team1,team2,autofill) = split_teams(ids, qroles)
                        # assign match id
                        old_ids = games_db.distinct('match_id')
                        # first match ever
                        if len(old_ids) == 0:
                            match_id = 1000
                        else:
                            # new match id is one more than old ones
                            match_id = max(old_ids) + 1
                        # create embed
                        if autofill:
                            description = 'Autofill is enabled for some players, feel free to swap roles among yourselves\n**MATCH ID**: '+str(match_id)
                        else:
                            description = 'No autofilled players in this, feel free to swap roles among yourselves\n**MATCH ID**: ' + str(match_id)
                        description += '\nCheck your DMs for lobby information!'
                        embed=discord.Embed(title='Queue Popped!', description=description, color=0x76105b)
                        team1Msg = ''
                        team2Msg = ''
                        for i in range(len(team1)):
                            team1Msg = team1Msg + validroles[i] + ': <@{}>'.format(team1[i]) + '\n'
                        team1Msg = team1Msg[:-1]
                        embed.add_field(name='-Team 1-', value=team1Msg, inline=True)
                        for i in range(len(team2)):
                            team2Msg = team2Msg + validroles[i] + ': <@{}>'.format(team2[i]) + '\n'
                        team2Msg = team2Msg[:-1]
                        embed.add_field(name='-Team 2-', value=team2Msg, inline=True)
                        embed.add_field(name='Lobby creator', value='<@{}>'.format(ids[random.randint(0,9)]))
                        await message.channel.send(embed=embed)

                        
                        games_db.insert_one({
                            'match_id': match_id,
                            'q_id': q_id,
                            'team1': team1,
                            'team2': team2,
                            'resolved': False,
                            'time_finished': None,
                        })
                        match_name = 'cc' + str(match_id)
                        match_pass = str(random.randint(1000,9999))
                        info_embed=discord.Embed(title='Lobby Details', description='**lobby name:** {} \n**password: **{}'.format(match_name, match_pass),color=0x76105b)
                        # send dms
                        for (id,qrole) in dict_q[q_id]:
                            user = 'pass'
                            if int(id) > 10:
                                user = await dc_client.fetch_user(int(id))
                            if user != 'pass':
                                await user.send('Your queue has popped! Please join the lobby chat')
                                await user.send(embed=embed)
                                await user.send(embed=info_embed)
                        # reset queue
                        dict_q[q_id] = []
        elif (args[0] == KEY_CHAR + 'removeroles' or args[0] == KEY_CHAR + 'remove'):
            if message.channel.id != 972118405631062056:
                await message.delete()
            if len(args) > 1:
                data = roles_db.find_one({'_id': message.author.id})
                if data == None:
                    await message.channel.send('You aren\'t on the database. Use !addroles before you remove them xx')
                else:
                    id = data['_id']
                    roles = data['roles']
                    removeroles = args[1:]
                    if len(removeroles) > 5:
                        await message.channel.send('Too many roles (you daft clown), none removed')
                    else:
                        invalidroles = []
                        preexistingroles = []
                        insertroles = []
                        for nr in removeroles:
                            nr.lower()
                            if nr in ['supp', 'sup']:
                                nr = 'support'
                            if nr == 'jg':
                                nr = 'jungle'
                            if nr in ['bot', 'bottom']:
                                nr = 'adc'
                            if not validroles.__contains__(nr):
                                invalidroles.append(nr)
                            elif not nr in roles:
                                preexistingroles.append(nr)
                            else:
                                insertroles.append(nr)
                        if len(invalidroles) > 0:
                            await message.channel.send('These roles were not recognised, so were not removed: ' + str(invalidroles))
                        if len(preexistingroles) > 0:
                            await message.channel.send('You don\'t have these roles, so were not removed: ' + str(preexistingroles))
                        if len(insertroles) > 0:
                            # if stored object exist and we need update it
                            if ...:
                                for rr in removeroles:
                                    roles = roles.replace(rr,'')
                                roles = roles.replace(',,,',',')
                                roles = roles.replace(',,',',')
                                if (len(roles) == 0):
                                    await message.channel.send('You can\'t remove all roles, so none were removed.')
                                else:
                                    if (roles[0] == ','):
                                        roles = roles = roles[1:]
                                    if (roles[-1] == ','):
                                        roles = roles = roles[:-1]
                                    data
                                    # await message.channel.send('Ok, <@{}> updated roles are: '.format(id) + roles)
                                    newroles = roles
                                    # sql = "UPDATE roles SET roles = ? WHERE id = ?"
                                    update_entry = {'$set': {
                                        'roles': newroles
                                    }}
                                    roles_db.update_one({'_id': id}, update_entry)
                                    embedTitle = "Ok, __**{}**__'s updated roles are:".format(message.author.name)
                                    roleList = roles.split(',')
                                    description = ''
                                    for r in roleList:
                                        description += r + "\n"
                                    removed=discord.Embed(title=embedTitle, description=description, color=0x76105b)
                                    await message.channel.send(embed=removed)
                            else:
                                # get data from first object
                                value_of_field_1 = data[0][0]
                                # get data from third object
                                value_of_field_2 = data[2][1]
                            # close database connection
            else:
                await message.channel.send('Please specify roles you want to add')
        elif (args[0] == KEY_CHAR + 'addroles' or args[0] == KEY_CHAR + 'add'):
            if message.channel.id != 972118405631062056:
                await message.delete()
                return
            # add role
            if len(args) > 1:
                data = roles_db.find_one({'_id': message.author.id})
                # get stored object from database
                print(message.author.id)
                newroles = args[1:]
                # if object does not exist, create it
                if data == None:
                    invalidroles = []
                    preexistingroles = []
                    insertroles = ''
                    newroles = list(dict.fromkeys(newroles))
                    for nr in newroles:
                        nr.lower()
                        if nr in ['supp', 'sup']:
                            nr = 'support'
                        if nr == 'jg':
                            nr = 'jungle'
                        if nr in ['bot', 'bottom']:
                            nr = 'adc'
                        if not validroles.__contains__(nr):
                            invalidroles.append(nr)
                        else:
                            insertroles = insertroles + nr + ','
                    if len(insertroles) > 0:
                        insertroles = insertroles[:-1]
                        uname = await dc_client.fetch_user(message.author.id)
                        new_entry = {
                            '_id': message.author.id,
                            'roles': insertroles,
                            'username': str(uname)[:-5],
                        }
                        result = roles_db.insert_one(new_entry)
                        added=discord.Embed(title='__**{}**__ added to database'.format(message.author.name), color=0x76105b)
                        added.add_field(name='Roles', value=insertroles, inline=False)
                        if len(invalidroles) > 0:
                            added.add_field(name='Invalid roles (not added)', value=str(invalidroles), inline=False)
                        await message.channel.send(embed=added)
                    else:
                        await message.channel.send('No valid roles were entered, so you were not added to the database')
                else:
                    # Case when player exists on db already
                    print(data)
                    id = data['_id']
                    roles = data['roles']
                    if len(newroles) > 5:
                        await message.channel.send('Too many roles detected, maximum 5 roles can be added. Obviously, you stupid, stupid idiot. I\'m not even going to bother adding the right ones if there were any. Retype it now you dog.')
                    else:
                        invalidroles = []
                        preexistingroles = []
                        insertroles = ''
                        newroles = list(dict.fromkeys(newroles))
                        for nr in newroles:
                            if not validroles.__contains__(nr):
                                invalidroles.append(nr)
                            elif nr in roles:
                                preexistingroles.append(nr)
                            else:
                                insertroles = insertroles + nr + ','
                        insertroles = insertroles[:-1]
                        if len(insertroles) > 0:
                            # if stored object exist and we need update it
                            if ...:
                                newroles = roles + ',' + insertroles
                                # sql = "UPDATE roles SET roles = ? WHERE id = ?"
                                update_entry = {'$set': {
                                    'roles': newroles
                                }}
                                roles_db.update_one({'_id': id}, update_entry)
                                description=newroles
                            else:
                                # get data from first object
                                value_of_field_1 = data[0][0]
                                # get data from third object
                                value_of_field_2 = data[2][1]
                        else:
                            description = '(No change) ' + str(roles)
                        
                        roleList = description.split(",")
                        description = ""
                        for r in roleList:
                            description += r + "\n"
                        added=discord.Embed(title='Ok, __*{}*__\'s updated roles:'.format(message.author.name), description=description, color=0x76105b)
                        if len(invalidroles) > 0:
                            added.add_field(name='Invalid roles (not added)', value=str(invalidroles), inline=False)
                        if len(preexistingroles) > 0:
                            added.add_field(name='Preexisting roles (not added)', value=str(preexistingroles), inline=False)
                        await message.channel.send(embed=added)
                        # close database connection
            else:
                await message.channel.send('Please specify roles you want to add')
        elif args[0] == KEY_CHAR + 'a':
            if message.channel.id != 972118405631062056:
                await message.delete()
                return
            if len(args) < 2:
                await message.channel.send("Please include the role you want to add")
            if (args[1] in ['plat-','plat']):
                user = message.author
                role = discord.utils.get(user.guild.roles, name="Plat-")
                await user.add_roles(role)
                await message.channel.send("Role 'plat-' added")
            elif (args[1] in ['diamond+', 'diamond', 'dia']):
                user = message.author
                role = discord.utils.get(user.guild.roles, name="Diamond+")
                await message.channel.send("Role 'diamond+' added")
                await user.add_roles(role)
            else:
                await message.channel.send("Invalid role specified, please choose either `plat` or `diamond`")
        elif args[0] == KEY_CHAR + 'r':
            if message.channel.id != 972118405631062056:
                await message.delete()
                return
            if len(args) < 2:
                await message.channel.send("Please include the role you want to remove")
            if (args[1] in ['plat-','plat']):
                user = message.author
                role = discord.utils.get(user.guild.roles, name="Plat-")
                await user.remove_roles(role)
                await message.channel.send("Role 'plat-' removed")
            elif (args[1] in ['diamond+', 'diamond', 'dia']):
                user = message.author
                role = discord.utils.get(user.guild.roles, name="Diamond+")
                await user.remove_roles(role)
                await message.channel.send("Role 'diamond+' removed")
            else:
                await message.channel.send("Invalid role specified, please choose either `plat` or `diamond`")


        elif message.content.startswith(KEY_CHAR + 'checkroles') or message.content.startswith(KEY_CHAR + 'roles'):
            if message.channel.id != 972118405631062056:
                await message.delete()
                return
            # return current roles
            data = roles_db.find_one({'_id': message.author.id})
            print(data)
            msg = ''
            if data == None:
                msg = "You haven't assigned your roles yet!"
            else:
                id = data['_id']
                msg = data['roles']
            roles = msg.split(",")
            description = ""
            for r in roles:
                description += r + "\n"
            checkRoles=discord.Embed(title='Roles for ' + message.author.name, description=description, color=0x76105b)
            await message.channel.send(embed=checkRoles)
        # ADMIN COMMANDS (CHECK ROLE)
        elif args[0] in [KEY_CHAR + 'del', KEY_CHAR + 'delete']:
            if len(args) > 1:
                del_id = int(re.sub('[^0-9]','',args[1]))
                data = roles_db.find_one({'_id': int(del_id)})
                if data != None:
                    roles_db.delete_one({'_id': del_id})
                    await message.channel.send('Deleted <@{}> from db'.format(del_id))
                else:
                    await message.channel.send('Couldn\'t find user')

        

# print(os.getenv('ACCESS_TOKEN'))
dc_client.run(os.getenv('ACCESS_TOKEN'))
mongo_client
