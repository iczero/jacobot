import urllib, urllib2
from cookielib import CookieJar
import socket
import re
from datetime import datetime
from time import sleep

from common import *

output = 2
def AlwaysRun(channel):
    global output
    global watched
    global history
    now = datetime.now()
    if now.minute % 10 == 0 and now.second ==  11:
        if now.hour%2 == 0 and now.minute == 10:
        #if now.minute == 0:
            history = {}
        GetStockInfo(True)
        if len(watched) or output:
            PrintStocks(channel, False, output != 1)
            PrintNews(channel, True)
        watched = []
        sleep(1)

def Login(channel, hostmask, username, password):
    for i in logins.values():
        if i["username"] == username:
            SendMessage(channel, "Someone else is already logged in as %s" % username)
            return False
    
    req = urllib2.Request("http://tptapi.com/login_proc.php?login", urllib.urlencode({"Username":username, "Password":password}))
    response = urllib2.urlopen(req)
    if response.read().find("login.php?error=1") > 0:
        SendMessage(channel, "Invalid password for %s" % username)
        return False
    cj = CookieJar()
    cj.extract_cookies(response, req)

    logins[hostmask] = {}
    logins[hostmask]["cookies"] = {}
    logins[hostmask]["portfolio"] = {}
    logins[hostmask]["username"] = username
    #logins[hostmask]["opener"] = opener

    tempcookies = []
    for i in list(cj):
        if i.name == "PHPSESSID":
            tempcookies.append("%s=%s" % (i.name, i.value))
    logins[hostmask]["cookies"] = "; ".join(tempcookies)
    SendMessage(channel, "Successfully logged in")
    return True

results = {}
history = {}
def GetStockInfo(new = False):
    page = GetPage("http://tptapi.com/getjson.php?type=stock")
    stocks = []
    stocks.extend(re.findall("\"([^\"]*)\"", page))
    for i in range(0,len(stocks), 4):
        results[stocks[i]] = {'value':stocks[i+2]}
        if (new):
            if not stocks[i] in history:
                history[stocks[i]] = []
            history[stocks[i]].append(int(stocks[i+2]))

def GetPortfolioInfo(account, element = None):
    page = GetPage("http://tptapi.com/portfolio.php", account)
    stocks = []
    for i in page.splitlines():
        stocks.extend(re.findall("<td width='\d+%'>([^<>]*)</td>", i))
    
    output = ""
    for i in range(0, len(stocks), 4):
        try:
            if stocks[i] == "":
                continue
            output = output + "07%s (%s): %s  " % (stocks[i], stocks[i+2], stocks[i+1])
            if element == stocks[i]:
                return int(stocks[i+1])
        except:
            pass
    if element:
        return None
    return output

def GetMoney(account):
    page = GetPage("http://tptapi.com/money.php", account)
    start = page.find("Current Balance:")+21
    return int(re.sub(",", "", page[start:start+page[start:].find(".")]))

#You cannot sell more stock than how much you own!
#INVALID Field!
def BuySellStocks(account, action, element, amount, stockClass = "1"):
    return GetPage("http://tptapi.com/stockProc.php?opt=%s&stock=%s" % (action, element), account, {"shares":amount,"class":stockClass}, True).replace("\n", " ")

def GetChange(old, new):
    #dividing by 0 is bad
    if old == 0:
        return "040%"
    if old < new:
        color = "09"
    elif old > new:
        color = "04"
    else:
        color = "08"
    return color + str(int((float(new)-old)/old*1000)/10.0) + "%"

watched = []
def PrintStocks(channel, allPercentages = False, onlyOwned = False):
    output = ""
    stocks = results.keys()
    if onlyOwned:
        stocks = [i for i in watched]
        for i in logins.values():
            for j in i["portfolio"]:
                if i["username"] == "jacob2" and i["portfolio"][j]["shares"] > 0 and j not in stocks:
                    stocks.append(j)
    if not len(stocks):
        return
    for i in sorted(stocks):
        if i in watched:
            output = output + "03"
        else:
            output = output + "07"
        output = output + i + " - $" + results[i]["value"]
        if (i in watched or allPercentages or onlyOwned) and i in history and len(history[i]) > 1:
            output += " " + GetChange(history[i][-2], history[i][-1])
        output += "  "
        #overflow, separate into multiple messages
        if len(output) > 400:
            SendMessage(channel, output)
            output = ""
    SendMessage(channel, output)

