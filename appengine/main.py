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

import hashlib, hmac, time # for bitcoinaverage API
import config # this file contains secret API key(s), and so it is in .gitignore

BLOCKEXPLORER_URL = 'http://chainz.cryptoid.info/dash/api.dws?q=getbalance&a='

TIMEOUT_DEADLINE = 10 # seconds

# used for BTC / (CNY, GBP, EUR, AUD)
def bitcoinaverage_ticker(currency):
  timestamp = int(time.time())
  payload = '{}.{}'.format(timestamp, config.bitcoinaverage_public_key)
  hex_hash = hmac.new(config.bitcoinaverage_secret_key.encode(), msg=payload.encode(), digestmod=hashlib.sha256).hexdigest()
  signature = '{}.{}'.format(payload, hex_hash)

  url = 'https://apiv2.bitcoinaverage.com/indices/global/ticker/BTC' + currency
  headers = {'X-Signature': signature}
  return urlfetch.fetch(url, headers=headers, deadline=TIMEOUT_DEADLINE)

def cryptopia_ticker(currency1, currency2):
  url = 'https://www.cryptopia.co.nz/api/GetMarket/' + currency1 + '_' + currency2
  return urlfetch.fetch(url, deadline=TIMEOUT_DEADLINE)

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

  url = BLOCKEXPLORER_URL + address + '&key=' + config.cryptoid_api_key
  data = urlfetch.fetch(url, deadline=TIMEOUT_DEADLINE)

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
  if (currency not in ['EUR', 'USD', 'GBP', 'CNY']):
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
  dataDict = None
  if (currency1 == 'BTC' and currency2 in ['CNY', 'GBP', 'EUR', 'USD']):
    data = bitcoinaverage_ticker(currency2)
    if (not data or not data.content or data.status_code != 200):
      logging.error('No content returned for ' + currency1 + '_' + currency2)
      return
    else:
      dataDict = json.loads(data.content)
      dataDict['price'] = dataDict['last']
  else:
    data = cryptopia_ticker(currency1, currency2)
    if (not data or not data.content or data.status_code != 200):
      logging.error('No content returned for ' + currency1 + '_' + currency2)
      return
    else:
      dataDict = json.loads(data.content)
      dataDict['price'] = dataDict['Data']['LastPrice']

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
  return "Done"

@bottle.error(404)
def error_404(error):
  """Return a custom 404 error."""
  return 'Sorry, Nothing at this URL.'
