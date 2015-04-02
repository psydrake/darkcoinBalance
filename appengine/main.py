"""Main.py is the top level script.

Loads the Bottle framework and mounts controllers.  Also adds a custom error
handler.
"""

from google.appengine.api import memcache, urlfetch
# import the Bottle framework
from server.lib.bottle import Bottle, request, response, template
import json, logging, StringIO, urllib2
from decimal import *

# TODO: name and list your controllers here so their routes become accessible.
from server.controllers import RESOURCE_NAME_controller

# Main block explorer URL no longer works 8/28/2014
BLOCKEXPLORER_URL = 'http://explorer.darkcoin.io/chain/Darkcoin/q/addressbalance/'
BLOCKEXPLORER_URL_BACKUP = 'http://chainz.cryptoid.info/drk/api.dws?q=getbalance&a='

#TRADING_PAIR_URL_BTC_BACKUP="https://api.mintpal.com/v1/market/stats/DRK/" # also used for LTC
TRADING_PAIR_URL_BTC_CRYPTSY = 'http://pubapi.cryptsy.com/api.php?method=singlemarketdata&marketid=155'
TRADING_PAIR_URL_LTC_CRYPTSY = 'http://pubapi.cryptsy.com/api.php?method=singlemarketdata&marketid=214'
TRADING_PAIR_URL = 'http://api.cryptocoincharts.info/tradingPair/' # no CNY or EUR
TRADING_PAIR_URL_USD_BACKUP = 'https://coinbase.com/api/v1/prices/buy' 
# TRADING_PAIR_URL_FIAT_BACKUP = 'http://api.bitcoincharts.com/v1/markets.json'
BTCAVERAGE_URL = 'https://api.bitcoinaverage.com/ticker/' # used for BTC / (CNY, EUR, GBP, AUD)

TIMEOUT_DEADLINE = 10 # seconds

# Run the Bottle wsgi application. We don't need to call run() since our
# application is embedded within an App Engine WSGI application server.
bottle = Bottle()

# Mount a new instance of bottle for each controller and URL prefix.
# TODO: Change 'RESOURCE_NAME' and add new controller references
bottle.mount("/RESOURCE_NAME", RESOURCE_NAME_controller.bottle)

@bottle.route('/')
def home():
  """Return project name at application root URL"""
  return "Darkcoin Balance"

@bottle.route('/api/balance/<address:re:[a-zA-Z0-9]+>')
def getBalance(address=''):
    response.content_type = 'application/json; charset=utf-8'

    url = BLOCKEXPLORER_URL + address
    data = None
    useBackupUrl = False

    try:
        data = urlfetch.fetch(url, deadline=TIMEOUT_DEADLINE)
        if (not data or not data.content or data.status_code != 200):
            logging.warn('No content returned from ' + url)
            useBackupUrl = True
    except:
        logging.warn('Error retrieving ' + url)
        useBackupUrl = True

    if (useBackupUrl):
        backupUrl = BLOCKEXPLORER_URL_BACKUP + address
        logging.warn('Now trying ' + backupUrl)
        data = urlfetch.fetch(backupUrl, deadline=TIMEOUT_DEADLINE)

    dataDict = json.loads(data.content)
    balance = json.dumps(dataDict)
    mReturn = balance

    query = request.query.decode()
    if (len(query) > 0):
        mReturn = query['callback'] + '({balance:' + balance + '})'

    logging.info("getBalance(" + address + "): " + mReturn)
    return mReturn

@bottle.route('/api/trading-dash')
@bottle.route('/api/trading-dash/')
@bottle.route('/api/trading-dash/<currency:re:[A-Z][A-Z][A-Z]>')
@bottle.route('/api/trading-drk')
@bottle.route('/api/trading-drk/')
@bottle.route('/api/trading-drk/<currency:re:[A-Z][A-Z][A-Z]>')
def tradingDASH(currency='BTC'):
    response.content_type = 'application/json; charset=utf-8'
    mReturn = '{}'

    # All supported currencies besides EUR have a direct trading pair with DASH
    # Update: Adding USD to this, b/c DRK_USD trading pair price seems inaccurate
    if (currency not in ['EUR', 'USD', 'GBP', 'CNY', 'AUD']):
        dashCurrency = json.loads(memcache.get('trading_DASH_' + currency))
        if (not dashCurrency):
            logging.warn('No data found in memcache for trading_DASH_' + currency)
            return mReturn
        else:
            mReturn = dashCurrency['price']
    else:
        # For EUR, CNY, GBP, and USD we have to convert from DASH -> BTC -> FIAT
        dashBtc = json.loads(memcache.get('trading_DASH_BTC'))
        if (not dashBtc):
            logging.warn("No data found in memcache for trading_DASH_BTC")
            return mReturn

        btcCurrency = json.loads(memcache.get('trading_BTC_' + currency))
        if (not btcCurrency):
            logging.warn("No data found in memcache for trading_BTC_" + currency)
            return mReturn

        logging.info('dashBtc: ' + str(dashBtc) + ', btcCurrency: ' + str(btcCurrency))
        mReturn = Decimal(dashBtc['price']) * Decimal(btcCurrency['price'])

    query = request.query.decode()
    if (len(query) > 0):
        mReturn = query['callback'] + '({price:' + str(mReturn) + '})'

    logging.info("tradingDASH(" + currency + "): " + str(mReturn))
    return str(mReturn)

