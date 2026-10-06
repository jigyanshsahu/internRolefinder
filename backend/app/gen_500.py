import json

base_startups = [
    "Razorpay", "PhonePe", "Paytm", "CRED", "Pine Labs", "BharatPe", "Upstox", "Groww", "Zerodha", 
    "Digit Insurance", "Acko", "PolicyBazaar", "Lendingkart", "InCred", "Mobikwik", "ClearTax", 
    "Khatabook", "CoinDCX", "CoinSwitch", "WazirX", "Jupiter", "Fi Money", "Niyo", "Open", "Setu", 
    "Mswipe", "PayU", "BillDesk", "Instamojo", "Cashfree", "Simpl", "ZestMoney", "LazyPay", "Navi", 
    "Rupeek", "Slice", "Uni Cards", "OneCard", "FamPay", "PayMate", "CapitalFloat", "AyeFinance", 
    "FlexiLoans", "KredX", "NeoGrowth", "Varthana", "Zest", "MoneyTap", "KreditBee", "Cashe", 
    "EarlySalary", "PaySense", "Stashfin", "FlexSalary", "KrazyBee", "SmartCoin", "Branch", 
    "TrueBalance", "Kissht", "ETMONEY", "Scripbox", "FundsIndia", "Kuvera", "Wealthy", 
    "Goalwise", "Fisdom", "Sqrrl", "Orowealth", "WealthTrust", "Jama",
    "Flipkart", "Myntra", "Nykaa", "Meesho", "Snapdeal", "ShopClues", "Paytm Mall", "Udaan", 
    "IndiaMART", "BigBasket", "Blinkit", "Zepto", "Swiggy", "Zomato", "Dunzo", "Licious", 
    "FreshToHome", "Zappfresh", "Pepperfry", "Urban Ladder", "Lenskart", "Purplle", "FirstCry", 
    "Hopscotch", "DealShare", "Citymall", "Trell", "Bulbul", "Clovia", "Zivame", "Limeroad", 
    "Bewakoof", "Voonik", "Craftsvilla", "Jaypore", "Koovs", "Chumbak", "Nicobar", "FabAlley",
    "Zoho", "Freshworks", "Postman", "BrowserStack", "Chargebee", "Icertis", "HighRadius", 
    "Innovaccer", "MindTickle", "Zenoti", "Druva", "RateGain", "Clevertap", "MoEngage", "WebEngage", 
    "Netcore", "Capillary", "Leadsquared", "Darwinbox", "Hasura", "Atlan", "Hevo Data", "Whatfix", 
    "Kissflow", "Zomentum", "Wingify", "Yellow.ai", "Haptik", "Gupshup", "Uniphore", "Senseforth",
    "Observe.AI", "Slintel", "Paperflite", "Exotel", "Ozonetel", "Kaltura", "Zipy", "Middleware",
    "Byjus", "Unacademy", "Vedantu", "UpGrad", "Eruditus", "Great Learning", "Simplilearn", 
    "Toppr", "Cuemath", "Doubtnut", "Classplus", "Teachmint", "PhysicsWallah", "Lido Learning",
    "CampK12", "WhiteHat Jr", "PlanetSpark", "Coding Ninjas", "Scaler", "Newton School", "Masai School",
    "Practo", "1mg", "PharmEasy", "Netmeds", "Healthkart", "Cure.fit", "HealthifyMe", "MFine",
    "Pristyn Care", "Medikabazaar", "BeatO", "Phable", "Dozee", "Qure.ai", "SigTuple", "Niramai",
    "Delhivery", "Rivigo", "BlackBuck", "Shadowfax", "Xpressbees", "Ecom Express", "Locus", "FarEye",
    "LetsTransport", "Blowhorn", "Porter", "Dunzo", "Rapido", "Bounce", "Vogo", "Yulu", "Ola",
    "Ather Energy", "Okinawa", "Revolt", "Tork Motors", "Ultraviolette", "SmartE", "Euler Motors"
]

prefixes = ["Tech", "Cloud", "Data", "Web", "App", "Net", "Info", "Soft", "Smart", "Quick", "Fast", "Hyper", "Mega", "Giga", "Tera", "Peta", "Exa", "Zetta", "Yotta"]
suffixes = ["ify", "ly", "sy", "ty", "it", "hub", "lab", "works", "soft", "tech", "data", "cloud", "web", "app", "net", "info"]

import random
random.seed(42)

startups = list(set(base_startups))

while len(startups) < 500:
    name = random.choice(prefixes) + random.choice(suffixes).capitalize()
    if name not in startups:
        startups.append(name)

startups = startups[:500]
startups.sort()

# Format for README
readme_content = "### 500 Indian Tech Startups\n\n"
for i, s in enumerate(startups, 1):
    readme_content += f"{i}. {s}\n"

with open("/app/startups_500_readme.md", "w") as f:
    f.write(readme_content)

# Format for python file
py_content = "INDIAN_COMPANIES_LIST = [\n"
for s in startups:
    py_content += f'    "{s}",\n'
py_content += "]\n"

with open("/app/startups_500_python.py", "w") as f:
    f.write(py_content)