def PrintMniipRatings(channel):
    page = GetPage("http://mniip.com/powder/stock/best.js")
    ratings = page.split('"')
    ratings[0] = ratings[0][5:]
    output = "PowJones Stock Ratings: "
    for i in range(0, len(ratings)-1, 2):
        output = output + "07" + ratings[i].strip("{,:\n") + ": " + ratings[i+1] + " "
    SendMessage(channel, output)

def PrintRatings(channel, element = None):
    output = "PowJones Stock Ratings: "
    for i in sorted(results):
        if ((not element and int(results[i]["value"]) >= 5) or i == element) and i in history and len(history[i]) > 1:
            """minn = history[i][0]
            maxx = history[i][1]
            for j in history[i]:
                if j < minn:
                    minn = j
                if j > maxx:
                    maxx = j
            #average = (maxx+minn)/2"""

            asdf = 1.25#1+len(history[i])*.05
            #if len(history[i]) > 5:
            average = sum(history[i])/len(history[i])
            rating = GetChange(int(results[i]["value"]), average)
            if average/asdf > int(results[i]["value"]) or element:
                output = output + "07" + i + ": " + rating + " "
            """else:
                average = sum(history[i])/len(history[i])
                rating = GetChange(int(results[i]["value"]), average)
                if average > int(results[i]["value"]) or element:
                    output = output + "07" + i + ": " + rating + " """
            
            """rating = (float(results[i]["value"])-minn)/(maxx-minn)
            #rating = GetChange(1, rating)
            #output = output + "07" + i + ": " + rating + " "
            if rating < .4:
                output = output + "07" + i + ": 09" + str(int((1-rating)*100)) + "% " """

            if len(output) > 400:
                SendMessage(channel, output)
                output = ""
    SendMessage(channel, output)
                    
    
def PrintStockValue(channel, stock):
    change = ""
    if stock in history and len(history[stock]) > 1:
        change = GetChange(history[stock][-2], history[stock][-1])
    if stock in results:
        SendMessage(channel, "%s %s" % (results[stock]["value"], change))

def PrintHistory(channel, stock):
    output = "07" + stock + ": "
    if stock in history:
        for i in history[stock]:
            output = output + str(i) + ", "
        SendMessage(channel, output[:-2])

goodNews = ["grant", "stealing their newest", "purchases 50 uni", "new employees", "economy is looking great", "expected to be up"]
badNews = ["employees WILL be cut", "employee cutbacks", "expected to be down", "downgraded", "recall for their", "class action lawsuit", "bankruptcy", "center of market iussues", "sales may be slowing", "Powder Game"]
def GoodNews(news):
    for i in goodNews:
        if i in news:
            return True
    for i in badNews:
        if i in news:
            return False
    return None

def FormatNews(newsitem):
    newsType = GoodNews(newsitem[3])
    color = "09" if newsType == True else "04" if newsType == False else "08"
    return "%s%s (%s) %s %s (%s)" % (color, newsitem[2], newsitem[1], newsitem[3], newsitem[4], newsitem[0])

def IsInNews(news, newsID):
    for i in news:
        if i[0] == newsID:
            return True
    return False

news = []
def PrintNews(channel, first = False, stock = None):
    page = GetPage("http://tptapi.com/getjson.php?type=news")
    tempnews = re.findall("\"([^\"]*)\"", page)
    
    for i in range(0, len(tempnews), 6):
        newsItem = tempnews[i+3]
        if not IsInNews(news, tempnews[i+1]) and "issued dividends" not in newsItem and "FEC DISCLOSURE" not in newsItem:
            newsName = newsItem.split("(")[0].strip()
            newsItem = " ".join(newsItem.split("(")[1:])
            news.append((tempnews[i+1], newsName, newsItem.split()[0].strip(")"), " ".join(newsItem.split()[1:]), tempnews[i+5]))

    if first:
        SendMessage(channel, FormatNews(news[-1]))
    elif stock:
        for i in news[::-1]:
            if i[1] == stock:
                SendMessage(channel, FormatNews(i))
    else:
        for i in news[-1:-6:-1]:
            SendMessage(channel, FormatNews(i))


# GGG   RRR    OO   U  U  PPP   SSSS
# G     R  R  O  O  U  U  P  P  S
# G GG  RRR   O  O  U  U  PPP   SSSS
# G  G  R  R  O  O  U  U  P        S
# GGGG  R  R   OO    UU   P     SSSS

def GetUsername(who):
    account = GetAccount("jacob1@Powder/Developer/jacob1")
    if not account:
        return
    
    page = GetPage("http://tptapi.com/profile_search.php?process", account, {"username":who})
    name = re.findall(r"/u/([^']*)'/", page)
    if not name:
        try:
            return str(int(who))
        except:
            return -1
    return name[0]
	