def pullTradingPair(currency1='DASH', currency2='BTC'):
    url = ''
    if (currency1 == 'DASH'):
        if (currency2 == 'BTC'):
            url = TRADING_PAIR_URL_BTC_CRYPTSY
        elif (currency2 == 'LTC'):
            url = TRADING_PAIR_URL_LTC_CRYPTSY
    elif (currency1 == 'BTC' and currency2 in ['AUD', 'CNY', 'GBP', 'EUR', 'USD']):
            url = BTCAVERAGE_URL + currency2 + '/'

    data = None
    useBackupUrl = False

    try:
        data = urlfetch.fetch(url, deadline=TIMEOUT_DEADLINE)
        if (not data or not data.content or data.status_code != 200):
            logging.warn('No content returned from ' + url)
            useBackupUrl = True
    except:
        logging.warn('Error retrieving ' + url)
        useBackupUrl = True

    if useBackupUrl:
        if (currency1 == 'BTC' and currency2 == 'USD'):
            backupUrl = TRADING_PAIR_URL_USD_BACKUP
            logging.warn('Now trying ' + backupUrl)
            try:
                data = urlfetch.fetch(backupUrl, deadline=TIMEOUT_DEADLINE)
                if (not data or not data.content or data.status_code != 200):
                    logging.error('No content returned from ' + backupUrl)
            except:
                logging.error('Error retrieving ' + backupUrl)
        else:
            backupUrl = TRADING_PAIR_URL + currency1 + '_' + currency2 
            logging.warn('Now trying ' + backupUrl)
            try:
                data = urlfetch.fetch(backupUrl, deadline=TIMEOUT_DEADLINE)
                if (not data or not data.content or data.status_code != 200):
                    logging.error('No content returned from ' + backupUrl)
            except:
                logging.error('Error retrieving ' + backupUrl)

    dataDict = json.loads(data.content)

    # now we have the API data - let's parse it
    if not useBackupUrl:
        if (currency1 == 'DASH' and currency2 in ['BTC', 'LTC']): # using cryptsy data

            # Cryptsy may not have switched to DASH from DRK yet
            dashData = None
            try:
                dashData = dataDict['return']['markets'][currency1]
            except:
                dashData = dataDict['return']['markets']['DRK']

            if (dashData['label'] == currency1 + "/" + currency2):
                dataDict = {'price': dashData['lasttradeprice']}
                logging.info(currency1 + '_' + currency2 + ': ' + dataDict['price'])
            else:
                logging.error('Cannot get trading pair for ' + currency1 + ' / ' + currency2)
                return

        elif (currency1 == 'BTC' and currency2 in ['AUD', 'CNY', 'EUR', 'GBP', 'USD']): # using btcaverage data
            # standardize format of exchange rate data from different APIs (we will use 'price' as a key)
            dataDict['price'] = dataDict['last'] 
    else: # we are using a backup API URL
        if (currency1 == 'BTC' and currency2 == 'USD'):
            if (dataDict['subtotal']['currency'] == 'USD'):
                dataDict = {'price': dataDict['subtotal']['amount']}
            else:
                logging.error('Unexpected JSON returned from URL ' + TRADING_PAIR_URL_USD_BACKUP)
                return
        # else dataDict.price should be correct from TRADING_PAIR_URL

    tradingData = json.dumps(dataDict).strip('"')
    memcache.set('trading_' + currency1 + '_' + currency2, tradingData)
    logging.info('Stored in memcache for key trading_' + currency1 + '_' + currency2 + ': ' + tradingData)

@bottle.route('/tasks/pull-cryptocoincharts-data')
def pullCryptocoinchartsData():
    pullTradingPair('DASH', 'BTC')
    pullTradingPair('DASH', 'LTC')
    pullTradingPair('BTC', 'CNY')
    pullTradingPair('BTC', 'USD')
    pullTradingPair('BTC', 'EUR')
    pullTradingPair('BTC', 'GBP')
    #pullTradingPair('BTC', 'AUD')
    return "Done"

@bottle.error(404)
def error_404(error):
  """Return a custom 404 error."""
  return 'Sorry, Nothing at this URL.'
