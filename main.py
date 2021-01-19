from bs4 import BeautifulSoup

import requests
import urllib.request
import shutil

import discord
import networkx as nx
import random
import sqlite3
from numpy.lib.shape_base import split
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import maximum_bipartite_matching

import os

# roles [top, jg, mid, adc, supp]
client  = discord.Client()
a = [0,1,0,1,0] # 0
b = [1,1,1,1,0] # 1
c = [0,0,0,1,0] # 2
d = [0,0,1,0,0] # 3
e = [0,0,1,0,0] # 4
f = [0,1,0,0,0] # 5
g = [1,1,1,0,0] # 6
h = [1,1,1,0,0] # 7
I = [1,1,1,1,0] # 8
j = [1,0,1,1,0] # 9

q = []
gameTeam1 = []
gameTeam2 = []
validroles = ['top','jungle','mid','adc','support']

#split into two teams, matching maximum amount of players
def split_teams(ids, players):
    autofill = False
    for p in players:
        p.extend(p)
    order = list(range(0,10))
    n = 0
    random.shuffle(order)
    print('order',order)
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

@client.event
async def on_ready():
    print('Logged in as {0.user}'.format(client))

# Handle messages
@client.event
async def on_message(message):
    # Ignore if message is from bot
    if message.author == client.user:
        return
    args = str(message.content).split()
    if message.content.startswith('$testscrim'):
        # sample scrim with players a-j
        global q
        q.extend([('1',a),('2',b),('3',c),('4',d),('5',e),('6',f),('7',g),('8',h)])
        await message.channel.send('9 players in q')
    # Nsfw message
    if message.content.startswith('!') and ('porn' in message.content or 'nsfw' in message.content or 'hentai' in message.content):
        if message.channel.nsfw:
            url = "https://rule34.xxx/?page=post&s=list&tags=league_of_legends&pid=" + str(random.randint(0,10000))
            response = requests.get(url)
            soup = BeautifulSoup(response.text, "html.parser")
            aas = soup.find_all("span", class_="thumb")
            response = requests.get('https://rule34.xxx/' + aas[0].find("a")['href'])
            soup = BeautifulSoup(response.text, "html.parser")
            aas = soup.find_all("img")
            await message.channel.send(aas[2]['src'])
        else:
            await message.channel.send('Not an nsfw channel you horny bastard xx')
    else:
        # Information
        if args[0] == '!info':
            info=discord.Embed(title='Commands:', color=0x76105b)
            info.add_field(name='Adding roles - `!add`', value='Add your role using the `!addroles` or `!add` command. It would look something like \n`!addroles top jungle mid adc support` \nThis will automatically add you to the database on first use', inline=False)
            info.add_field(name='Removing roles - `!remove`', value='Remove your roles in the same way using `!removeroles` or `!remove`', inline=False)
            info.add_field(name='Queueing - `!q`', value='Use `!q` or `!queue` to queue up and `!leave` to leave', inline=False)
            info.add_field(name='Report score - `!report`', value='Use `!report win` to report a win for your team or lose for vice versa. \nUse `!report remake` if you decide to cancel the game', inline=False)
            info.add_field(name='See standings - `!table`', value='Use `!leaderboard` or `!table` to see the current standings (sorted by games won)', inline=False)
            await message.channel.send(embed=info)
        elif args[0] == '!elo':
            # Finds a given player's elo
            if (len(args) >= 2):
                profile = ''
                for a in args[1:]:
                    profile = profile + str(a) + ' '
                profile = profile[:-1]
                url = "https://u.gg/lol/profile/euw1/{}/overview".format(profile)
                response = requests.get(url)
                soup = BeautifulSoup(response.text, "html.parser")
                aas = soup.find_all("div", class_="rank-text")
                if not (len(aas) == 2):
                    await message.channel.send('Could not find ranked information for `' + profile + '` (EUW)')
                else:
                    colstr = aas[0].find_all('strong')[0]['style'][7:]
                    if(colstr == ""):
                        colstr = aas[1].find_all('strong')[0]['style'][7:]
                    col = 'ffffff'
                    if (len(colstr) == 0):
                        col = hex(int('ffffff', 16))
                    else:
                        col = hex(int(colstr, 16))
                    elo=discord.Embed(title='Elo for: **__' + str(profile) + '__**', color=int(col, 16))
                    elo.add_field(name='Ranked Solo/Duo', value=aas[0].text, inline=True)
                    elo.add_field(name='Ranked Flex', value=aas[1].text, inline=True)
                    await message.channel.send(embed=elo)
            else:
                await message.channel.send('Enter the name of the player to lookup')
        elif args[0] == '!cefsmitesim':
            smitechance = random.randint(0,100)
            if smitechance >= 95:
                await message.channel.send('Uh oh, youcef smited your cannon!')
            elif smitechance >= 85:
                await message.channel.send('Youcef successfully smited drake!')
            elif smitechance >= 75:
                await message.channel.send('What the fuck, Youcef is farming krugs')
            else:
                await message.channel.send('Youcef missed smite! (AGAIN)')
        # Show table
        elif args[0] == '!table' or args[0] == '!leaderboard':
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
        elif args[0] == '!report':
            # Report score
            id = message.author.id
            team = 2
            global gameTeam1
            global gameTeam2
            teams = [gameTeam1, gameTeam2]
            print(gameTeam1)
            print(gameTeam2)
            if gameTeam1.__contains__(str(id)):
                team = 0
            elif gameTeam2.__contains__(str(id)):
                team = 1
            if team == 2:
                await message.channel.send('You\'re not playing in any games right now')
            else:
                if args[1] == 'lose':
                    team = (team+1)%2
                if args[1] == 'remake':
                    await message.channel.send('Ok, no ones score updated')
                else:
                    winners = teams[team]
                    losers = teams[(team+1)%2]
                    conn = sqlite3.connect('scrims.db')
                    cursor = conn.cursor()
                    # get stored object from database
                    for p in winners:
                        if len(p) > 2:
                            print('updating ', p)
                            sql = "SELECT * FROM results WHERE id = ?"
                            cursor.execute(sql, (p,))
                            data = cursor.fetchall()
                            print(data)
                            (id, played, wins) = data[0]
                            sql = "UPDATE results SET w = ? WHERE id = ?"
                            cursor.execute(sql, [(wins + 1), (p)])
                            sql = "UPDATE results SET played = ? WHERE id = ?"
                            cursor.execute(sql, [(played + 1), (p)])
                    for p in losers:
                        if len(p) > 2:
                            sql = "SELECT * FROM results WHERE id = ?"
                            cursor.execute(sql, (p,))
                            data = cursor.fetchall()
                            (id, played, wins) = data[0]
                            sql = "UPDATE results SET played = ? WHERE id = ?"
                            cursor.execute(sql, [(played + 1), (p)])
                    conn.commit()
                    conn.close()
                gameTeam1 = []
                gameTeam2 = []
        elif args[0] == '!show':
            # Show queue
            if len(q) > 0:
                msg = ''
                for (id,roles) in q:
                    msg = msg + '<@{}>'.format(id) + '\n'
                msg = msg[:-1]
                showQ=discord.Embed(title=str(len(q)) + ' players currently in queue', description=msg, color=0x76105b)
                await message.channel.send(embed=showQ)
            else:
                await message.channel.send('No queue right now. Type !q or !queue to start one')
        #COPYPASTAS
        elif args[0] == '!stfu' or args[0] == '!shut':
            await message.channel.send("I know you have something to say and I know you're eager to say it so I'll get right to the point: Shut the fuck up. Nobody wants to hear it. Nobody will ever want to hear it. Nobody cares. And the fact that you thought someone might care is honestly baffling to me. I've actually pulled the entire world. Here's a composite of the faces of everybody who wants you to shut the fuck up. It seems as if this is a composite of every human being on the planet. Interesting. Now for a composite of the faces that want you to keep talking: Interesting it seems as if nothing has happened. Here's the world map. Now here's the text: Shit the fuck up. That's what you should do. But you know what? Maybe I am being a little too harsh here. I actually do have it on good authority thanks to my pulling data that there is as at least 1 person who actually wants to hear you speak. It's a little child in Mozambique and he- oh? He's dead? Well sorry man I guess nobody wants to hear you talk anymore. Please shut the fuck up. I'm not just telling you to shut up, I'm telling you to shut the FUCK up and you need to hear it. This is a public service. I have nothing to gain from this, except by telling YOU exactly what you need to hear. And on that note let me make this clear: This isn't a broad message I'm aiming at all of you, this is a message specifically pointed at you. That's right! You! You know who you are. And I'm sick of your shit. We all are. The only good you will ever do for humanity is refusing to participate in it. You can take a vow of silence, join a monastery, you can even just be a mime! Mimes are fun. But you kinda know that what I'm saying is true already don't you?")
            await message.channel.send("You understand that you really should shut the fuck up, why do you keep speaking? I'm genuinely curious. Why do you think you deserve to be heard? The core of what I'm getting at is that you are not a worthwhile person. You are not worth listening to. Everything you've said has been said before more eloquently and more coherently. And it's not that everything has been said we still need people to have discourse in order to say new things and discover new things about ourselves and humanity but you, you will never be those people so shut the fuck up.")
            await message.channel.send("<@245619552438845461>")
        elif args[0] == '!based':
            await message.channel.send("Based? Based on what? In your dick? Please shut the fuck up and use words properly you fuckin troglodyte, do you think God gave us a freedom of speech just to spew random words that have no meaning that doesn't even correllate to the topic of the conversation? Like please you always complain about why no one talks to you or no one expresses their opinions on you because you're always spewing random shit like poggers based cringe and when you try to explain what it is and you just say that it's funny like what? What the fuck is funny about that do you think you'll just become a stand-up comedian that will get a standing ovation just because you said \"cum\" in the stage? HELL NO YOU FUCKIN IDIOT, so please shut the fuck up and use words properly you dumb bitch")
        elif args[0] == '!leave':
            # Leave queue
            if len(q) > 0:
                id = str(message.author.id)
                inQ = False
                for (pid,roles) in q:
                    if (str(pid) == id):
                        inQ = True
                        q.remove((pid,roles))
                if inQ:
                    desc = '<@{}> left.'.format(id)
                    leaveQ=discord.Embed(title=str(len(q)) + ' players currently in queue', description=desc, color=0x76105b)
                    await message.channel.send(embed=leaveQ)
                else:
                    await message.channel.send('You\'re not even in the queue!')
            else:
                await message.channel.send('No queue right now. Type !q or !queue to start one')
        elif args[0] == '!q':
            #Join q
            conn = sqlite3.connect('scrims.db')
            cursor = conn.cursor()
            # get stored object from database
            sql = "SELECT * FROM roles WHERE id = ?"
            cursor.execute(sql, (message.author.id,))
            data = cursor.fetchall()
            if len(data) == 0:
                await message.channel.send('You\'re not set up yet. Add your roles to join the queue')
            else:
                (id, roles) = data[0]
                inq = False
                for (q_id, _) in q:
                    if q_id == id:
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
                    q.append((id,rolesindex))
                    if len(q) < 10:
                        # await message.channel.send('Ok, joined queue. There are currently ' + str(len(q)) + ' People in the queue')
                        embedVal = '<@{}> has joined.'.format(id)
                        joinQ=discord.Embed(title=str(len(q)) + ' players are currently in the queue', description=embedVal, color=0x76105b)
                        # joinQ.add_field(name='\u200b', value=embedVal, inline=False)
                        await message.channel.send(embed=joinQ)
                    else:
                        ids = []
                        qroles = []
                        atMessage = ''
                        for (id,qrole) in q:
                            ids.append(id)
                            atMessage = atMessage + '<@{}>'.format(id)
                            qroles.append(qrole)
                        await message.channel.send(atMessage)
                        (team1,team2,autofill) = split_teams(ids, qroles)
                        gameTeam1 = team1
                        gameTeam2 = team2
                        if autofill:
                            description = 'Autofill is enabled for some players, feel free to swap roles among yourselves'
                        else:
                            description = 'No autofilled players in this, feel free to swap roles among yourselves'
                        embed=discord.Embed(title='Queue Popped!', description=description, color=0x76105b)
                        q = []
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
                        await message.channel.send(embed=embed)
        elif args[0] == '!removeroles' or args[0] == '!remove':
            #remove role
            if len(args) > 1:
                conn = sqlite3.connect('scrims.db')
                cursor = conn.cursor()
                # get stored object from database
                print(message.author.id)
                sql = "SELECT * FROM roles WHERE id = ?"
                cursor.execute(sql, (message.author.id,))
                data = cursor.fetchall()
                if len(data) == 0:
                    await message.channel.send('You aren\'t on the database. Use !addroles before you remove them xx')
                else:
                    (id, roles) = data[0]
                    removeroles = args[1:]
                    if len(removeroles) > 5:
                        await message.channel.send('Too many roles (you daft clown), none added')
                    else:
                        invalidroles = []
                        preexistingroles = []
                        insertroles = []
                        for nr in removeroles:
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
                                    sql = "UPDATE roles SET roles = ? WHERE id = ?"
                                    cursor.execute(sql, [(roles), (message.author.id)])
                                    await message.channel.send('Ok, <@{}> updated roles are: '.format(id) + roles)
                            else:
                                # get data from first object
                                value_of_field_1 = data[0][0]
                                # get data from third object
                                value_of_field_2 = data[2][1]
                            # close database connection
                        conn.commit()
                        conn.close()
            else:
                await message.channel.send('Please specify roles you want to add')
        elif args[0] == '!addroles' or args[0] == '!add':
            # add role
            if len(args) > 1:
                conn = sqlite3.connect('scrims.db')
                cursor = conn.cursor()
                # get stored object from database
                print(message.author.id)
                sql = "SELECT * FROM roles WHERE id = ?"
                cursor.execute(sql, (message.author.id,))
                data = cursor.fetchall()
                newroles = args[1:]
                # if object does not exist, create it
                if len(data) == 0:
                    invalidroles = []
                    preexistingroles = []
                    insertroles = ''
                    for nr in newroles:
                        if not validroles.__contains__(nr):
                            invalidroles.append(nr)
                        else:
                            insertroles = insertroles + nr + ','
                    if len(insertroles) > 0:
                        insertroles = insertroles[:-1]
                        sql = "INSERT INTO roles VALUES (?, ?)"
                        cursor.execute(sql, [(message.author.id), (insertroles)])
                        sql = "INSERT INTO results VALUES (?, ?, ?)"
                        cursor.execute(sql, [(message.author.id), 0, 0])
                        conn.commit()
                        conn.close()
                        added=discord.Embed(title='<@{}> added to database'.format(message.author.id), color=0x76105b)
                        added.add_field(name='Roles', value=insertroles, inline=False)
                        if len(invalidroles) > 0:
                            added.add_field(name='Invalid roles (not added)', value=str(invalidroles), inline=False)
                        await message.channel.send(embed=added)
                    else:
                        await message.channel.send('No valid roles were entered, so you were not added to the database')
                else:
                    # Case when player exists on db already
                    print(data)
                    (id, roles) = data[0]
                    if len(newroles) > 5:
                        await message.channel.send('Too many roles detected, maximum 5 roles can be added. Obviously, you stupid, stupid idiot. I\'m not even going to bother adding the right ones if there were any. Retype it now you dog.')
                    else:
                        invalidroles = []
                        preexistingroles = []
                        insertroles = ''
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
                                sql = "UPDATE roles SET roles = ? WHERE id = ?"
                                cursor.execute(sql, [(newroles), (message.author.id)])
                                description=newroles
                            else:
                                # get data from first object
                                value_of_field_1 = data[0][0]
                                # get data from third object
                                value_of_field_2 = data[2][1]
                        else:
                            description = '(No change) ' + str(roles)
                        added=discord.Embed(title='Updated roles', description=description, color=0x76105b)
                        if len(invalidroles) > 0:
                            added.add_field(name='Invalid roles (not added)', value=str(invalidroles), inline=False)
                        if len(preexistingroles) > 0:
                            added.add_field(name='Preexisting roles (not added)', value=str(preexistingroles), inline=False)
                        await message.channel.send(embed=added)
                        # close database connection
                        conn.commit()
                        conn.close()
            else:
                await message.channel.send('Please specify roles you want to add')
        if message.content.startswith('!checkroles'):
            # return current roles
            conn = sqlite3.connect('scrims.db')
            cursor = conn.cursor()
            sql = "SELECT * FROM roles WHERE id = ?"
            cursor.execute(sql, (message.author.id,))
            data = cursor.fetchall()
            print(data)
            msg = ''
            if len(data) == 0:
                msg = "You haven't assigned your roles yet!"
            else:
                (id, msg) = data[0]
            await message.channel.send(msg)
        

client.run(os.getenv('TOKEN'))