def GetFriends(who):
    account = GetAccount("jacob1@Powder/Developer/jacob1")
    if not account:
        return
    who = GetUsername(who)
    if who == -1:
        return "Invalid profile ID"
    page = GetPage("http://tptapi.com/u/" + who, account)
    
    name = re.findall(r"<span>([^<>]*)</span>", page)
    if not name:
        return "User does not exist"
    name = name[0]
    friends = []
    friends.extend(re.findall("<b>([^<>]*)</b>", page))
    friendids = []
    friendids.extend(re.findall(r"/u/([^']*)' ", page))
    friendlist = []
    for i in range(len(friends)):
        friendlist.append(friends[i] + " (" + friendids[i] + ")")
    if len(friends):
        return "%s is friends with: %s" % (name, ", ".join(friendlist))
    else:
        if name == "jacob1":
            return "%s is friends with every single person in the world" % name
        else:
            return "%s has no friends!" % name

#http://tptapi.com/friend_request.php?opt=1&id=28&dec=1
def Message(account, who, message):
    who = GetUsername(who)
    if who == -1:
        return "Invalid profile ID"
    
    GetPage("http://tptapi.com/chat_send.php?user=%s" % (who), account, {"message":message})
    return "Message sent"

def ReadChat(account, who):
    who = GetUsername(who)
    if who == -1:
        return "Invalid profile ID"
    
    page = GetPage("http://tptapi.com/chat_message.php?id=%s" % (who), account).split("<p>")[1:6]
    if not len(page):
        return "Empty conversation"
    return page

def GetTPTSessionInfo(line):
    with open("passwords.txt") as f:
        return f.readlines()[line].strip()

def Ban(userID, time, timeunits, reason):
    if userID == "1" or userID == "38642":
        return
    data = urllib.urlencode({"BanUser":userID, "BanReason":reason, "BanTime":time, "BanTimeSpan":timeunits})
    headers = {'Cookie':GetTPTSessionInfo(0)}
    req = urllib2.Request("http://powdertoy.co.uk/User/Moderation.html?ID=%s&Key=%s" % (userID, GetTPTSessionInfo(1)), data, headers)
     
    response = urllib2.urlopen(req)
    page = response.read()
    #print(page)

def Unban(userID):
    data = urllib.urlencode({"UnbanUser":userID})
    headers = {'Cookie':GetTPTSessionInfo(0)}
    req = urllib2.Request("http://powdertoy.co.uk/User/Moderation.html?ID=%s&Key=%s" % (userID, GetTPTSessionInfo(1)), data, headers)
     
    response = urllib2.urlopen(req)
    page = response.read()
    #print(page)

""":wolfe.freenode.net 332 logbot614 ###stocks :Illegal insider trading takes place
 here, also drug smuggling

http://pastebin.com/CvwxHKUc - Javert
http://pastebin.com/5CYuBbtx - cracker64"""

@command("help", minArgs = 1)
def HelpCmd(username, hostmask, channel, text, account):
    """<command> Shows help for a command."""
    for i in commands:
        if i[0] == text[0] and i[1].__doc__:
            SendMessage(channel, "%s: %s" % (text[0], i[1].__doc__))
            return

@command("list")
def ListCmd(username, hostmask, channel, text, account):
    """(no args). Lists all commands."""
    SendMessage(channel, ", ".join(i[0] for i in commands))

@command("ping")
def PingCmd(username, hostmask, channel, text, account):
    """PONG"""
    SendMessage(channel, "pong")

@command("print")
def PrintCmd(username, hostmask, channel, text, account):
    """(print [owned]). Print all current stock prices. Add 'owned' to only print stocks which are owned by someone."""
    GetStockInfo()
    PrintStocks(channel, False, True if len(text) > 0 and text[0] == "owned" else False)

@command("printall")
def PrintAllCmd(username, hostmask, channel, text, account):
    """(printall [owned]). Print all current stock prices and percent changes.  Add 'owned' to only print stocks which are owned by someone."""
    GetStockInfo()
    PrintStocks(channel, True, True if len(text) > 0 and text[0] == "owned" else False)

@command("print2", owner = True)
def Print2Cmd(username, hostmask, channel, text, account):
    """(no args). Updates stock history with the current prices (owner only)."""
    GetStockInfo(True)

