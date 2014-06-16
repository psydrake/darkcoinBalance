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

BLOCKEXPLORER_URL = 'http://explorer.darkcoin.io/chain/DarkCoin/q/addressbalance/'
BLOCKEXPLORER_URL_BACKUP = 'http://chainz.cryptoid.info/drk/api.dws?q=getbalance&a='
TRADING_PAIR_URL = 'http://www.cryptocoincharts.info/v2/api/tradingPair/'
TRADING_PAIR_URL_BTC_BACKUP="https://api.mintpal.com/v1/market/stats/DRK/" # also used for LTC
TRADING_PAIR_URL_USD_BACKUP = 'https://coinbase.com/api/v1/prices/buy' 
# TRADING_PAIR_URL_FIAT_BACKUP = 'http://api.bitcoincharts.com/v1/markets.json'

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

@bottle.route('/api/trading-drk')
@bottle.route('/api/trading-drk/')
@bottle.route('/api/trading-drk/<currency:re:[A-Z][A-Z][A-Z]>')
def tradingDRK(currency='BTC'):
    response.content_type = 'application/json; charset=utf-8'
    mReturn = '{}'

    # All supported currencies besides EUR have a direct trading pair with DRK
    # Update: Adding USD to this, b/c DRK_USD trading pair price seems inaccurate
    if (currency not in ['EUR', 'USD']):
        drkCurrency = json.loads(memcache.get('trading_DRK_' + currency))
        if (not drkCurrency):
            logging.warn('No data found in memcache for trading_DRK_' + currency)
            return mReturn
        else:
            mReturn = drkCurrency['price']
    else:
        # For EUR and USD we have to convert from DRK -> BTC -> EUR / USD
        drkBtc = json.loads(memcache.get('trading_DRK_BTC'))
        if (not drkBtc):
            logging.warn("No data found in memcache for trading_DRK_BTC")
            return mReturn

        btcCurrency = json.loads(memcache.get('trading_BTC_' + currency))
        if (not btcCurrency):
            logging.warn("No data found in memcache for trading_BTC_" + currency)
            return mReturn

        logging.info('drkBtc: ' + str(drkBtc) + ', btcCurrency: ' + str(btcCurrency))
        mReturn = Decimal(drkBtc['price']) * Decimal(btcCurrency['price'])

    query = request.query.decode()
    if (len(query) > 0):
        mReturn = query['callback'] + '({price:' + str(mReturn) + '})'

    logging.info("tradingDRK(" + currency + "): " + str(mReturn))
    return str(mReturn)

def pullTradingPair(currency1='DRK', currency2='BTC'):
    url = TRADING_PAIR_URL + currency1 + '_' + currency2
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
        if (currency1 == 'DRK' and currency2 in ['BTC', 'LTC']):
            backupUrl = TRADING_PAIR_URL_BTC_BACKUP + currency2
            logging.warn('Now trying ' + backupUrl)
            data = urlfetch.fetch(backupUrl, deadline=TIMEOUT_DEADLINE)
        elif (currency1 == 'BTC' and currency2 == 'USD'):
            backupUrl = TRADING_PAIR_URL_USD_BACKUP
            logging.warn('Now trying ' + backupUrl)
            data = urlfetch.fetch(backupUrl, deadline=TIMEOUT_DEADLINE)
        else:
            logger.error('Cannot get trading pair for ' + currency1 + ' / ' + currency2)
            return

    dataDict = json.loads(data.content)
    if (useBackupUrl):
        if (currency1 == 'DRK' and currency2 in ['BTC', 'LTC']):
            dataDict = {'price': dataDict[0]['last_price']}
        elif (currency1 == 'BTC' and currency2 == 'USD'):
            if (dataDict['subtotal']['currency'] == 'USD'):
                dataDict = {'price': dataDict['subtotal']['amount']}
            else:
                logger.error('Unexpected JSON returned from URL ' + TRADING_PAIR_URL_USD_BACKUP)
        else:
            logger.error('Should never get here')

    tradingData = json.dumps(dataDict).strip('"')
    memcache.set('trading_' + currency1 + '_' + currency2, tradingData)
    logging.info('Stored in memcache for key trading_' + currency1 + '_' + currency2 + ': ' + tradingData)

@bottle.route('/tasks/pull-cryptocoincharts-data')
def pullCryptocoinchartsData():
    pullTradingPair('DRK', 'BTC')
    pullTradingPair('DRK', 'LTC')
    pullTradingPair('BTC', 'USD')
    pullTradingPair('DRK', 'CNY')
    pullTradingPair('BTC', 'EUR')
    return "Done"

@bottle.error(404)
def error_404(error):
  """Return a custom 404 error."""
  return 'Sorry, Nothing at this URL.'
