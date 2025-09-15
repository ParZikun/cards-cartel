# cards-cartel

## THINGS TO REMEMBER
- U need a way to refresh the auth and cookies data if they expire
- also need to think for a backup if acc is bloacked (like think of ways that the id doenst get blocked kek)

KEEP it optimized as we are fighting with time here as the cards might get sniped in near about 5 seconds so we need our process to run within 1 secs for one cycle of watch dog (except the first run we'll ignore it as we are populating the DB with older entries)

## File Functions

    > TIP: In the API call keep Sort by time so we can just populate the DB once and then we can just call it every 0.6 secs if we get a new listing process it, else just wait like a watch-dog kind of shit.    

- `get_data.py` - GET DATA functions LOGIC:

    - ME API: send the params and get all latest listing in pagination mode if more than 100 (not possible but just in case I dont want it to break when db is empty and we run it for first time we'll get more than 100 so).✅

    - ALT.XYZ SITE: (to search using cert id we need to login, we need to see if we can save some cookies or some shit somewhere so that we can sracpe it easily) scraper and regex to filter the recent 5 transactions (For the recent transactions we'll consider either the 5 transactions or less than 5 but all the transactions we are selecting shall be have been made within a month) ✅
  
- `convert_price.py` - Converter
  - need a function to convert usdc to sol and visa versa and save both values bcoz it can be listed as any

- `discord_alert.py` - Alert 
  - Send the alert based on the sensitivity of listing

- `dashboard.py` - Simple Dashboard to show the details

- `save_data.py` - to save the listing in db per listing not all at once bcoz we need to do this quickly as possible.

- `main.py` - to control the whole pipeline (|| : indicates we can do it parallely)
    main (run this Forever) =>
        - `watch_dog()` - Watch dog to scrape ME site every 0.6secs for new listings and save in the db. 
        watch-dog (Till all latest listing processed under 1 sec (as the listings are quite apart so we'll probably get one listing per 0.6 CALL, but as we are in competition with the other snipers in the market we need to be quick as a egale), ignoring the first run were we'll take more time as we'll get all the listing to populate the db to catup to latest one hahaha) => 
            get_data ✅ => convert_price 🦾 => save_data 🦾 || check conditions ⚠️ => discord || dashboard 🦾 
            (complete this loop in under 1 second, bcoz after the first iteration we'll only get 10-20 listing at max)

## Details to Display

- Dashboard & Discord Embed Message 
  - CARD DISPLAY Details
    - Name
    - Grade
    - Insured Value
    - grading company
    - Avg Price alt
    - Posted value (difference with % compared to Alt in green)
    - ME Link
    - Alt Link (if easy to find)
    - mint token adress
    - CC link
    - IMG
    - grading_id
    - token_mint
    - price it is listed in 
    - price_sol
    - price_usdc

## SNIPER LOGIC

- Get the List of all the (status: buy now, trait: category=pokemon) cards/bundles/boxes from ME and their dets and save them in DB
- For each item we'll process all the list that we got from ME:

  - if Bundles/ boxes 
    - Get the mint token address and get insured value from CC
    - if ME listed price < 25% of insured price (the most imp one) HIGH ALERT 
        - ALERT PING on DC 
        - Dashboard update
    - if ME listed price < 50% of insured price (okish) ALERT
        - PING on DC 
        - Dashboard update
    - if ME listed price < insured price (just to be updated) JUST UPDATE
        - DC Message 
        - Dashboard update

  - Cards
    - Get the grading id/ cert id from ME and search the exact card on alt.xyz and return recent trnxs and find the avg buy price of it
    - Also get the insured price from CC just to show it as a param on dc message and dashboard
    - if ME listed price < 25% of avg price in recent transaction HIGH ALERT 
        - ALERT PING on DC 
        - Dashboard update
    - if ME listed price < 50% of avg price in recent transaction ALERT
        - PING on DC 
        - Dashboard update
    - if ME listed price < avg price in recent transaction JUST UPDATE
        - DC Message 
        - Dashboard update
  