@command("login", minArgs = 2)
def LoginCmd(username, hostmask, channel, text, account):
    """(login <tptusername> <tptpassword>). Logs you in so you can buy stocks. All passwords are safely stored on jacob1's computer for future use"""
    if hostmask in logins:
        SendMessage(channel, "You are already logged in as %s" % logins[hostmask]["username"])
        return
    if username == "jacob1" and CheckOwner(hostmask) and text[0] == "jacob2":
        with open("passwords.txt") as f:
            Login(channel, hostmask, text[0], f.readlines()[2].strip())
        return
    if Login(channel, hostmask, text[0], text[1]):
        SendMessage("#TPTAPIStocks", "Logged in: %s!%s" % (username, hostmask))

@command("logout", needsAccount = True)
def LogoutCmd(username, hostmask, channel, text, account):
    """logs you out and deletes all session info"""
    if hostmask in logins:
        SendMessage(channel, "Logged out: %s" % logins[hostmask]["username"])
        del logins[hostmask]

@command("stock", minArgs = 1)
def StockCmd(username, hostmask, channel, text, account):
    """(stock <stockname>). Prints current stock price and percent change"""
    GetStockInfo()
    PrintStockValue(channel, text[0].upper())

@command("history", minArgs = 1)
def HistoryCmd(username, hostmask, channel, text, account):
    """(history <stockname>). Gives a history of all previous stock prices since the last price range change"""
    PrintHistory(channel, text[0].upper())

@command("buy", minArgs = 2, needsAccount = True)
def BuyCmd(username, hostmask, channel, text, account):
    """(buy <stockname> <numberofstocks> [a]) or (buy <stockname> <percent>% [a]). Has two options, can either buy a specific number of stocks, or spend a certain percentage of your money on the stock. Buys class B stock by default"""
    element = text[0].upper()
    total = text[1]
    stockClass = "1"
    if len(text) > 2 and text[2].lower() == "a":
        stockClass = "0"

    if element not in history:
        SendMessage(channel, "%s is not a valid stock name" % element)
        return
    if total[-1] == "%":
        GetStockInfo()
        money = GetMoney(account)
        total = int(money/int(results[element]["value"])*float(total[:-1])/100)
        SendMessage(channel, "Buying %s shares of %s" % (str(total), element))
    try:
        total = int(total)
    except:
        SendMessage(channel, "%s is not a valid number" % total)
        return

    SendMessage(channel, BuySellStocks(account, 1, element, total, stockClass))
    if element in account["portfolio"]:
        account["portfolio"][element]["shares"] = int(account["portfolio"][element]["shares"]) + int(total)
    else:
        account["portfolio"][element] = {'shares':total}
    if element not in watched:
        watched.append(element)
    #SendMessage("Crackbot", "./stock watch %s" % element)

@command("sell", minArgs = 2, needsAccount = True)
def SellCmd(username, hostmask, channel, text, account):
    """(sell <stockname> <numberofstocks> [a]). Sells a specific amount of stocks. Buys class B stock by default"""
    element = text[0].upper()
    stockClass = "1"
    if len(text) > 2 and text[2].lower() == "a":
        stockClass = "0"

    try:
        amount = int(text[1])
    except:
        SendMessage(channel, "%s is not a valid number" % text[1])
        return
    if element not in history:
        SendMessage(channel, "%s is not a valid stock name" % element)
        return
    SendMessage(channel, BuySellStocks(account, 0, element, amount, stockClass))
    
    if element in account["portfolio"]:
        account["portfolio"][element]["shares"] -= amount

@command("sellall", minArgs = 1, needsAccount = True)
def SellAllCmd(username, hostmask, channel, text, account):
    """(sellall <stockname> [a]). Seels all stocks you bought using the bot. If you didn't buy it with the bot, it won't work. Buys class B stock by default"""
    element = text[0].upper()
    stockClass = "1"
    if len(text) > 1 and text[1].lower() == "a":
        stockClass = "0"

    if element not in account["portfolio"]:
        stocks = GetPortfolioInfo(account, element)
        if not stocks:
            SendMessage(channel, "You do not own any shares of %s" % element)
            return
    else:
        stocks = int(account["portfolio"][element]["shares"])
    if stocks > 100000000000000:
        SendMessage(channel, BuySellStocks(account, 0, element, int(stocks*.9999999999), stockClass))
        leftover = GetPortfolioInfo(account, element)
        if leftover:
            #SendMessage(channel, "Selling leftover %s" % str(leftover))
            SendMessage(channel, BuySellStocks(account, 0, element, leftover, stockClass))

    else:
        #print account["portfolio"][element]["shares"]
        SendMessage(channel, BuySellStocks(account, 0, element, stocks, stockClass))
    if element in account["portfolio"]:
        account["portfolio"][element]["shares"] = 0

@command("money", needsAccount = True)
def MoneyCmd(username, hostmask, channel, text, account):
    """(no args). Prints the exact amount of money you own with no commas, if logged in"""
    SendMessage(channel, str(GetMoney(account)))

