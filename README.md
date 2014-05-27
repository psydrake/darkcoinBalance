# Darkcoin Balance

## About
Web / mobile app for checking the balance of your Darkcoin wallet address(es), as well as the currency value of Darkcoin.

## Technical
Darkcoin Balance consists of two parts:
* A pure HTML / CSS / JavaScript front end built with the [AngularJS](http://angularjs.org/) JavaScript framework.
* A [Google App Engine](https://developers.google.com/appengine/) back end, written in [Python](http://www.python.org/), that looks up wallet balance data from the [Darkcoin Blockchain](http://explorer.darkcoin.io/chain/DarkCoin/) and caches currency price data from the [cryptocoincharts.info](http://www.cryptocoincharts.info/) API.

The front end communicates with the back end via [JSONP](http://en.wikipedia.org/wiki/JSONP) calls. The backend polls cryptocoincharts.info every 10 minutes, and it stores this data in [memcache](https://developers.google.com/appengine/docs/python/memcache/) for all subsequent client requests, in order to reduce load on the CryptoCoinCharts server. Wallet balance lookups from the Darkcoin Blockchain [API](http://explorer.darkcoin.io/chain/DarkCoin/q/) occur on demand.

## Install On Your Device
* [Android](https://play.google.com/store/apps/details?id=net.edrake.darkcoinbalancewow)
* [Amazon Kindle Fire](http://www.amazon.com/Drake-Emko-Darkcoin-Balance/dp/B00ISNBWEY)
* [Windows Phone](http://www.windowsphone.com/en-us/store/app/darkcoin-balance/9e343cb7-3552-4f7f-9d88-0a0d87c05848)
* [Blackberry 10](http://appworld.blackberry.com/webstore/content/53031888/)
* [FirefoxOS](https://marketplace.firefox.com/app/darkcoin-balance)
* [Chrome Web Store](https://chrome.google.com/webstore/detail/darkcoin-balance/mbldbbdmcmpelfakglhfafgiopeepnob)
* [Browse As A Web Site](http://d2a4gw4qtrw231.cloudfront.net/main.html)

## Author
Drake Emko - drakee (a) gmail.com
* [@DrakeEmko](https://twitter.com/DrakeEmko)
* [Wolfgirl Band](http://wolfgirl.bandcamp.com/)