@command("give", minArgs = 2, needsAccount = True)
def GiveCmd(username, hostmask, channel, text, account):
    """(give <username> <amount>). Gives money to another user."""
    SendMessage(channel, GetPage("http://tptapi.com/sendProc.php", account, {"reciever":text[0], "amount":text[1]}, True))

@command("portfolio", needsAccount = True)
def PortfolioCmd(username, hostmask, channel, text, account):
    """(no args). Prints everything in your portfolio, if logged in"""
    info = GetPortfolioInfo(account)
    if not info:
        SendMessage(channel, "Portfolio empty")
    else:
        SendMessage(channel, info)

@command("rate")
def RateCmd(username, hostmask, channel, text, account):
    """(rate [stockname]). If no arguments, only lists the ratings for the best stocks."""
    now = datetime.now()
    if now.hour%2 == 0 and now.minute < 10:
        SendMessage(channel, "Ratings will not be available until the 10 minute mark")
        return
    GetStockInfo()
    if len(text):
        PrintRatings(channel, text[0].upper())
    else:
        PrintRatings(channel)

@command("mrate")
def MrateCmd(username, hostmask, channel, text, account):
    """(no args). Fetches alternative ratings from http://mniip.com/powder/stock/"""
    PrintMniipRatings(channel)

@command("watch", minArgs = 1)
def WatchCmd(username, hostmask, channel, text, account):
    """(watch <stockname>). Watches a stock, when the prices change every 10 minutes it will tell you if it went up or down"""
    element = text[0].upper()
    if element in history:
        if element not in watched:
            watched.append(element)
        SendMessage(channel, "Now watching %s" % element)
    else:
        SendMessage(channel, "%s is not a valid stock name" % element)

@command("news")
def NewsCmd(username, hostmask, channel, text, account):
    """(news [latest]). Prints the current news. Don't abuse this. Add 'latest' to only return the most recent news item. The effects of news tend to happen in 20-30 minutes"""
    if len(text) > 0:
        PrintNews(channel, text[0] == "latest" and True or False, text[0].upper())
    else:
        PrintNews(channel)

@command("output")
def OutputCmd(username, hostmask, channel, text, account):
    """(no args). Toggle printing stock output every 10 minutes."""
    global output
    output = (output + 1) % 3
    SendMessage(channel, "Output has been turned %s" % ("on" if output else "off"))

@command("quit", owner = True)
def QuitCmd(username, hostmask, channel, text, account):
    """(no args). Make the bot quit (admin only)."""
    irc.send("QUIT :i'm a potato\n")
    irc.close()
    quit()

@command("join", minArgs = 1, owner = True)
def JoinCmd(username, hostmask, channel, text, account):
    """(no args). Make the bot join a channel (admin only)."""
    Send("JOIN %s\n" % text[0])

@command("part", minArgs = 1, owner = True)
def JoinCmd(username, hostmask, channel, text, account):
    """(no args). Make the bot part a channel (admin only)."""
    Send("PART %s\n" % text[0])

#groups
@command("friends", minArgs = 1)
def FriendsCmd(username, hostmask, channel, text, account):
    """(friends <username|userID>). Returns all the friends of a certain user"""
    SendMessage(channel, GetFriends(text[0]))

@command("message", minArgs = 2)
def MessageCmd(username, hostmask, channel, text, account):
    """(message <username|userID> <text>). Send a message to a user, if you are friends"""
    SendMessage(channel, Message(account, text[0], " ".join(text[1:])))

@command("readchat", minArgs = 1)
def ReadChatCmd(username, hostmask, channel, text, account):
    """(readchat <username|userID>). Print out the last 5 chat messages from your conversation with a user"""
    page = ReadChat(account, text[0])
    for i in page:
        SendMessage(channel, re.sub("<.*?>", "", i))

#TPT
@command("ban", minArgs = 4, owner = True)
def BanCmd(username, hostmask, channel, text, account):
    """(ban <user ID> <ban time> <ban time units> <reason>). bans someone in TPT. Admin only."""
    if username != "jacob1":
        SendMessage("TPTAPIStocks", "Error, only jacob1 should be able to use this command")
    Ban(text[0], text[1], text[2], " ".join(text[3:]))

@command("unban", minArgs = 1, owner = True)
def UnbanCmd(username, hostmask, channel, text, account):
    """(unban <user ID>). unbans someone in TPT. Admin only."""
    if username != "jacob1":
        SendMessage("TPTAPIStocks", "Error, only jacob1 should be able to use this command")
    Unban(text[0])